from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
from decimal import Decimal
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app import AppSettings
from backend.app.agent_runtime.contracts import SafetyClassificationResultV1
from backend.app.access_admin.farm_service import FarmService
from backend.app.plant_operations import ManualMeasurement
from backend.app.safety_gate import SafetyActionDecision, SafetyClassification
from backend.app.task_follow_up import (
    Approval,
    ApprovalDecisionCommandV1,
    ApprovalStatus,
    ClassifiedMessageTaskCommandV1,
    CompleteTaskCommandV1,
    Outcome,
    OutcomeValue,
    OrdinaryTaskDispatchDisposition,
    RecordOutcomeCommandV1,
    Task,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskFollowUpRepository,
    TaskFollowUpService,
    TaskKind,
)
from backend.app.task_follow_up.contracts import canonical_fingerprint
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
)
from tests.backend.safety_gate.helpers import envelope_for


NOW = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _apply_task_follow_up_cleanup_revision(ft012_database):
    script = ScriptDirectory.from_config(
        build_alembic_config(AppSettings.from_env())
    )
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            script.get_revision("ft012_runtime_dispositions").module.upgrade()
            script.get_revision(
                "ft012_simplify_follow_up_runtime"
            ).module.upgrade()
        connection.commit()


def _measurement(database, actor, plant, *, ph=None, ec=None, measured_at=NOW):
    row = ManualMeasurement(
        measurement_id=uuid.uuid4(), farm_id=actor.farm_id,
        plant_id=plant.plant_id, check_in_id=None,
        actor_account_id=actor.account_id,
        actor_membership_id=actor.membership_id,
        measured_at=measured_at, recorded_at=NOW,
        ph=Decimal(str(ph)) if ph is not None else None,
        ec_ms_cm=Decimal(str(ec)) if ec is not None else None,
        provenance_note=None, source_type="manual_user",
        source_refs={"source": "synthetic-ft012"},
        trust_status="confirmed", event_refs={},
    )
    with database.session() as session, session.begin():
        session.add(row)
    return row


def _pending_decision(
    database, farm, actor, plant, *, expires_at=NOW,
    action_kind="ph_adjustment", instant=NOW,
):
    ph = _measurement(database, actor, plant, ph="6.10", measured_at=instant)
    ec = _measurement(database, actor, plant, ec="1.900", measured_at=instant)
    message_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    digest = "a" * 64
    with database.session() as session, session.begin():
        session.add(SafetyClassification(
            message_id=message_id, farm_id=farm.farm_id, plant_id=plant.plant_id,
            origin_agent_id="hydroponics_advisor", classifier_version="safety_gate_v1",
            classification="physical_action", safe_task_kind=None,
            reason_code="physical_action_detected", physical_action_kind=action_kind,
            provider_status="completed", model_ref="test:safety", input_sha256=digest,
            result_sha256=digest,
        ))
        session.flush()
        session.add(SafetyActionDecision(
            decision_id=decision_id, classification_message_id=message_id,
            farm_id=farm.farm_id, plant_id=plant.plant_id,
            actor_account_id=actor.account_id,
            actor_membership_id=actor.membership_id,
            actor_role_preset="boss", permission_source="boss_role", grant_id=None,
            action_kind=action_kind, safety_status="pending_human_approval",
            reason_code="ready_for_human_approval",
            ph_measurement_id=ph.measurement_id, ec_measurement_id=ec.measurement_id,
            ph_status="fresh", ec_status="fresh",
            ph_measured_at=ph.measured_at, ec_measured_at=ec.measured_at,
            expires_at=expires_at, evaluated_at=instant, created_at=instant,
            summary_text={
                "ph_adjustment": "Предложена ручная корректировка pH. Требуется решение уполномоченного пользователя.",
                "ec_adjustment": "Предложена ручная корректировка EC питательного раствора. Требуется решение уполномоченного пользователя.",
                "solution_change": "Предложена ручная замена питательного раствора. Требуется решение уполномоченного пользователя.",
            }[action_kind],
        ))
    return decision_id, ph, ec


def _approval_command(actor, plant, decision_id, *, request_id=None, decision="approved"):
    return ApprovalDecisionCommandV1(
        actor_context=actor, plant_id=plant.plant_id,
        safety_decision_id=decision_id, request_id=request_id or uuid.uuid4(),
        expected_version=1, decision=ApprovalStatus(decision),
    )


