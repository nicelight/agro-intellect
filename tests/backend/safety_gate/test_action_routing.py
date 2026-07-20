from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from sqlalchemy import func, select

from backend.app.access_admin.farm_service import FarmService
from backend.app.agent_chat import (
    AgentBusEvent,
    AgentChatContractError,
    UIFeedEvent,
    UIFeedEventV1,
)
from backend.app.plant_operations import ManualMeasurement
from backend.app.safety_gate import (
    SafetyActionDecision,
    SafetyActionDecisionCommandV1,
    SafetyActionDecisionRepository,
    SafetyActionDecisionService,
    SafetyClassification,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
    revoke_access,
)


NOW = datetime(2026, 7, 20, 6, 0, tzinfo=timezone.utc)
SUPPORTED = ("ph_adjustment", "ec_adjustment", "solution_change")
UNSUPPORTED = (
    "pump_command",
    "light_command",
    "dosing_command",
    "pruning",
    "transplanting",
    "root_trimming",
    "other_physical_action",
)


def _classification(database, farm, plant, *, action_kind, origin="hydroponics_advisor"):
    message_id = uuid.uuid4()
    digest = hashlib.sha256(f"{message_id}:{action_kind}".encode()).hexdigest()
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id=origin,
                classifier_version="safety_gate_v1",
                classification="physical_action",
                safe_task_kind=None,
                reason_code="physical_action_detected",
                physical_action_kind=action_kind,
                provider_status="completed",
                model_ref="test_provider:safety_v1",
                input_sha256=digest,
                result_sha256=digest,
            )
        )
    return message_id


def _measurement(database, actor, plant, *, measured_at, ph=None, ec=None):
    measurement_id = uuid.uuid4()
    with database.session() as session, session.begin():
        session.add(
            ManualMeasurement(
                measurement_id=measurement_id,
                farm_id=actor.farm_id,
                plant_id=plant.plant_id,
                check_in_id=None,
                actor_account_id=actor.account_id,
                actor_membership_id=actor.membership_id,
                measured_at=measured_at,
                recorded_at=NOW,
                ph=Decimal(str(ph)) if ph is not None else None,
                ec_ms_cm=Decimal(str(ec)) if ec is not None else None,
                provenance_note=None,
                source_type="manual_user",
                source_refs={"source": "synthetic-authoritative-test"},
                trust_status="confirmed",
                event_refs={},
            )
        )
    return measurement_id


def _command(actor, message_id, *, decision_id=None):
    return SafetyActionDecisionCommandV1(
        decision_id=decision_id or uuid.uuid4(),
        actor_context=actor,
        classification_message_id=message_id,
    )


def _evaluate(database, command, *, repository=None, clock=lambda: NOW):
    with database.session() as session:
        service = SafetyActionDecisionService(
            session,
            repository=repository(session) if repository else None,
            clock=clock,
        )
        return service.evaluate(command)


def _rows(database):
    with database.session() as session:
        decisions = list(session.scalars(select(SafetyActionDecision)))
        ui = list(
            session.scalars(
                select(UIFeedEvent).where(UIFeedEvent.display_kind == "safety_status")
            )
        )
        bus = session.scalar(select(func.count(AgentBusEvent.event_id)))
    return decisions, ui, bus


def _blocked_ui_value():
    decision_id = uuid.uuid4()
    message_id = uuid.uuid4()
    return {
        "schema_version": 1,
        "ui_event_id": str(decision_id),
        "created_at": NOW.isoformat().replace("+00:00", "Z"),
        "farm_id": str(uuid.uuid4()),
        "plant_id": str(uuid.uuid4()),
        "source_type": "safety",
        "source_id": str(decision_id),
        "source_refs": [
            f"message_envelope:{message_id}",
            f"safety_classification:{message_id}",
        ],
        "display_kind": "safety_status",
        "display_payload": {
            "payload_kind": "safety_status",
            "decision_ref": f"safety_decision:{decision_id}",
            "classification_ref": f"safety_classification:{message_id}",
            "action_kind": "dosing_command",
            "safety_status": "safety_blocked",
            "reason_code": "unsupported_action",
            "summary_text": "Действие не поддерживается безопасным процессом MVP.",
            "evidence_refs": [],
            "approval_input_freshness": None,
            "expires_at": None,
        },
        "visible_to_roles": ["boss", "engineer"],
        "visible_to_agents": False,
        "consumable_by_agents": False,
    }


