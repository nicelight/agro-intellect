from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import threading
import time
import uuid

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Uuid, event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from backend.app import AppSettings
from backend.app.access_admin.farm_service import FarmService
from backend.app.access_admin.models import Plant, PlantAccessGrant
from backend.app.agent_runtime import DatabaseRuntimeAuthorizationGuard
from backend.app.safety_gate import (
    SafetyClassification,
    SafetyGateClassificationService,
)
from backend.app.safety_gate.repository import (
    CurrentGuardLockUnavailable,
    SafetyClassificationRepository,
)
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
    revoke_access,
)
from tests.backend.safety_gate.helpers import (
    FailingExecutor,
    RecordingExecutor,
    candidate,
    command_for,
    envelope_for,
)


def _classification_count(database) -> int:
    with database.session() as session:
        return session.scalar(select(func.count(SafetyClassification.message_id)))


def _downstream_counts(database) -> tuple[int, int, int]:
    with database.session() as session:
        return tuple(
            session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("agent_bus_events", "ui_feed_events", "plant_state_records")
        )


def _database_deadlocks(database) -> int:
    with database.session() as session:
        return int(
            session.scalar(
                text(
                    "SELECT deadlocks FROM pg_stat_database "
                    "WHERE datname = current_database()"
                )
            )
            or 0
        )


def _wait_for_postgresql_lock(database, backend_pid: int, *, timeout: float = 10) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with database.session() as session:
            wait_event_type = session.scalar(
                text(
                    "SELECT wait_event_type FROM pg_stat_activity "
                    "WHERE pid = :backend_pid"
                ),
                {"backend_pid": backend_pid},
            )
        if wait_event_type == "Lock":
            return True
        time.sleep(0.01)
    return False


def test_authoritative_physical_classification_round_trips_without_direct_effect(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(
        boss,
        plant,
        candidate_output="credential=opaque-candidate ручное добавление питания",
    )
    executor = RecordingExecutor(candidate(action_kind="ec_adjustment"))
    with ft011_database.session() as session:
        def assert_no_transaction():
            assert session.in_transaction() is False

        executor.transaction_probe = assert_no_transaction
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
        ).classify(command_for(boss, envelope))

    assert outcome.outcome_kind == "classification_persisted"
    assert outcome.authoritative is True
    assert outcome.effect == "evidence_written"
    assert outcome.classification_result is not None
    assert outcome.classification_result.classification == "physical_action"
    assert outcome.classification_result.reason_code == "physical_action_detected"
    assert outcome.physical_action_kind == "ec_adjustment"
    assert outcome.provider_status == "completed"
    assert outcome.error_code is None
    assert len(executor.requests) == 1
    assert "credential=opaque-candidate" not in str(outcome.as_value())

    with ft011_database.session() as session:
        row = session.get(SafetyClassification, envelope.message_id)
        assert row is not None
        assert row.message_id == envelope.message_id
        assert row.farm_id == farm.farm_id
        assert row.plant_id == plant.plant_id
        assert row.origin_agent_id == "hydroponics_advisor"
        assert row.classifier_version == "safety_gate_v1"
        assert row.classification == "physical_action"
        assert row.safe_task_kind is None
        assert row.physical_action_kind == "ec_adjustment"
        assert row.provider_status == "completed"
        assert row.model_ref == "test_provider:safety_v1"
        assert len(row.input_sha256) == len(row.result_sha256) == 64
        assert row.created_at is not None
    assert _downstream_counts(ft011_database) == (0, 0, 0)