def _ordinary_command(
    database,
    farm,
    actor,
    plant,
    *,
    envelope=None,
    run_id=None,
):
    envelope = envelope or envelope_for(
        actor,
        plant,
        candidate_output="Проверить состояние листьев.",
        candidate_claim_type="task_request",
    )
    if run_id is not None:
        envelope = replace(envelope, run_id=run_id)
    classification = SafetyClassificationResultV1.from_untrusted({
        "schema_version": 1,
        "message_id": str(envelope.message_id),
        "classifier_version": "safety_gate_v1",
        "classification": "safe_task_request",
        "safe_task_kind": "check",
        "reason_code": "safe_check_request",
    })
    with database.session() as session, session.begin():
        session.add(SafetyClassification(
            message_id=envelope.message_id,
            farm_id=farm.farm_id,
            plant_id=plant.plant_id,
            origin_agent_id=envelope.agent_id,
            classifier_version="safety_gate_v1",
            classification="safe_task_request",
            safe_task_kind="check",
            reason_code="safe_check_request",
            physical_action_kind=None,
            provider_status="completed",
            model_ref="test:safety",
            input_sha256=canonical_fingerprint(envelope.as_value()),
            result_sha256="d" * 64,
        ))
    return ClassifiedMessageTaskCommandV1(
        actor_context=actor,
        message_envelope=envelope,
        classification=classification,
        task_kind=TaskKind.CHECK,
    )


def test_matched_ordinary_task_is_authoritative_literal_and_idempotent(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    envelope = envelope_for(
        boss, plant, candidate_output="<b>Проверьте листья</b> — это literal data.",
        candidate_claim_type="task_request",
    )
    result = SafetyClassificationResultV1.from_untrusted({
        "schema_version": 1, "message_id": str(envelope.message_id),
        "classifier_version": "safety_gate_v1",
        "classification": "safe_task_request", "safe_task_kind": "check",
        "reason_code": "safe_check_request",
    })
    with ft012_database.session() as session, session.begin():
        session.add(SafetyClassification(
            message_id=envelope.message_id, farm_id=farm.farm_id,
            plant_id=plant.plant_id, origin_agent_id=envelope.agent_id,
            classifier_version="safety_gate_v1", classification="safe_task_request",
            safe_task_kind="check", reason_code="safe_check_request",
            physical_action_kind=None, provider_status="completed",
            model_ref="test:safety", input_sha256=canonical_fingerprint(envelope.as_value()),
            result_sha256="b" * 64,
        ))
    command = ClassifiedMessageTaskCommandV1(
        actor_context=boss, message_envelope=envelope,
        classification=result, task_kind=TaskKind.CHECK,
    )
    with ft012_database.session() as session:
        created = TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).create_ordinary_task(command)
    with ft012_database.session() as session:
        duplicate = TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).create_ordinary_task(command)
    assert created.result == "created" and duplicate.result == "duplicate"
    assert created.task.task_id == duplicate.task.task_id
    assert created.task.display_text == envelope.candidate_output
    assert [event.event_type for event in task_timeline.events] == ["task_created"]
    with ft012_database.session() as session:
        assert session.scalar(select(func.count(Task.task_id))) == 1
        assert session.scalar(select(func.count(Approval.approval_id))) == 0
    conflicting = replace(envelope, candidate_output="Другой текст")
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as conflict:
            TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).create_ordinary_task(
                ClassifiedMessageTaskCommandV1(
                    actor_context=boss, message_envelope=conflicting,
                    classification=result, task_kind=TaskKind.CHECK,
                )
            )
    assert conflict.value.code is TaskFollowUpErrorCode.TASK_VERSION_CONFLICT


def test_consumed_retry_requires_current_task_authority_without_exposing_task(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    command = _ordinary_command(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        created = TaskFollowUpService(
            session,
            timeline_appender=task_timeline,
            clock=lambda: NOW,
        ).create_ordinary_task(command)

    archive_plant(ft012_database, boss, plant_id=plant.plant_id)
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            ).create_ordinary_task(command)
    assert denied.value.code is TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE
    assert str(denied.value) == "TASK_PLANT_NOT_ACTIVE"
    with ft012_database.session() as session:
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            command.message_envelope.message_id,
        )
        assert disposition is not None
        assert disposition.outcome == "consumed"
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.task_id == created.task.task_id
            )
        ) == 1


