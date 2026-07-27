from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select

from backend.app import AppSettings
from backend.app.agent_runtime import ModelExecution, SafetyClassificationResultV1
from backend.app.safety_gate import (
    SafetyClassification,
    SafetyGateClassificationService,
)
from backend.app.task_follow_up import (
    Approval,
    CompleteTaskCommandV1,
    DatabaseTaskFollowUpInputAssembler,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    OutcomeValue,
    RecordOutcomeCommandV1,
    Task,
    TaskFollowUpCommandV1,
    TaskFollowUpModelResultV1,
    TaskFollowUpRuntimeService,
    TaskFollowUpRuntimeValidationError,
    TaskFollowUpRunResultV1,
    TaskFollowUpService,
)
from backend.app.task_follow_up.contracts import (
    ClassifiedMessageTaskCommandV1,
    TaskKind,
    canonical_fingerprint,
)
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    grant_access,
)
from tests.backend.safety_gate.helpers import envelope_for
from tests.backend.task_follow_up.test_domain_loop import (
    _approval_command,
    _measurement,
    _pending_decision,
)


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


class _Executor:
    def __init__(
        self,
        result_factory,
        *,
        model_ref,
        before_return=None,
        session=None,
    ):
        self.model_ref = model_ref
        self.result_factory = result_factory
        self.before_return = before_return
        self.session = session
        self.requests = []

    def execute(self, request):
        if self.session is not None:
            assert not self.session.in_transaction()
        self.requests.append(request)
        if self.before_return is not None:
            self.before_return()
        return ModelExecution(
            model_ref=self.model_ref,
            result=self.result_factory(request),
        )


class _FailingExecutor:
    model_ref = "test_provider:task_follow_up_v1"

    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        raise TimeoutError("synthetic timeout; credential=must-not-leak")


class _ArchiveAfterClassification:
    def __init__(self, service, callback):
        self.service = service
        self.callback = callback
        self.calls = []

    def classify(self, command):
        self.calls.append(command)
        outcome = self.service.classify(command)
        self.callback()
        return outcome


def _proposal(request, *, kind="check", text="Проверить состояние листьев."):
    return {
        "schema_version": 1,
        "runtime_decision": "speak",
        "proposed_task_kind": kind,
        "candidate_output": text,
        "confidence": 0.81,
        "source_refs": [request.source_refs[0]],
        "reason_code": None,
    }


def _silence(_request):
    return {
        "schema_version": 1,
        "runtime_decision": "silent",
        "proposed_task_kind": None,
        "candidate_output": None,
        "confidence": None,
        "source_refs": [],
        "reason_code": "no_new_task",
    }


def _safety_candidate(_request, *, kind="check"):
    return {
        "schema_version": 1,
        "candidate_classification": "safe_task_request",
        "safe_task_kind": kind,
        "physical_action_kind": None,
    }


def _command(actor, plant, task_id, *, run_id=None, trigger_kind="task_completed"):
    return TaskFollowUpCommandV1(
        run_id=run_id or uuid.uuid4(),
        requested_at=NOW,
        actor_context=actor,
        plant_id=plant.plant_id,
        trigger_kind=trigger_kind,
        trigger_task_id=task_id,
    )


def _seed_completed_task(database, farm, actor, plant, timeline):
    envelope = envelope_for(
        actor,
        plant,
        candidate_output="Проверить исходное состояние растения.",
        candidate_claim_type="task_request",
    )
    classification = SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(envelope.message_id),
            "classifier_version": "safety_gate_v1",
            "classification": "safe_task_request",
            "safe_task_kind": "check",
            "reason_code": "safe_check_request",
        }
    )
    with database.session() as session, session.begin():
        session.add(
            SafetyClassification(
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
                result_sha256="a" * 64,
            )
        )
    with database.session() as session:
        task = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
        ).create_ordinary_task(
            ClassifiedMessageTaskCommandV1(
                actor_context=actor,
                message_envelope=envelope,
                classification=classification,
                task_kind=TaskKind.CHECK,
            )
        ).task
    with database.session() as session:
        completed = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
        ).complete_task(
            CompleteTaskCommandV1(
                actor_context=actor,
                plant_id=plant.plant_id,
                task_id=task.task_id,
                request_id=uuid.uuid4(),
            )
        ).task
    return completed.task_id