@pytest.mark.parametrize("action_kind", SUPPORTED)
def test_supported_actions_reach_only_pending_human_approval(
    ft011_database,
    ft011_seed,
    action_kind,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind=action_kind,
    )
    evidence_id = _measurement(
        ft011_database,
        boss,
        plant,
        measured_at=NOW - timedelta(minutes=30),
        ph="6.10",
        ec="1.700",
    )
    outcome = _evaluate(ft011_database, _command(boss, message_id))

    assert outcome.authoritative is True
    assert outcome.safety_status == "pending_human_approval"
    assert outcome.reason_code == "ready_for_human_approval"
    assert outcome.expires_at == NOW + timedelta(hours=1, minutes=30)
    decisions, ui, bus = _rows(ft011_database)
    assert len(decisions) == len(ui) == 1 and bus == 0
    decision = decisions[0]
    event = ui[0]
    assert decision.ph_measurement_id == decision.ec_measurement_id == evidence_id
    assert event.ui_event_id == decision.decision_id
    assert event.visible_to_agents is event.consumable_by_agents is False
    assert event.visible_to_roles == ["boss", "engineer"]
    assert event.display_payload["evidence_refs"] == [
        f"manual_measurement:{evidence_id}"
    ]
    assert "candidate" not in str(event.display_payload).lower()


def test_safety_status_contract_rejects_unknown_or_inconsistent_payloads():
    valid = _blocked_ui_value()
    parsed = UIFeedEventV1.from_untrusted(valid)
    assert parsed.display_kind == "safety_status"
    cases = []
    unknown = deepcopy(valid)
    unknown["display_payload"]["candidate_output"] = "do not expose"
    cases.append(unknown)
    wrong_summary = deepcopy(valid)
    wrong_summary["display_payload"]["summary_text"] = "Добавьте раствор"
    cases.append(wrong_summary)
    wrong_route = deepcopy(valid)
    wrong_route["display_payload"]["safety_status"] = "pending_human_approval"
    cases.append(wrong_route)
    wrong_roles = deepcopy(valid)
    wrong_roles["visible_to_roles"] = ["boss", "engineer", "consultant"]
    cases.append(wrong_roles)
    for value in cases:
        with pytest.raises(AgentChatContractError):
            UIFeedEventV1.from_untrusted(value)


@pytest.mark.parametrize("action_kind", UNSUPPORTED)
def test_every_unsupported_action_is_blocked_without_evidence(
    ft011_database,
    ft011_seed,
    action_kind,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind=action_kind,
    )
    outcome = _evaluate(ft011_database, _command(boss, message_id))
    assert outcome.safety_status == "safety_blocked"
    assert outcome.reason_code == "unsupported_action"
    decision = _rows(ft011_database)[0][0]
    assert decision.ph_status is decision.ec_status is None
    assert decision.ph_measurement_id is decision.ec_measurement_id is None
    assert decision.expires_at is None


@pytest.mark.parametrize(
    ("role", "approve_flag", "expected"),
    (
        ("engineer", True, "pending_human_approval"),
        ("engineer", False, "safety_blocked"),
        ("consultant", False, "safety_blocked"),
    ),
)
def test_current_role_and_grant_approval_matrix(
    ft011_database,
    ft011_seed,
    role,
    approve_flag,
    expected,
):
    farm, boss, _membership, plant = ft011_seed
    actor, membership = create_actor(ft011_database, farm, role)
    with ft011_database.session() as session:
        FarmService(session).grant_access(
            boss,
            plant_id=plant.plant_id,
            membership_id=membership.membership_id,
            plant_approve_actions=approve_flag,
        )
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="ec_adjustment",
    )
    if approve_flag:
        _measurement(
            ft011_database,
            actor,
            plant,
            measured_at=NOW - timedelta(minutes=15),
            ph="6.00",
            ec="1.500",
        )
    outcome = _evaluate(ft011_database, _command(actor, message_id))
    assert outcome.safety_status == expected
    assert outcome.reason_code == (
        "ready_for_human_approval"
        if expected == "pending_human_approval"
        else "approval_authority_missing"
    )