def test_archived_ordinary_denial_is_terminal_and_both_new_identities_are_required(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    command = _ordinary_command(ft012_database, farm, boss, plant)
    archive_plant(ft012_database, boss, plant_id=plant.plant_id)

    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as first_denial:
            TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).create_ordinary_task(command)
    assert first_denial.value.code is TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE
    with ft012_database.session() as session:
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            command.message_envelope.message_id,
        )
        assert disposition is not None
        assert disposition.run_id == command.message_envelope.run_id
        assert disposition.outcome == "denied"
        assert disposition.denial_code == "TASK_PLANT_NOT_ACTIVE"
        assert session.scalar(select(func.count(Task.task_id))) == 0

    with ft012_database.session() as session:
        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)

    class NoGuardReevaluationRepository(TaskFollowUpRepository):
        def lock_current_scope(self, *_args, **_kwargs):
            raise AssertionError("terminal denial must be read before guard evaluation")

    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as stored_denial:
            TaskFollowUpService(
                session,
                repository=NoGuardReevaluationRepository(session),
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            ).create_ordinary_task(command)
    assert stored_denial.value.code is TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE

    changed_run = replace(
        command.message_envelope,
        run_id=uuid.uuid4(),
    )
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as same_message_conflict:
            TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).create_ordinary_task(replace(command, message_envelope=changed_run))
    assert same_message_conflict.value.code is TaskFollowUpErrorCode.TASK_VERSION_CONFLICT

    same_run_new_message = _ordinary_command(
        ft012_database,
        farm,
        boss,
        plant,
        run_id=command.message_envelope.run_id,
    )
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as same_run_conflict:
            TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).create_ordinary_task(same_run_new_message)
    assert same_run_conflict.value.code is TaskFollowUpErrorCode.TASK_VERSION_CONFLICT

    new_invocation = _ordinary_command(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        created = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).create_ordinary_task(new_invocation)
    assert created.result == "created"
    assert task_timeline.events[-1].event_type == "task_created"


def test_disposition_rolls_back_with_audit_failure_then_concurrent_retry_consumes_once(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    command = _ordinary_command(ft012_database, farm, boss, plant)

    def fail_audit(_event):
        raise RuntimeError("synthetic timeline failure")

    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as failed:
            TaskFollowUpService(
                session, timeline_appender=fail_audit, clock=lambda: NOW
            ).create_ordinary_task(command)
    assert failed.value.code is TaskFollowUpErrorCode.TASK_AUDIT_FAILED
    with ft012_database.session() as session:
        assert session.get(
            OrdinaryTaskDispatchDisposition,
            command.message_envelope.message_id,
        ) is None
        assert session.scalar(select(func.count(Task.task_id))) == 0

    def consume():
        with ft012_database.session() as session:
            return TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).create_ordinary_task(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _index: consume(), range(2)))
    assert {result.result for result in results} == {"created", "duplicate"}
    assert len({result.task.task_id for result in results}) == 1
    with ft012_database.session() as session:
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            command.message_envelope.message_id,
        )
        assert disposition is not None
        assert disposition.outcome == "consumed"
        assert disposition.denial_code is None
        task = session.scalar(
            select(Task).where(
                Task.classification_message_id
                == disposition.classification_message_id
            )
        )
        assert task is not None
        assert session.scalar(select(func.count(Task.task_id))) == 1
    assert [event.event_type for event in task_timeline.events] == ["task_created"]