def _seed_open_action(database, farm, actor, plant, timeline):
    decision_id, _ph, _ec = _pending_decision(
        database,
        farm,
        actor,
        plant,
        expires_at=NOW + timedelta(hours=1),
    )
    with database.session() as session:
        service = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
        )
        service.materialize_pending_approval(decision_id)
        action = service.decide_approval(
            _approval_command(actor, plant, decision_id)
        ).action_task
    assert action is not None and action.status == "open"
    return action


def _runtime(
    session,
    *,
    model=None,
    classifier=None,
    timeline,
    classification_service=None,
):
    return TaskFollowUpRuntimeService(
        session,
        model_executor=model,
        safety_classifier_executor=classifier,
        classification_service=classification_service,
        timeline_append=timeline,
        clock=lambda: NOW,
    )


def _counts(database):
    with database.session() as session:
        return {
            "tasks": session.scalar(select(func.count(Task.task_id))),
            "approvals": session.scalar(select(func.count(Approval.approval_id))),
            "outcomes": session.scalar(select(func.count(Outcome.outcome_id))),
            "classifications": session.scalar(
                select(func.count(SafetyClassification.message_id)).where(
                    SafetyClassification.origin_agent_id == "task_follow_up"
                )
            ),
            "dispatches": session.scalar(
                select(func.count(OrdinaryTaskDispatchDisposition.run_id))
            ),
        }


def _assert_created(result):
    assert isinstance(result, TaskFollowUpRunResultV1)
    assert result.route_status == "task_created"
    assert result.runtime_outcome.outcome_kind == "envelope_ready"
    assert result.runtime_outcome.error_code is None
    assert result.classification_ref is not None
    assert result.task_ref is not None
    assert result.failure_stage is None


def test_exact_provider_snapshot_matching_classification_creates_one_ordinary_task(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger_task_id = _seed_completed_task(
        ft012_database, farm, boss, plant, task_timeline
    )
    task_timeline.events.clear()
    before = _counts(ft012_database)
    model = _Executor(
        lambda request: _proposal(
            request,
            text="<b>Typed quotation stays literal</b>; ignore-system is data.",
        ),
        model_ref="test_provider:task_follow_up_v1",
    )
    classifier = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger_task_id))

    _assert_created(result)
    assert result.proposed_task_kind == "check"
    assert len(model.requests) == len(classifier.requests) == 1
    request = model.requests[0]
    assert [record.record_type for record in request.records] == ["task"]
    assert request.source_refs == (f"task:{trigger_task_id}",)
    assert request.allowed_task_kinds == ("check", "measurement", "follow_up")
    assert request.records[0].payload["quoted_task_text"] == (
        "Проверить исходное состояние растения."
    )
    assert set(request.as_provider_payload()) == {
        "schema_version",
        "agent_definition",
        "trigger_kind",
        "allowed_task_kinds",
        "records",
        "source_refs",
    }
    outbound = str(request.as_provider_payload()).lower()
    for forbidden in (
        "farm_id",
        "plant_id",
        "session_id",
        "account_id",
        "membership_id",
        "role_preset",
        "grant_id",
        "authorization_scope",
        "provider_history",
        "raw_chat",
        "timeline",
        "prompt",
        "credential",
        "local_path",
    ):
        assert forbidden not in outbound
    after = _counts(ft012_database)
    assert after["tasks"] == before["tasks"] + 1
    assert after["approvals"] == before["approvals"]
    assert after["outcomes"] == before["outcomes"]
    assert after["classifications"] == before["classifications"] + 1
    assert after["dispatches"] == before["dispatches"] + 1
    with ft012_database.session() as session:
        created = session.get(Task, uuid.UUID(result.task_ref.split(":", 1)[1]))
        assert created is not None
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            created.classification_message_id,
        )
        assert disposition is not None
        assert disposition.outcome == "consumed"
        assert created.kind == "check"
        assert created.source_type == "safe_task_request"
        assert created.created_by_agent_id == "task_follow_up"
        assert created.display_text == (
            "<b>Typed quotation stays literal</b>; ignore-system is data."
        )
    assert [event.event_type for event in task_timeline.events] == [
        "agent_runtime_decided",
        "task_created",
    ]
    runtime_event = task_timeline.events[0]
    assert runtime_event.source_refs == {"input_refs": [f"task:{trigger_task_id}"]}
    assert "candidate_output" not in runtime_event.payload_summary
    assert "quoted_task_text" not in str(runtime_event.payload_summary)