@pytest.mark.parametrize(
    ("ph_time", "ec_time", "ph_status", "ec_status"),
    (
        (None, None, "missing", "missing"),
        (None, NOW - timedelta(minutes=10), "missing", "fresh"),
        (NOW - timedelta(minutes=10), None, "fresh", "missing"),
        (NOW - timedelta(hours=3), NOW - timedelta(minutes=10), "stale", "fresh"),
        (NOW + timedelta(seconds=1), NOW - timedelta(minutes=10), "stale", "fresh"),
        (NOW - timedelta(hours=2), NOW - timedelta(hours=2), "fresh", "fresh"),
    ),
)
def test_independent_two_hour_freshness_is_closed_and_not_analysis_window(
    ft011_database,
    ft011_seed,
    ph_time,
    ec_time,
    ph_status,
    ec_status,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="solution_change",
    )
    if ph_time is not None:
        _measurement(ft011_database, boss, plant, measured_at=ph_time, ph="6.20")
    if ec_time is not None:
        _measurement(ft011_database, boss, plant, measured_at=ec_time, ec="1.800")
    outcome = _evaluate(ft011_database, _command(boss, message_id))
    decision = _rows(ft011_database)[0][0]
    assert (decision.ph_status, decision.ec_status) == (ph_status, ec_status)
    if (ph_status, ec_status) == ("fresh", "fresh"):
        assert outcome.safety_status == "pending_human_approval"
        assert outcome.expires_at == NOW
    else:
        assert outcome.safety_status == "needs_fresh_evidence"
        assert outcome.expires_at is None


def test_identical_retry_is_inert_and_conflicting_retry_fails_closed(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="dosing_command",
    )
    command = _command(boss, message_id)
    first = _evaluate(ft011_database, command)
    duplicate = _evaluate(ft011_database, command, clock=lambda: NOW + timedelta(hours=1))
    conflict = _evaluate(ft011_database, _command(boss, message_id))
    assert first.outcome_kind == "decision_persisted"
    assert duplicate.outcome_kind == "decision_idempotent"
    assert duplicate.effect == "evidence_duplicate"
    assert conflict.outcome_kind == "decision_conflict"
    assert conflict.error_code == "SAFETY_DECISION_CONFLICT"
    decisions, ui, bus = _rows(ft011_database)
    assert len(decisions) == len(ui) == 1 and bus == 0


class _FailAfterDecisionFlush(SafetyActionDecisionRepository):
    def persist_first(self, decision, projection):
        self._session.add(decision)
        self._session.flush()
        raise RuntimeError("synthetic atomic rollback")


def test_decision_and_projection_roll_back_together(ft011_database, ft011_seed):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="light_command",
    )
    outcome = _evaluate(
        ft011_database,
        _command(boss, message_id),
        repository=_FailAfterDecisionFlush,
    )
    assert outcome.outcome_kind == "persistence_failed"
    assert outcome.error_code == "SAFETY_DECISION_PERSISTENCE_FAILED"
    decisions, ui, bus = _rows(ft011_database)
    assert decisions == [] and ui == [] and bus == 0


def test_companion_and_non_physical_classification_are_ineligible(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="ph_adjustment",
        origin="companion",
    )
    outcome = _evaluate(ft011_database, _command(boss, message_id))
    assert outcome.outcome_kind == "classification_ineligible"
    assert _rows(ft011_database) == ([], [], 0)