def test_approve_action_follow_up_and_outcome_are_atomic_and_exact(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    decision_id, ph, _ec = _pending_decision(ft012_database, farm, boss, plant)
    approval_request = uuid.uuid4()
    approve = _approval_command(boss, plant, decision_id, request_id=approval_request)
    with ft012_database.session() as session:
        service = TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW)
        approved = service.decide_approval(approve)
    with ft012_database.session() as session:
        duplicate = TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).decide_approval(approve)
    assert approved.result == "created" and duplicate.result == "duplicate"
    assert approved.action_task.task_id == duplicate.action_task.task_id
    action_id = approved.action_task.task_id

    completion_at = NOW + timedelta(minutes=10)
    complete = CompleteTaskCommandV1(
        actor_context=boss, plant_id=plant.plant_id,
        task_id=action_id, request_id=uuid.uuid4(),
    )
    with ft012_database.session() as session:
        completed = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: completion_at
        ).complete_task(complete)
    assert completed.follow_up_task.due_at == completion_at + timedelta(hours=48)

    outcome_command = RecordOutcomeCommandV1(
        actor_context=boss, plant_id=plant.plant_id,
        follow_up_task_id=completed.follow_up_task.task_id,
        request_id=uuid.uuid4(), value=OutcomeValue.IMPROVED,
        evidence_refs=(f"manual_measurement:{ph.measurement_id}",),
    )
    with ft012_database.session() as session:
        outcome = TaskFollowUpService(
            session, timeline_appender=task_timeline,
                clock=lambda: completion_at + timedelta(hours=1),
        ).record_outcome(outcome_command)
    assert outcome.task.status == "completed" and outcome.outcome.value == "improved"
    assert [event.event_type for event in task_timeline.events] == [
        "approval_decided", "task_created", "task_completed", "task_created",
        "task_completed", "follow_up_outcome_recorded",
        "dataset_candidate_created",
    ]
    with ft012_database.session() as session:
        assert session.scalar(select(func.count(Task.task_id))) == 2
        assert session.scalar(select(func.count(Outcome.outcome_id))) == 1


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_approval_timeline_payload_is_branch_exact(
    ft012_database, ft012_seed, task_timeline, decision,
):
    farm, boss, _membership, plant = ft012_seed
    decision_id, _ph, _ec = _pending_decision(
        ft012_database,
        farm,
        boss,
        plant,
        expires_at=NOW + timedelta(hours=1),
    )
    with ft012_database.session() as session:
        result = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).decide_approval(
            _approval_command(boss, plant, decision_id, decision=decision)
        )
    payload = task_timeline.events[0].payload_summary
    assert payload == {
        "decision": decision,
        "action_kind": "ph_adjustment",
        "record_version": 2,
        **(
            {"action_task_id": str(result.action_task.task_id)}
            if decision == "approved"
            else {}
        ),
    }


def test_reject_expiry_engineer_consultant_and_audit_rollback(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    consultant, consultant_membership = create_actor(ft012_database, farm, "consultant")
    grant_access(ft012_database, boss, membership_id=consultant_membership.membership_id, plant_id=plant.plant_id)
    decision_id, _ph, _ec = _pending_decision(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).decide_approval(
                _approval_command(consultant, plant, decision_id)
            )
    assert denied.value.code is TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN

    def fail_audit(_event):
        raise RuntimeError("secret=must-not-leak")

    with ft012_database.session() as session:
        TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).materialize_pending_approval(decision_id)
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as failed:
            TaskFollowUpService(session, timeline_appender=fail_audit, clock=lambda: NOW).decide_approval(
                _approval_command(boss, plant, decision_id)
            )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_AUDIT_FAILED
    assert "secret" not in str(failed.value)
    with ft012_database.session() as session:
        approval = session.scalar(select(Approval).where(Approval.safety_decision_id == decision_id))
        assert approval.status == "pending"
        assert session.scalar(select(func.count(Task.task_id))) == 0

    expired_id, _ph, _ec = _pending_decision(
        ft012_database, farm, boss, plant, expires_at=NOW
    )
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as expired:
            TaskFollowUpService(
                session, timeline_appender=task_timeline,
                clock=lambda: NOW + timedelta(microseconds=1),
            ).decide_approval(_approval_command(boss, plant, expired_id, decision="rejected"))
    assert expired.value.code is TaskFollowUpErrorCode.APPROVAL_NOT_CURRENT


def test_archive_freezes_open_action_and_restore_has_no_replay(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    decision_id, _ph, _ec = _pending_decision(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        approved = TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).decide_approval(
            _approval_command(boss, plant, decision_id)
        )
    archive_plant(ft012_database, boss, plant_id=plant.plant_id)
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as blocked:
            TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).complete_task(
                CompleteTaskCommandV1(
                    actor_context=boss, plant_id=plant.plant_id,
                    task_id=approved.action_task.task_id, request_id=uuid.uuid4(),
                )
            )
    assert blocked.value.code is TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE
    with ft012_database.session() as session:
        task = session.get(Task, approved.action_task.task_id)
        assert task.status == "open"
        assert session.scalar(select(func.count(Task.task_id))) == 1