@pytest.mark.parametrize(
    ("executor_factory", "provider_status", "provider_call_status", "error_code"),
    [
        (
            lambda: None,
            "not_configured",
            "not_attempted",
            "SAFETY_CLASSIFIER_NOT_CONFIGURED",
        ),
        (
            FailingExecutor,
            "failed",
            "failed",
            "SAFETY_CLASSIFIER_PROVIDER_FAILED",
        ),
        (
            lambda: RecordingExecutor(
                {
                    "schema_version": 1,
                    "candidate_classification": "safe_information",
                    "safe_task_kind": None,
                    "physical_action_kind": None,
                    "raw_reasoning": "forbidden",
                }
            ),
            "invalid",
            "completed",
            "SAFETY_CLASSIFIER_OUTPUT_INVALID",
        ),
    ],
)
def test_unbound_failure_and_invalid_output_persist_only_fail_closed_authority(
    executor_factory,
    provider_status,
    provider_call_status,
    error_code,
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    executor = executor_factory()
    with ft011_database.session() as session:
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
        ).classify(command_for(boss, envelope))

    assert outcome.authoritative is True
    assert outcome.classification_result is not None
    assert outcome.classification_result.classification == "blocked_uncertain"
    assert outcome.classification_result.reason_code == "classification_uncertain"
    assert outcome.physical_action_kind is None
    assert outcome.provider_status == provider_status
    assert outcome.provider_call_status == provider_call_status
    assert outcome.error_code == error_code
    with ft011_database.session() as session:
        row = session.get(SafetyClassification, envelope.message_id)
        assert row is not None
        assert row.classification == "blocked_uncertain"
        assert row.provider_status == provider_status
        assert row.safe_task_kind is None
        assert row.physical_action_kind is None
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_postgresql_accepts_every_shared_result_family_only_after_backend_mapping(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    cases = (
        (candidate("safe_information"), "safe_information", None, None),
        (
            candidate("safe_task_request", task_kind="check"),
            "safe_task_request",
            "check",
            None,
        ),
        (
            candidate("safe_task_request", task_kind="measurement"),
            "safe_task_request",
            "measurement",
            None,
        ),
        (
            candidate("safe_task_request", task_kind="follow_up"),
            "safe_task_request",
            "follow_up",
            None,
        ),
        (candidate("blocked_uncertain"), "blocked_uncertain", None, None),
    )
    message_ids = []
    for raw, expected_class, expected_task, expected_action in cases:
        envelope = envelope_for(boss, plant)
        message_ids.append(envelope.message_id)
        with ft011_database.session() as session:
            outcome = SafetyGateClassificationService(
                session,
                model_executor=RecordingExecutor(raw),
            ).classify(command_for(boss, envelope))
        assert outcome.authoritative is True
        assert outcome.classification_result is not None
        assert outcome.classification_result.classification == expected_class
        assert outcome.classification_result.safe_task_kind == expected_task
        assert outcome.physical_action_kind == expected_action

    with ft011_database.session() as session:
        rows = list(
            session.scalars(
                select(SafetyClassification)
                .where(SafetyClassification.message_id.in_(message_ids))
                .order_by(SafetyClassification.message_id)
            )
        )
    assert len(rows) == len(cases)
    assert all(row.provider_status == "completed" for row in rows)
    assert all(row.classifier_version == "safety_gate_v1" for row in rows)
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_identical_retry_avoids_provider_and_returns_first_authority(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    first_executor = RecordingExecutor(candidate(action_kind="solution_change"))
    with ft011_database.session() as session:
        first = SafetyGateClassificationService(
            session,
            model_executor=first_executor,
        ).classify(command_for(boss, envelope))
    retry_executor = FailingExecutor()
    with ft011_database.session() as session:
        retry = SafetyGateClassificationService(
            session,
            model_executor=retry_executor,
        ).classify(command_for(boss, envelope))

    assert first.outcome_kind == "classification_persisted"
    assert retry.outcome_kind == "classification_idempotent"
    assert retry.authoritative is True
    assert retry.effect == "evidence_duplicate"
    assert retry.physical_action_kind == "solution_change"
    assert retry.provider_call_status == "not_attempted"
    assert len(first_executor.requests) == 1
    assert retry_executor.requests == []
    assert _classification_count(ft011_database) == 1
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_conflicting_input_fingerprint_is_no_effect_and_first_write_is_immutable(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    message_id = uuid.uuid4()
    first_envelope = envelope_for(
        boss,
        plant,
        message_id=message_id,
        candidate_output="Ручная корректировка pH.",
    )
    first_executor = RecordingExecutor(candidate(action_kind="ph_adjustment"))
    with ft011_database.session() as session:
        first = SafetyGateClassificationService(
            session,
            model_executor=first_executor,
        ).classify(command_for(boss, first_envelope))
    conflicting_envelope = envelope_for(
        boss,
        plant,
        message_id=message_id,
        candidate_output="Включить насос.",
    )
    conflicting_executor = RecordingExecutor(candidate(action_kind="pump_command"))
    with ft011_database.session() as session:
        conflict = SafetyGateClassificationService(
            session,
            model_executor=conflicting_executor,
        ).classify(command_for(boss, conflicting_envelope))

    assert first.authoritative is True
    assert conflict.outcome_kind == "classification_conflict"
    assert conflict.authoritative is False
    assert conflict.effect == "no_effect"
    assert conflict.classification_result is not None
    assert conflict.classification_result.classification == "blocked_uncertain"
    assert conflict.error_code == "SAFETY_CLASSIFICATION_CONFLICT"
    assert conflicting_executor.requests == []
    with ft011_database.session() as session:
        row = session.get(SafetyClassification, message_id)
        assert row is not None
        assert row.physical_action_kind == "ph_adjustment"
    assert _classification_count(ft011_database) == 1
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_pre_provider_archive_guard_makes_no_call_or_write(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    archive_plant(ft011_database, boss, plant_id=plant.plant_id)
    pre_executor = RecordingExecutor(candidate())
    with ft011_database.session() as session:
        pre = SafetyGateClassificationService(
            session,
            model_executor=pre_executor,
        ).classify(command_for(boss, envelope_for(boss, plant)))
    assert pre.outcome_kind == "guard_denied"
    assert pre_executor.requests == []
    assert _classification_count(ft011_database) == 0


def test_post_provider_archive_denies_write_and_restore_does_not_replay(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    executor = RecordingExecutor(
        candidate(),
        before_return=lambda: archive_plant(
            ft011_database,
            boss,
            plant_id=plant.plant_id,
        ),
    )
    with ft011_database.session() as session:
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
        ).classify(command_for(boss, envelope_for(boss, plant)))
    assert outcome.outcome_kind == "guard_denied"
    assert outcome.provider_call_status == "completed"
    assert len(executor.requests) == 1
    assert _classification_count(ft011_database) == 0

    with ft011_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_post_provider_grant_revocation_denies_write_and_restore_does_not_replay(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, engineer_membership = create_actor(ft011_database, farm, "engineer")
    grant = grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    envelope = envelope_for(engineer, plant, grant_id=grant.grant_id)
    executor = RecordingExecutor(
        candidate(),
        before_return=lambda: revoke_access(
            ft011_database,
            boss,
            plant_id=plant.plant_id,
            membership_id=engineer_membership.membership_id,
        ),
    )
    with ft011_database.session() as session:
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
        ).classify(command_for(engineer, envelope))

    assert outcome.outcome_kind == "guard_denied"
    assert outcome.authoritative is False
    assert outcome.provider_call_status == "completed"
    assert len(executor.requests) == 1
    assert _classification_count(ft011_database) == 0
    grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


class _ArchiveAfterWriteGuard:
    def __init__(self, session, database, boss, plant_id):
        self._delegate = DatabaseRuntimeAuthorizationGuard(session)
        self._database = database
        self._boss = boss
        self._plant_id = plant_id
        self.calls = 0

    def current_scope(self, actor, *, plant_id):
        scope = self._delegate.current_scope(actor, plant_id=plant_id)
        self.calls += 1
        if self.calls == 2 and scope is not None:
            archive_plant(
                self._database,
                self._boss,
                plant_id=self._plant_id,
            )
        return scope


def test_archive_after_write_guard_before_insert_is_denied_without_raw_error(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    executor = RecordingExecutor(candidate())
    with ft011_database.session() as session:
        guard = _ArchiveAfterWriteGuard(
            session,
            ft011_database,
            boss,
            plant.plant_id,
        )
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
            authorization_guard=guard,
        ).classify(command_for(boss, envelope))

    assert guard.calls == 3
    assert len(executor.requests) == 1
    assert outcome.outcome_kind == "guard_denied"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_GUARD_DENIED"
    assert "database" not in str(outcome.as_value()).lower()
    assert "sql" not in str(outcome.as_value()).lower()
    with ft011_database.session() as session:
        assert session.get(Plant, plant.plant_id).status == "archived"
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


class _RevokeAfterWriteGuard:
    def __init__(self, session, database, boss, plant_id, membership_id):
        self._delegate = DatabaseRuntimeAuthorizationGuard(session)
        self._database = database
        self._boss = boss
        self._plant_id = plant_id
        self._membership_id = membership_id
        self.calls = 0

    def current_scope(self, actor, *, plant_id):
        scope = self._delegate.current_scope(actor, plant_id=plant_id)
        self.calls += 1
        if self.calls == 2 and scope is not None:
            with self._database.session() as session:
                result = FarmService(session).revoke_access(
                    self._boss,
                    plant_id=self._plant_id,
                    membership_id=self._membership_id,
                )
            assert result.changed is True
        return scope


def test_revoke_after_write_guard_before_final_locks_is_guard_denied(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, engineer_membership = create_actor(ft011_database, farm, "engineer")
    grant = grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    envelope = envelope_for(engineer, plant, grant_id=grant.grant_id)
    executor = RecordingExecutor(candidate())
    with ft011_database.session() as session:
        guard = _RevokeAfterWriteGuard(
            session,
            ft011_database,
            boss,
            plant.plant_id,
            engineer_membership.membership_id,
        )
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
            authorization_guard=guard,
        ).classify(command_for(engineer, envelope))

    assert guard.calls == 3
    assert len(executor.requests) == 1
    assert outcome.outcome_kind == "guard_denied"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_GUARD_DENIED"
    assert "database" not in str(outcome.as_value()).lower()
    assert "sql" not in str(outcome.as_value()).lower()
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_partial_guard_acquisition_serializes_with_production_revoke_without_deadlock(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, engineer_membership = create_actor(ft011_database, farm, "engineer")
    grant = grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    envelope = envelope_for(engineer, plant, grant_id=grant.grant_id)
    executor = RecordingExecutor(candidate())
    engine = ft011_database.engine()
    classifier_before_plant = threading.Event()
    allow_classifier_plant = threading.Event()
    revoker_has_plant = threading.Event()
    allow_revoker_membership = threading.Event()
    classifier_pid: list[int] = []
    deadlocks_before = _database_deadlocks(ft011_database)

    def before_cursor_execute(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        normalized = statement.lower()
        if (
            threading.current_thread().name.startswith("safety-classifier")
            and "from plants" in normalized
            and "for update" in normalized
        ):
            classifier_before_plant.set()
            assert allow_classifier_plant.wait(10)

    def after_cursor_execute(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        normalized = statement.lower()
        if (
            threading.current_thread().name.startswith("safety-revoker")
            and "from plants" in normalized
            and "for update" in normalized
        ):
            revoker_has_plant.set()
            assert allow_revoker_membership.wait(10)

    def classify():
        with engine.connect() as connection:
            classifier_pid.append(
                int(connection.scalar(text("SELECT pg_backend_pid()")))
            )
            connection.rollback()
            with OrmSession(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
            ) as session:
                return SafetyGateClassificationService(
                    session,
                    model_executor=executor,
                ).classify(command_for(engineer, envelope))

    def revoke():
        with ft011_database.session() as session:
            return FarmService(session).revoke_access(
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
            )

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        with (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="safety-classifier",
            ) as classifier_pool,
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="safety-revoker",
            ) as revoker_pool,
        ):
            classifier_future = classifier_pool.submit(classify)
            assert classifier_before_plant.wait(10)
            revoker_future = revoker_pool.submit(revoke)
            assert revoker_has_plant.wait(10)
            allow_classifier_plant.set()
            assert classifier_pid
            assert _wait_for_postgresql_lock(ft011_database, classifier_pid[0])
            allow_revoker_membership.set()
            revoke_result = revoker_future.result(timeout=10)
            outcome = classifier_future.result(timeout=10)
    finally:
        allow_classifier_plant.set()
        allow_revoker_membership.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert _database_deadlocks(ft011_database) == deadlocks_before
    assert revoke_result.changed is True
    assert outcome.outcome_kind == "guard_denied"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_GUARD_DENIED"
    safe_outcome = str(outcome.as_value()).lower()
    assert all(
        raw_term not in safe_outcome
        for raw_term in ("database", "sql", "deadlock", "psycopg")
    )
    with ft011_database.session() as session:
        assert session.get(PlantAccessGrant, grant.grant_id).status == "revoked"
    assert len(executor.requests) == 1
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_later_identity_lock_contention_restarts_without_archive_inversion(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    executor = RecordingExecutor(candidate())
    engine = ft011_database.engine()
    classifier_before_account = threading.Event()
    allow_classifier_account = threading.Event()
    archiver_pid_ready = threading.Event()
    archiver_pid: list[int] = []
    deadlocks_before = _database_deadlocks(ft011_database)

    def before_cursor_execute(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        normalized = statement.lower()
        if (
            threading.current_thread().name.startswith("safety-classifier")
            and "from accounts" in normalized
            and "for update nowait" in normalized
        ):
            classifier_before_account.set()
            assert allow_classifier_account.wait(10)

    def classify():
        with ft011_database.session() as session:
            return SafetyGateClassificationService(
                session,
                model_executor=executor,
            ).classify(command_for(boss, envelope))

    def archive():
        with engine.connect() as connection:
            archiver_pid.append(int(connection.scalar(text("SELECT pg_backend_pid()"))))
            connection.rollback()
            archiver_pid_ready.set()
            with OrmSession(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
            ) as session:
                return FarmService(session).archive_plant(
                    boss,
                    plant_id=plant.plant_id,
                )

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        with (
            ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="safety-classifier",
            ) as classifier_pool,
            ThreadPoolExecutor(max_workers=1) as archiver_pool,
        ):
            classifier_future = classifier_pool.submit(classify)
            assert classifier_before_account.wait(10)
            archiver_future = archiver_pool.submit(archive)
            assert archiver_pid_ready.wait(10)
            assert _wait_for_postgresql_lock(ft011_database, archiver_pid[0])
            allow_classifier_account.set()
            archive_result = archiver_future.result(timeout=10)
            outcome = classifier_future.result(timeout=10)
    finally:
        allow_classifier_account.set()
        event.remove(engine, "before_cursor_execute", before_cursor_execute)

    assert _database_deadlocks(ft011_database) == deadlocks_before
    assert archive_result.changed is True
    assert outcome.outcome_kind == "guard_denied"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_GUARD_DENIED"
    assert len(executor.requests) == 1
    with ft011_database.session() as session:
        assert session.get(Plant, plant.plant_id).status == "archived"
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


class _PauseAfterGuardLocksRepository(SafetyClassificationRepository):
    def __init__(self, session, locked, allow_persist):
        super().__init__(session)
        self._locked = locked
        self._allow_persist = allow_persist

    def lock_current_guard_rows(self, actor, *, plant_id):
        super().lock_current_guard_rows(actor, plant_id=plant_id)
        self._locked.set()
        assert self._allow_persist.wait(10)


def test_revoke_after_all_classifier_locks_serializes_after_classification(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, engineer_membership = create_actor(ft011_database, farm, "engineer")
    grant = grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    envelope = envelope_for(engineer, plant, grant_id=grant.grant_id)
    executor = RecordingExecutor(candidate())
    all_guard_rows_locked = threading.Event()
    allow_classification_persist = threading.Event()
    revoker_pid_ready = threading.Event()
    revoker_pid: list[int] = []
    engine = ft011_database.engine()
    deadlocks_before = _database_deadlocks(ft011_database)

    def classify():
        with ft011_database.session() as session:
            repository = _PauseAfterGuardLocksRepository(
                session,
                all_guard_rows_locked,
                allow_classification_persist,
            )
            return SafetyGateClassificationService(
                session,
                model_executor=executor,
                repository=repository,
            ).classify(command_for(engineer, envelope))

    def revoke():
        with engine.connect() as connection:
            revoker_pid.append(int(connection.scalar(text("SELECT pg_backend_pid()"))))
            connection.rollback()
            revoker_pid_ready.set()
            with OrmSession(
                bind=connection,
                autoflush=False,
                expire_on_commit=False,
            ) as session:
                return FarmService(session).revoke_access(
                    boss,
                    plant_id=plant.plant_id,
                    membership_id=engineer_membership.membership_id,
                )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            classifier_future = pool.submit(classify)
            assert all_guard_rows_locked.wait(10)
            revoker_future = pool.submit(revoke)
            assert revoker_pid_ready.wait(10)
            assert _wait_for_postgresql_lock(ft011_database, revoker_pid[0])
            allow_classification_persist.set()
            outcome = classifier_future.result(timeout=10)
            revoke_result = revoker_future.result(timeout=10)
    finally:
        allow_classification_persist.set()

    assert _database_deadlocks(ft011_database) == deadlocks_before
    assert outcome.outcome_kind == "classification_persisted"
    assert outcome.authoritative is True
    assert outcome.effect == "evidence_written"
    assert outcome.error_code is None
    assert revoke_result.changed is True
    with ft011_database.session() as session:
        assert session.get(PlantAccessGrant, grant.grant_id).status == "revoked"
    assert len(executor.requests) == 1
    assert _classification_count(ft011_database) == 1
    assert _downstream_counts(ft011_database) == (0, 0, 0)


class _WriteFailureRepository(SafetyClassificationRepository):

    def persist_first(self, _row):
        raise RuntimeError("synthetic persistence failure raw=candidate")


class _AlwaysBusyGuardRepository(SafetyClassificationRepository):
    def __init__(self, session):
        super().__init__(session)
        self.lock_attempts = 0

    def lock_current_guard_rows(self, _actor, *, plant_id):
        self.lock_attempts += 1
        raise CurrentGuardLockUnavailable


def test_guard_lock_restart_is_bounded_and_never_repeats_provider_io(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    executor = RecordingExecutor(candidate())
    with ft011_database.session() as session:
        repository = _AlwaysBusyGuardRepository(session)
        outcome = SafetyGateClassificationService(
            session,
            model_executor=executor,
            repository=repository,
        ).classify(command_for(boss, envelope))

    assert repository.lock_attempts == 3
    assert len(executor.requests) == 1
    assert outcome.outcome_kind == "persistence_failed"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.provider_call_status == "completed"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED"
    assert _classification_count(ft011_database) == 0
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_persistence_failure_is_redacted_no_effect(ft011_database, ft011_seed):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    with ft011_database.session() as session:
        outcome = SafetyGateClassificationService(
            session,
            model_executor=RecordingExecutor(candidate()),
            repository=_WriteFailureRepository(session),
        ).classify(command_for(boss, envelope))
    assert outcome.outcome_kind == "persistence_failed"
    assert outcome.authoritative is False
    assert outcome.effect == "no_effect"
    assert outcome.error_code == "SAFETY_CLASSIFICATION_PERSISTENCE_FAILED"
    assert "synthetic" not in str(outcome.as_value())
    assert "candidate" not in str(outcome.as_value())
    assert _classification_count(ft011_database) == 0


def test_concurrent_identical_digests_commit_once_across_safe_model_refs(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    barrier = threading.Barrier(2)

    def invoke(model_ref):
        executor = RecordingExecutor(candidate(), before_return=lambda: barrier.wait(10))
        executor.model_ref = model_ref
        with ft011_database.session() as session:
            outcome = SafetyGateClassificationService(
                session,
                model_executor=executor,
            ).classify(command_for(boss, envelope))
        return outcome, len(executor.requests)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=20)
            for future in [
                pool.submit(invoke, "test_provider:safety_v1"),
                pool.submit(invoke, "alternate_test:safety_v1"),
            ]
        ]

    outcomes = [item[0] for item in results]
    assert {item.outcome_kind for item in outcomes} == {
        "classification_persisted",
        "classification_idempotent",
    }
    assert all(item.authoritative for item in outcomes)
    assert [item[1] for item in results] == [1, 1]
    assert _classification_count(ft011_database) == 1
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_concurrent_conflicting_results_keep_first_and_return_no_effect(
    ft011_database,
    ft011_seed,
):
    _farm, boss, _membership, plant = ft011_seed
    envelope = envelope_for(boss, plant)
    barrier = threading.Barrier(2)
    results = [candidate("safe_information"), candidate(action_kind="dosing_command")]

    def invoke(raw):
        executor = RecordingExecutor(raw, before_return=lambda: barrier.wait(10))
        with ft011_database.session() as session:
            return SafetyGateClassificationService(
                session,
                model_executor=executor,
            ).classify(command_for(boss, envelope))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke, raw) for raw in results]
        outcomes = [future.result(timeout=20) for future in futures]

    assert sum(item.authoritative for item in outcomes) == 1
    conflict = next(item for item in outcomes if not item.authoritative)
    assert conflict.outcome_kind == "classification_conflict"
    assert conflict.effect == "no_effect"
    assert conflict.error_code == "SAFETY_CLASSIFICATION_CONFLICT"
    assert _classification_count(ft011_database) == 1
    assert _downstream_counts(ft011_database) == (0, 0, 0)


def test_model_and_postgresql_schema_enforce_exact_safe_authority_shape(
    ft011_database,
):
    table = SafetyClassification.__table__
    assert isinstance(table.c.message_id.type, Uuid)
    assert isinstance(table.c.farm_id.type, Uuid)
    assert isinstance(table.c.plant_id.type, Uuid)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in table.foreign_keys)
    names = {item.name for item in table.constraints if item.name}
    assert {
        "ck_safety_classifications_classifier_version",
        "ck_safety_classifications_result_matrix",
        "ck_safety_classifications_provider_failure_closed",
        "ck_safety_classifications_model_ref",
        "ck_safety_classifications_input_sha256",
        "ck_safety_classifications_result_sha256",
    } <= names

    inspector = inspect(ft011_database.engine())
    columns = {item["name"]: item for item in inspector.get_columns("safety_classifications")}
    assert set(columns) == {
        "message_id",
        "farm_id",
        "plant_id",
        "origin_agent_id",
        "classifier_version",
        "classification",
        "safe_task_kind",
        "reason_code",
        "physical_action_kind",
        "provider_status",
        "model_ref",
        "input_sha256",
        "result_sha256",
        "created_at",
    }
    assert all(
        forbidden not in columns
        for forbidden in (
            "candidate_output",
            "provider_request",
            "provider_response",
            "prompt",
            "reasoning",
            "credentials",
            "authorization_scope",
            "source_refs",
        )
    )
    assert isinstance(columns["message_id"]["type"], Uuid)
    assert all(
        item["options"]["ondelete"] == "RESTRICT"
        for item in inspector.get_foreign_keys("safety_classifications")
    )


def test_postgresql_rejects_invalid_result_matrix(ft011_database, ft011_seed):
    farm, _boss, _membership, plant = ft011_seed
    with pytest.raises(IntegrityError):
        with ft011_database.session() as session, session.begin():
            session.add(
                SafetyClassification(
                    message_id=uuid.uuid4(),
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    origin_agent_id="hydroponics_advisor",
                    classifier_version="safety_gate_v1",
                    classification="safe_information",
                    safe_task_kind="measurement",
                    reason_code="non_physical_information",
                    physical_action_kind=None,
                    provider_status="completed",
                    model_ref="test_provider:safety_v1",
                    input_sha256="a" * 64,
                    result_sha256="b" * 64,
                    created_at=datetime.now(timezone.utc),
                )
            )


def test_ft011_revision_is_ordered_head_and_guarded():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("head")
    assert revision is not None
    assert revision.revision == "ft012_runtime_dispositions"
    assert revision.down_revision == "ft012_task_approval_outcomes"
    ft012 = script.get_revision("ft012_task_approval_outcomes")
    assert ft012 is not None
    assert ft012.down_revision == "ft011_safety_action_decisions"
    decisions_revision = script.get_revision("ft011_safety_action_decisions")
    assert decisions_revision is not None
    assert decisions_revision.down_revision == "ft011_safety_classifications"
    classification_revision = script.get_revision("ft011_safety_classifications")
    assert classification_revision is not None
    assert classification_revision.down_revision == "ft009_plant_state"
    source = Path(classification_revision.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "downgrade refused" in source
    assert "SELECT EXISTS (SELECT 1 FROM safety_classifications LIMIT 1)" in source
    for forbidden in (
        "candidate_output",
        "provider_request",
        "provider_response",
        "raw_candidate",
        "prompt",
        "reasoning",
        "credentials",
    ):
        assert forbidden not in source