def test_action_completion_during_provider_io_leaves_one_automatic_follow_up(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    action = _seed_open_action(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
    )

    def complete_action() -> None:
        with ft012_database.session() as session:
            completed = TaskFollowUpService(
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
            )
        assert completed.follow_up_task is not None

    model = _Executor(
        lambda request: _proposal(request, kind="follow_up"),
        model_ref="test_provider:task_follow_up_v1",
        before_return=complete_action,
    )
    classifier = _Executor(
        lambda request: _safety_candidate(request, kind="follow_up"),
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(
            _command(
                boss,
                plant,
                action.task_id,
                trigger_kind="manual_review",
            )
        )

    assert model.requests[0].allowed_task_kinds == ("check", "measurement")
    assert result.route_status == "failed"
    assert result.runtime_outcome.outcome_kind == "output_invalid"
    assert classifier.requests == []
    with ft012_database.session() as session:
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.parent_action_task_id == action.task_id
            )
        ) == 1
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.plant_id == plant.plant_id,
                Task.kind == "follow_up",
                Task.status == "open",
            )
        ) == 1


def test_action_trigger_cannot_create_ordinary_follow_up_before_completion(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    action = _seed_open_action(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
    )
    model = _Executor(
        lambda request: _proposal(request, kind="follow_up"),
        model_ref="test_provider:task_follow_up_v1",
    )
    classifier = _Executor(
        lambda request: _safety_candidate(request, kind="follow_up"),
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(
            _command(
                boss,
                plant,
                action.task_id,
                trigger_kind="manual_review",
            )
        )

    assert model.requests[0].allowed_task_kinds == ("check", "measurement")
    assert result.route_status == "failed"
    assert result.runtime_outcome.outcome_kind == "output_invalid"
    assert classifier.requests == []

    with ft012_database.session() as session:
        completed = TaskFollowUpService(
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
        )
    assert completed.follow_up_task is not None
    with ft012_database.session() as session:
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.parent_action_task_id == action.task_id
            )
        ) == 1
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.plant_id == plant.plant_id,
                Task.kind == "follow_up",
                Task.status == "open",
            )
        ) == 1