def test_engineer_approval_requires_current_grant_flag(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    engineer, engineer_membership = create_actor(ft012_database, farm, "engineer")
    grant_access(
        ft012_database, boss, plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    decision_id, _ph, _ec = _pending_decision(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as denied:
            TaskFollowUpService(session, timeline_appender=task_timeline, clock=lambda: NOW).decide_approval(
                _approval_command(engineer, plant, decision_id)
            )
    assert denied.value.code is TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN
    with ft012_database.session() as session:
        FarmService(session).grant_access(
            boss, plant_id=plant.plant_id,
            membership_id=engineer_membership.membership_id,
            plant_approve_actions=True,
        )
    with ft012_database.session() as session:
        approved = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).decide_approval(_approval_command(engineer, plant, decision_id))
    assert approved.action_task.created_by_role_preset == "engineer"
    assert approved.approval.decision_grant_id is not None


def test_concurrent_identical_action_completion_creates_one_follow_up(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    decision_id, _ph, _ec = _pending_decision(ft012_database, farm, boss, plant)
    with ft012_database.session() as session:
        action = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).decide_approval(_approval_command(boss, plant, decision_id)).action_task
    command = CompleteTaskCommandV1(
        actor_context=boss, plant_id=plant.plant_id,
        task_id=action.task_id, request_id=uuid.uuid4(),
    )

    def complete():
        with ft012_database.session() as session:
            return TaskFollowUpService(
                session, timeline_appender=task_timeline,
                clock=lambda: NOW + timedelta(minutes=1),
            ).complete_task(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _item: complete(), range(2)))
    assert {first.result, second.result} == {"created", "duplicate"}
    assert first.follow_up_task.task_id == second.follow_up_task.task_id
    with ft012_database.session() as session:
        assert session.scalar(
            select(func.count(Task.task_id)).where(Task.parent_action_task_id == action.task_id)
        ) == 1


class _RequestCollisionRepository(TaskFollowUpRepository):
    def __init__(self, session, barrier: Barrier) -> None:
        super().__init__(session)
        self._barrier = barrier

    def task_for_completion_request(self, request_id):
        owner = super().task_for_completion_request(request_id)
        self._barrier.wait(timeout=15)
        return owner


def test_concurrent_cross_parent_request_collision_is_version_conflict(
    ft012_database, ft012_seed, task_timeline,
):
    farm, boss_one, _membership, plant_one = ft012_seed
    boss_two, _membership_two = create_actor(ft012_database, farm, "boss")
    plant_two = create_active_plant(
        ft012_database,
        boss_two,
        plant_key=f"ft012_collision_{uuid.uuid4().hex[:8]}",
    )
    commands = (
        _ordinary_command(ft012_database, farm, boss_one, plant_one),
        _ordinary_command(ft012_database, farm, boss_two, plant_two),
    )
    tasks = []
    for command in commands:
        with ft012_database.session() as session:
            tasks.append(TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).create_ordinary_task(command).task)

    request_id = uuid.uuid4()
    barrier = Barrier(2)

    def complete(actor, plant, task):
        try:
            with ft012_database.session() as session:
                result = TaskFollowUpService(
                    session,
                    repository=_RequestCollisionRepository(session, barrier),
                    timeline_appender=task_timeline,
                    clock=lambda: NOW + timedelta(minutes=5),
                ).complete_task(CompleteTaskCommandV1(
                    actor_context=actor,
                    plant_id=plant.plant_id,
                    task_id=task.task_id,
                    request_id=request_id,
                ))
            return result.result
        except TaskFollowUpError as error:
            return error.code.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(complete, boss_one, plant_one, tasks[0]),
            pool.submit(complete, boss_two, plant_two, tasks[1]),
        )
        results = [future.result(timeout=30) for future in futures]
    assert set(results) == {"created", "TASK_VERSION_CONFLICT"}
    with ft012_database.session() as session:
        rows = list(session.scalars(select(Task).where(
            Task.task_id.in_([task.task_id for task in tasks])
        )))
        assert sorted(row.status for row in rows) == ["completed", "open"]
        assert session.scalar(select(func.count(Task.task_id)).where(
            Task.completion_request_id == request_id
        )) == 1