def test_revoke_archive_and_restore_do_not_replay_a_decision(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, membership = create_actor(ft011_database, farm, "engineer")
    grant_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="pump_command",
    )
    revoke_access(
        ft011_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=membership.membership_id,
    )
    revoked = _evaluate(ft011_database, _command(engineer, message_id))
    assert revoked.outcome_kind == "guard_denied"
    assert _rows(ft011_database) == ([], [], 0)

    boss_command = _command(boss, message_id)
    first = _evaluate(ft011_database, boss_command)
    archive_plant(ft011_database, boss, plant_id=plant.plant_id)
    archived_retry = _evaluate(ft011_database, boss_command)
    assert first.outcome_kind == "decision_persisted"
    assert archived_retry.outcome_kind == "guard_denied"
    with ft011_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)
    restored_retry = _evaluate(ft011_database, boss_command)
    assert restored_retry.outcome_kind == "decision_idempotent"
    decisions, ui, bus = _rows(ft011_database)
    assert len(decisions) == len(ui) == 1 and bus == 0


def test_engineer_without_current_grant_is_guard_denied(ft011_database, ft011_seed):
    farm, _boss, _membership, plant = ft011_seed
    engineer, _membership = create_actor(ft011_database, farm, "engineer")
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="solution_change",
    )
    outcome = _evaluate(ft011_database, _command(engineer, message_id))
    assert outcome.outcome_kind == "guard_denied"
    assert _rows(ft011_database) == ([], [], 0)


def test_concurrent_different_decision_ids_are_first_write_wins(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="root_trimming",
    )
    commands = (_command(boss, message_id), _command(boss, message_id))
    barrier = threading.Barrier(2)

    def run(command):
        barrier.wait(timeout=5)
        return _evaluate(ft011_database, command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, commands))
    assert {item.outcome_kind for item in outcomes} == {
        "decision_persisted",
        "decision_conflict",
    }
    decisions, ui, bus = _rows(ft011_database)
    assert len(decisions) == len(ui) == 1 and bus == 0


def test_archive_committed_before_final_guard_writes_no_decision_or_projection(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="pump_command",
    )
    before_locks = threading.Event()
    continue_locks = threading.Event()

    class PauseBeforeLocks(SafetyActionDecisionRepository):
        def lock_current_guard_rows(self, actor, *, plant_id):
            before_locks.set()
            assert continue_locks.wait(timeout=5)
            return super().lock_current_guard_rows(actor, plant_id=plant_id)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            _evaluate,
            ft011_database,
            _command(boss, message_id),
            repository=PauseBeforeLocks,
        )
        assert before_locks.wait(timeout=5)
        archive_plant(ft011_database, boss, plant_id=plant.plant_id)
        continue_locks.set()
        outcome = future.result(timeout=5)
    assert outcome.outcome_kind == "guard_denied"
    assert _rows(ft011_database) == ([], [], 0)


def test_revoke_committed_before_final_guard_writes_no_decision_or_projection(
    ft011_database,
    ft011_seed,
):
    farm, boss, _membership, plant = ft011_seed
    engineer, membership = create_actor(ft011_database, farm, "engineer")
    with ft011_database.session() as session:
        FarmService(session).grant_access(
            boss,
            plant_id=plant.plant_id,
            membership_id=membership.membership_id,
            plant_approve_actions=True,
        )
    message_id = _classification(
        ft011_database,
        farm,
        plant,
        action_kind="ec_adjustment",
    )
    before_locks = threading.Event()
    continue_locks = threading.Event()

    class PauseBeforeLocks(SafetyActionDecisionRepository):
        def lock_current_guard_rows(self, actor, *, plant_id):
            before_locks.set()
            assert continue_locks.wait(timeout=5)
            return super().lock_current_guard_rows(actor, plant_id=plant_id)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            _evaluate,
            ft011_database,
            _command(engineer, message_id),
            repository=PauseBeforeLocks,
        )
        assert before_locks.wait(timeout=5)
        revoke_access(
            ft011_database,
            boss,
            plant_id=plant.plant_id,
            membership_id=membership.membership_id,
        )
        continue_locks.set()
        outcome = future.result(timeout=5)
    assert outcome.outcome_kind == "guard_denied"
    assert _rows(ft011_database) == ([], [], 0)