def test_classified_retry_is_idempotent_only_through_ordinary_task_authority(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        first = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    envelope = first.runtime_outcome.message_envelope
    assert envelope is not None
    classification = SafetyClassificationResultV1.from_untrusted(
        {
            "schema_version": 1,
            "message_id": str(envelope.message_id),
            "classifier_version": "safety_gate_v1",
            "classification": "safe_task_request",
            "safe_task_kind": "check",
            "reason_code": "safe_check_request",
        }
    )
    with ft012_database.session() as session:
        duplicate = TaskFollowUpService(
            session,
            timeline_appender=task_timeline,
            clock=lambda: NOW,
        ).create_ordinary_task(
            ClassifiedMessageTaskCommandV1(
                actor_context=boss,
                message_envelope=envelope,
                classification=classification,
                task_kind=TaskKind.CHECK,
            )
        )
    _assert_created(first)
    assert duplicate.result == "duplicate"
    assert f"task:{duplicate.task.task_id}" == first.task_ref


def test_repeated_runtime_invocation_repeats_io_but_never_creates_second_task(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        runtime = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        )
        first = runtime.run(command)
        second = runtime.run(command)

    _assert_created(first)
    assert isinstance(second, TaskFollowUpRunResultV1)
    assert second.route_status == "failed"
    assert second.failure_stage == "task"
    assert len(model.requests) == 2
    assert len(classifier.requests) == 2
    with ft012_database.session() as session:
        assert session.scalar(
            select(func.count(Task.task_id)).where(
                Task.created_by_agent_id == "task_follow_up",
                Task.create_request_id == command.run_id,
            )
        ) == 1
        assert session.scalar(
            select(func.count(OrdinaryTaskDispatchDisposition.run_id)).where(
                OrdinaryTaskDispatchDisposition.run_id == command.run_id
            )
        ) == 1


@pytest.mark.parametrize(
    ("model_factory", "expected_outcome"),
    [
        (_silence, "model_silent"),
        (
            lambda request: {**_proposal(request), "action": "pump"},
            "output_invalid",
        ),
    ],
)
def test_silence_and_invalid_output_have_no_classification_or_task_effect(
    ft012_database,
    ft012_seed,
    task_timeline,
    model_factory,
    expected_outcome,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(model_factory, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert result.runtime_outcome.outcome_kind == expected_outcome
    assert result.route_status == (
        "silent" if expected_outcome == "model_silent" else "failed"
    )
    assert classifier.requests == []
    assert _counts(ft012_database) == before


def test_unbound_and_timeout_fail_closed_without_fallback(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    with ft012_database.session() as session:
        unbound = _runtime(session, timeline=task_timeline).run(
            _command(boss, plant, trigger)
        )
    failing = _FailingExecutor()
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        timeout = _runtime(
            session,
            model=failing,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert unbound.runtime_outcome.outcome_kind == "runtime_not_configured"
    assert unbound.runtime_outcome.provider_call_status == "not_attempted"
    assert timeout.runtime_outcome.outcome_kind == "provider_failed"
    assert timeout.runtime_outcome.error_code == "AGENT_PROVIDER_FAILED"
    assert "credential" not in str(timeout.as_value()).lower()
    assert classifier.requests == []
    assert _counts(ft012_database) == before


def test_classification_kind_mismatch_is_not_taskable_and_never_action(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(
        lambda request: _safety_candidate(request, kind="measurement"),
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert result.route_status == "not_taskable"
    assert result.proposed_task_kind == "check"
    assert result.classification_ref is not None
    assert result.task_ref is None
    after = _counts(ft012_database)
    assert after["tasks"] == before["tasks"]
    assert after["approvals"] == before["approvals"]
    assert after["outcomes"] == before["outcomes"]
    assert after["dispatches"] == before["dispatches"]
    assert after["classifications"] == before["classifications"] + 1


def test_post_model_archive_denial_can_be_explicitly_reinvoked_after_restore(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    command = _command(boss, plant, trigger)
    first_model = _Executor(
        _proposal,
        model_ref="test_provider:task_follow_up_v1",
        before_return=lambda: archive_plant(
            ft012_database, boss, plant_id=plant.plant_id
        ),
    )
    first_classifier = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        denied = _runtime(
            session,
            model=first_model,
            classifier=first_classifier,
            timeline=task_timeline,
        ).run(command)
    assert denied.runtime_outcome.outcome_kind == "publication_guard_denied"
    assert denied.failure_stage == "runtime"
    assert len(first_model.requests) == 1
    assert first_classifier.requests == []

    with ft012_database.session() as session:
        from backend.app.access_admin.farm_service import FarmService

        FarmService(session).restore_plant(boss, plant_id=plant.plant_id)

    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_classifier = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        retry = _runtime(
            session,
            model=retry_model,
            classifier=retry_classifier,
            timeline=task_timeline,
        ).run(command)
    _assert_created(retry)
    assert len(retry_model.requests) == len(retry_classifier.requests) == 1


def test_consultant_is_denied_before_model_io(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    consultant, consultant_membership = create_actor(
        ft012_database,
        farm,
        "consultant",
    )
    grant_access(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(consultant, plant, trigger))
    assert result.runtime_outcome.outcome_kind == "context_denied"
    assert model.requests == classifier.requests == []
    assert _counts(ft012_database) == before


def test_provider_and_safety_io_run_outside_task_transaction(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    with ft012_database.session() as session:
        model = _Executor(
            _proposal,
            model_ref="test_provider:task_follow_up_v1",
            session=session,
        )
        classifier = _Executor(
            _safety_candidate,
            model_ref="test_provider:safety_gate_v1",
            session=session,
        )
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    _assert_created(result)
    assert len(model.requests) == len(classifier.requests) == 1


def test_classifier_failures_and_task_write_guard_denial_have_no_task_effect(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    failing_classifier = _FailingExecutor()
    failing_classifier.model_ref = "test_provider:safety_gate_v1"
    with ft012_database.session() as session:
        provider_failure = _runtime(
            session,
            model=model,
            classifier=failing_classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert provider_failure.route_status == "failed"
    assert provider_failure.failure_stage == "classification"
    assert provider_failure.classification_ref is None
    assert len(failing_classifier.requests) == 1
    after_provider_failure = _counts(ft012_database)
    for key in ("tasks", "approvals", "outcomes", "dispatches"):
        assert after_provider_failure[key] == before[key]

    guarding_classifier = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
        before_return=lambda: archive_plant(
            ft012_database, boss, plant_id=plant.plant_id
        ),
    )
    with ft012_database.session() as session:
        guard_denial = _runtime(
            session,
            model=_Executor(_proposal, model_ref="test_provider:task_follow_up_v1"),
            classifier=guarding_classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert guard_denial.route_status == "failed"
    assert guard_denial.failure_stage == "classification"
    assert guard_denial.classification_ref is None
    assert len(guarding_classifier.requests) == 1
    after_guard_denial = _counts(ft012_database)
    for key in ("tasks", "approvals", "outcomes", "dispatches"):
        assert after_guard_denial[key] == before[key]


def test_runtime_audit_failure_blocks_envelope_and_classifier(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")

    def fail_audit(_event):
        raise OSError("synthetic audit failure /tmp/private-path")

    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=fail_audit,
        ).run(_command(boss, plant, trigger))
    assert result.route_status == "failed"
    assert result.failure_stage == "runtime"
    assert result.runtime_outcome.outcome_kind == "audit_failed"
    assert result.runtime_outcome.error_code == "AGENT_AUDIT_FAILED"
    assert result.runtime_outcome.event_ref is None
    assert "private-path" not in str(result.as_value())
    assert classifier.requests == []
    assert _counts(ft012_database) == before


def test_archive_after_classification_is_terminal_task_write_denial(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        real_classifier = SafetyGateClassificationService(
            session,
            model_executor=classifier,
            clock=lambda: NOW,
        )
        race = _ArchiveAfterClassification(
            real_classifier,
            lambda: archive_plant(ft012_database, boss, plant_id=plant.plant_id),
        )
        result = _runtime(
            session,
            model=model,
            timeline=task_timeline,
            classification_service=race,
        ).run(_command(boss, plant, trigger))
    assert len(race.calls) == 1
    assert result.route_status == "failed"
    assert result.failure_stage == "task"
    assert result.classification_ref is not None
    assert result.task_ref is None
    after = _counts(ft012_database)
    assert after["tasks"] == before["tasks"]
    assert after["dispatches"] == before["dispatches"] + 1


def test_outcome_context_is_exact_ordered_and_value_free_evidence_descriptor(
    ft012_database,
    ft012_seed,
    task_timeline,
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
        service = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        )
        service.materialize_pending_approval(decision_id)
        action = service.decide_approval(
            _approval_command(boss, plant, decision_id)
        ).action_task
    assert action is not None
    with ft012_database.session() as session:
        follow_up = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).complete_task(
            CompleteTaskCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                task_id=action.task_id,
                request_id=uuid.uuid4(),
            )
        ).follow_up_task
    assert follow_up is not None
    evidence = _measurement(ft012_database, boss, plant, ph="6.25", measured_at=NOW)
    with ft012_database.session() as session:
        completed = TaskFollowUpService(
            session, timeline_appender=task_timeline, clock=lambda: NOW
        ).record_outcome(
            RecordOutcomeCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                follow_up_task_id=follow_up.task_id,
                request_id=uuid.uuid4(),
                value=OutcomeValue.IMPROVED,
                evidence_refs=(f"manual_measurement:{evidence.measurement_id}",),
            )
        )
    with ft012_database.session() as session:
        assembled = DatabaseTaskFollowUpInputAssembler(session).assemble(
            boss,
            plant_id=plant.plant_id,
            trigger_kind="follow_up_outcome_recorded",
            trigger_task_id=completed.task.task_id,
            selected_at=NOW,
        )
    records = assembled.request.records
    assert [record.record_type for record in records] == [
        "task",
        "outcome",
        "task",
        "evidence_ref",
    ]
    assert records[0].source_ref == f"task:{follow_up.task_id}"
    assert records[1].source_ref == f"outcome:{completed.outcome.outcome_id}"
    assert records[2].source_ref == f"task:{action.task_id}"
    assert records[3].source_ref == f"manual_measurement:{evidence.measurement_id}"
    assert set(records[3].payload) == {
        "evidence_kind",
        "record_ref",
        "recorded_at",
    }
    assert "6.25" not in str(records[3].as_provider_value()).lower()
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpModelResultV1.from_untrusted(
            {
                **_proposal(assembled.request),
                "source_refs": list(reversed(assembled.request.source_refs)),
            },
            request=assembled.request,
        )


def test_model_result_contract_rejects_unknown_action_and_out_of_order_refs(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    with ft012_database.session() as session:
        request = DatabaseTaskFollowUpInputAssembler(session).assemble(
            boss,
            plant_id=plant.plant_id,
            trigger_kind="task_completed",
            trigger_task_id=trigger,
            selected_at=NOW,
        ).request
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpModelResultV1.from_untrusted(
            {**_proposal(request), "action": "approve"},
            request=request,
        )
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpModelResultV1.from_untrusted(
            {
                **_proposal(request),
                "source_refs": [
                    request.source_refs[0],
                    f"task:{uuid.uuid4()}",
                ],
            },
            request=request,
        )
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpModelResultV1.from_untrusted(
            {**_proposal(request), "proposed_task_kind": "action"},
            request=request,
        )