@pytest.mark.parametrize(
    "constraint_name",
    ["uq_tasks_completion_request", "uq_tasks_parent_action"],
)
def test_ownerless_or_unrelated_integrity_error_stays_persistence_failure(
    ft012_database, ft012_seed, task_timeline, constraint_name,
):
    farm, boss, _membership, plant = ft012_seed
    with ft012_database.session() as session:
        task = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).create_ordinary_task(
            _ordinary_command(ft012_database, farm, boss, plant)
        ).task

    class Diagnostic:
        def __init__(self, name):
            self.constraint_name = name

    class DriverError(Exception):
        def __init__(self, name):
            super().__init__("synthetic integrity failure")
            self.diag = Diagnostic(name)

    request_id = uuid.uuid4()
    with ft012_database.session() as session:
        def fail_flush(*_args, **_kwargs):
            raise IntegrityError(
                "synthetic integrity failure",
                {},
                DriverError(constraint_name),
            )

        session.flush = fail_flush
        with pytest.raises(TaskFollowUpError) as failed:
            TaskFollowUpService(
                session, timeline_appender=task_timeline, clock=lambda: NOW
            ).complete_task(CompleteTaskCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                task_id=task.task_id,
                request_id=request_id,
            ))
    assert failed.value.code is TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
    with ft012_database.session() as session:
        stored = session.get(Task, task.task_id)
        assert stored.status == "open"
        assert session.scalar(select(func.count(Task.task_id)).where(
            Task.completion_request_id == request_id
        )) == 0


def test_consumed_retry_missing_task_link_uses_existing_redacted_mapping(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    command = _ordinary_command(ft012_database, farm, boss, plant)

    with ft012_database.session() as session:
        created = TaskFollowUpService(
            session,
            timeline_appender=task_timeline,
            clock=lambda: NOW,
        ).create_ordinary_task(command)
    with ft012_database.session() as session, session.begin():
        stored = session.get(Task, created.task.task_id)
        assert stored is not None
        session.delete(stored)

    with ft012_database.session() as session:
        with pytest.raises(TaskFollowUpError) as failed:
            TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            ).create_ordinary_task(command)

    assert failed.value.code is TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
    assert str(failed.value) == "TASK_PERSISTENCE_FAILED"
    assert failed.value.__cause__ is None
    with ft012_database.session() as session:
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            command.message_envelope.message_id,
        )
        assert disposition is not None
        assert disposition.outcome == "consumed"
        assert session.scalar(select(func.count(Task.task_id))) == 0


@pytest.mark.parametrize("ref_kind", ["task", "outcome"])
def test_w1_outcome_evidence_still_rejects_task_and_outcome_refs(
    ft012_database,
    ft012_seed,
    task_timeline,
    ref_kind,
):
    farm, boss, _membership, plant = ft012_seed

    def create_follow_up():
        decision_id, _ph, _ec = _pending_decision(
            ft012_database,
            farm,
            boss,
            plant,
            expires_at=NOW + timedelta(hours=1),
        )
        with ft012_database.session() as session:
            service = TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            )
            service.materialize_pending_approval(decision_id)
            action = service.decide_approval(
                _approval_command(boss, plant, decision_id)
            ).action_task
        assert action is not None
        with ft012_database.session() as session:
            follow_up = TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            ).complete_task(
                CompleteTaskCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    task_id=action.task_id,
                    request_id=uuid.uuid4(),
                )
            ).follow_up_task
        assert follow_up is not None
        return action, follow_up

    action, target = create_follow_up()
    if ref_kind == "task":
        bad_ref = f"task:{action.task_id}"
    else:
        _source_action, source_follow_up = create_follow_up()
        with ft012_database.session() as session:
            source = TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            ).record_outcome(
                RecordOutcomeCommandV1(
                    actor_context=boss,
                    plant_id=plant.plant_id,
                    follow_up_task_id=source_follow_up.task_id,
                    request_id=uuid.uuid4(),
                    value=OutcomeValue.NO_DATA,
                    evidence_refs=(),
                )
            ).outcome
        bad_ref = f"outcome:{source.outcome_id}"

    with ft012_database.session() as session, pytest.raises(TaskFollowUpError) as failed:
        TaskFollowUpService(
            session,
            timeline_appender=task_timeline,
            clock=lambda: NOW,
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=target.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(bad_ref,),
            )
        )
    assert failed.value.code is TaskFollowUpErrorCode.TASK_EVIDENCE_REQUIRED
    with ft012_database.session() as session:
        stored = session.get(Task, target.task_id)
        assert stored is not None and stored.status == "open"
        assert session.scalar(
            select(func.count(Outcome.outcome_id)).where(
                Outcome.follow_up_task_id == target.task_id
            )
        ) == 0
