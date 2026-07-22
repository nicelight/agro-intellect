from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, Lock
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import event, func, select
from sqlalchemy.exc import DBAPIError

from backend.app import AppSettings
from backend.app.access_admin.models import LocalSession
from backend.app.access_admin.farm_service import FarmService
from backend.app.agent_runtime import (
    DatabaseRuntimeAuthorizationGuard,
    ModelExecution,
    SafetyClassificationResultV1,
)
from backend.app.safety_gate import (
    SafetyClassification,
    SafetyClassificationOutcomeV1,
    SafetyGateClassificationService,
)
from backend.app.safety_gate.repository import SafetyClassificationRepository
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
    TaskFollowUpDispositionResultV1,
    TaskFollowUpModelResultV1,
    TaskFollowUpRepository,
    TaskFollowUpRuntimeDisposition,
    TaskFollowUpRuntimeService,
    TaskFollowUpRuntimeValidationError,
    TaskFollowUpRunResultV1,
    TaskFollowUpService,
    task_follow_up_command_fingerprint,
    task_follow_up_run_lock_key,
)
from backend.app.task_follow_up.contracts import (
    ClassifiedMessageTaskCommandV1,
    TaskKind,
    canonical_fingerprint,
)
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    grant_access,
    revoke_access,
)
from tests.backend.safety_gate.helpers import envelope_for
from tests.backend.task_follow_up.test_domain_loop import (
    _approval_command,
    _measurement,
    _pending_decision,
)


NOW = datetime(2026, 7, 20, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _apply_runtime_disposition_revision(ft012_database):
    script = ScriptDirectory.from_config(
        build_alembic_config(AppSettings.from_env())
    )
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            script.get_revision("ft012_runtime_dispositions").module.upgrade()
        connection.commit()


class _Executor:
    def __init__(self, result_factory, *, model_ref, before_return=None):
        self.model_ref = model_ref
        self.result_factory = result_factory
        self.before_return = before_return
        self.requests = []

    def execute(self, request):
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


class _ProcessStop(BaseException):
    pass


class _AlwaysDeniedGuard:
    def current_scope(self, _actor, *, plant_id):
        del plant_id
        return None


class _FailingSafetyRepository(SafetyClassificationRepository):
    def persist_first(self, _classification):
        raise RuntimeError("synthetic classification persistence failure")


class _StopBeforeClassifier:
    def classify(self, _command):
        raise _ProcessStop("synthetic stop after committed handoff")


class _StopBeforeTaskService:
    def create_ordinary_task(self, _command):
        raise _ProcessStop("synthetic stop after committed classification")


class _CountingTaskService:
    def __init__(self, service, *, before_call=None):
        self._service = service
        self._before_call = before_call
        self.calls = 0

    def create_ordinary_task(self, command):
        if self._before_call is not None:
            self._before_call()
        self.calls += 1
        return self._service.create_ordinary_task(command)


class _OneTransactionClassifier:
    """Deterministic Safety spy for lock/barrier tests; one insert, no rollback."""

    def __init__(self, session, executor):
        self._session = session
        self._executor = executor

    def classify(self, command):
        assert not self._session.in_transaction()
        envelope = command.message_envelope
        self._executor.execute(object())
        result = SafetyClassificationResultV1.from_untrusted(
            {
                "schema_version": 1,
                "message_id": str(envelope.message_id),
                "classifier_version": "safety_gate_v1",
                "classification": "safe_task_request",
                "safe_task_kind": "check",
                "reason_code": "safe_check_request",
            }
        )
        with self._session.begin():
            self._session.add(
                SafetyClassification(
                    message_id=envelope.message_id,
                    farm_id=envelope.farm_id,
                    plant_id=envelope.plant_id,
                    origin_agent_id=envelope.agent_id,
                    classifier_version="safety_gate_v1",
                    classification="safe_task_request",
                    safe_task_kind="check",
                    reason_code="safe_check_request",
                    physical_action_kind=None,
                    provider_status="completed",
                    model_ref=self._executor.model_ref,
                    input_sha256=canonical_fingerprint(envelope.as_value()),
                    result_sha256="b" * 64,
                )
            )
        return SafetyClassificationOutcomeV1(
            classification_run_id=command.classification_run_id,
            outcome_kind="classification_persisted",
            authoritative=True,
            effect="evidence_written",
            classification_result=result,
            physical_action_kind=None,
            provider_status="completed",
            model_ref=self._executor.model_ref,
            provider_call_status="completed",
            error_code=None,
        )


class _PostModelGateRepository(TaskFollowUpRepository):
    """Pause the second run-lock request, which is post-model terminal selection."""

    def __init__(self, session, *, ready: Event, release: Event, trace=None):
        super().__init__(session)
        self._ready = ready
        self._release = release
        self._run_lock_calls = 0
        self._trace = trace

    def acquire_task_follow_up_run_lock(self, run_id, *, lock_key=None):
        self._run_lock_calls += 1
        if self._run_lock_calls == 2:
            self._ready.set()
            assert self._release.wait(timeout=20)
        if self._trace is not None:
            self._trace.append("advisory")
        return super().acquire_task_follow_up_run_lock(run_id, lock_key=lock_key)


class _DenyOnlyUnclaimedRunGuard:
    """Deny terminal selection, but allow read resolution of an already-owned run."""

    def __init__(self, session, *, clock):
        self._session = session
        self._delegate = DatabaseRuntimeAuthorizationGuard(session, clock=clock)

    def current_scope(self, actor, *, plant_id):
        has_runtime_owner = self._session.scalar(
            select(func.count(TaskFollowUpRuntimeDisposition.run_id))
        )
        if not has_runtime_owner:
            return None
        return self._delegate.current_scope(actor, plant_id=plant_id)


class _TraceRepository(TaskFollowUpRepository):
    def __init__(self, session, trace, *, writer=False):
        super().__init__(session)
        self._trace = trace
        self._writer = writer

    def acquire_task_follow_up_run_lock(self, run_id, *, lock_key=None):
        self._trace.append("writer.advisory" if self._writer else "runtime.advisory")
        return super().acquire_task_follow_up_run_lock(run_id, lock_key=lock_key)

    def runtime_disposition_for_run(self, run_id, *, for_update=False):
        self._trace.append("writer.runtime" if self._writer else "runtime.runtime")
        return super().runtime_disposition_for_run(run_id, for_update=for_update)

    def dispatch_disposition_for_run(self, run_id, *, for_update=False):
        self._trace.append("writer.classified" if self._writer else "runtime.classified")
        return super().dispatch_disposition_for_run(run_id, for_update=for_update)

    def safety_classification(self, message_id, *, for_update=False):
        if self._writer:
            self._trace.append("writer.classification")
        return super().safety_classification(message_id, for_update=for_update)

    def lock_current_scope(self, actor, *, plant_id, now):
        self._trace.append("writer.current" if self._writer else "runtime.current")
        return super().lock_current_scope(actor, plant_id=plant_id, now=now)

    def lock_task_follow_up_source_ref(self, ref, *, farm_id, plant_id):
        if self._writer:
            self._trace.append("writer.source")
        return super().lock_task_follow_up_source_ref(
            ref,
            farm_id=farm_id,
            plant_id=plant_id,
        )


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


def _command(actor, plant, task_id, *, trigger_kind="task_completed"):
    return TaskFollowUpCommandV1(
        run_id=uuid.uuid4(),
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
        }


def _authority_counts(database, *, run_id=None):
    with database.session() as session:
        runtime_query = select(func.count(TaskFollowUpRuntimeDisposition.run_id))
        dispatch_query = select(func.count(OrdinaryTaskDispatchDisposition.run_id))
        task_query = select(func.count(Task.task_id)).where(
            Task.created_by_agent_id == "task_follow_up"
        )
        classification_query = select(func.count(SafetyClassification.message_id)).where(
            SafetyClassification.origin_agent_id == "task_follow_up"
        )
        if run_id is not None:
            runtime_query = runtime_query.where(
                TaskFollowUpRuntimeDisposition.run_id == run_id
            )
            dispatch_query = dispatch_query.where(
                OrdinaryTaskDispatchDisposition.run_id == run_id
            )
            task_query = task_query.where(Task.create_request_id == run_id)
            classification_query = classification_query.where(
                SafetyClassification.message_id.in_(
                    select(TaskFollowUpRuntimeDisposition.message_id).where(
                        TaskFollowUpRuntimeDisposition.run_id == run_id
                    )
                )
            )
        runtime_rows = session.scalar(runtime_query)
        handed_off = session.scalar(
            select(func.count(TaskFollowUpRuntimeDisposition.run_id)).where(
                TaskFollowUpRuntimeDisposition.outcome == "envelope_handed_off",
                *(
                    (TaskFollowUpRuntimeDisposition.run_id == run_id,)
                    if run_id is not None
                    else ()
                ),
            )
        )
        denied = session.scalar(
            select(func.count(TaskFollowUpRuntimeDisposition.run_id)).where(
                TaskFollowUpRuntimeDisposition.outcome == "publication_denied",
                *(
                    (TaskFollowUpRuntimeDisposition.run_id == run_id,)
                    if run_id is not None
                    else ()
                ),
            )
        )
        return {
            "runtime": runtime_rows,
            "handed_off": handed_off,
            "publication_denied": denied,
            "messages": handed_off,
            "classifications": session.scalar(classification_query),
            "dispatches": session.scalar(dispatch_query),
            "tasks": session.scalar(task_query),
        }


def _assert_local(result, status, code, *, classification_ref=None, task_ref=None):
    assert isinstance(result, TaskFollowUpDispositionResultV1)
    assert result.result_status == status
    assert result.result_code == code
    assert result.classification_ref == classification_ref
    assert result.task_ref == task_ref
    assert result.retry_requires_new_run is True


def _assert_created(result):
    assert isinstance(result, TaskFollowUpRunResultV1)
    assert result.route_status == "task_created"
    assert result.runtime_outcome.outcome_kind == "envelope_ready"
    assert result.runtime_outcome.error_code is None
    assert result.classification_ref is not None
    assert result.task_ref is not None
    assert result.failure_stage is None


def _assert_denied(result):
    assert isinstance(result, TaskFollowUpRunResultV1)
    assert result.route_status == "failed"
    assert result.runtime_outcome.outcome_kind == "publication_guard_denied"
    assert result.runtime_outcome.error_code == "AGENT_PUBLICATION_BLOCKED"
    assert result.classification_ref is None
    assert result.task_ref is None
    assert result.failure_stage == "runtime"


def _fresh_success(database, actor, plant, trigger, timeline, *, command=None):
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    task_counter = None
    with database.session() as session:
        task_counter = _CountingTaskService(
            TaskFollowUpService(
                session,
                timeline_appender=timeline,
                clock=lambda: NOW,
            )
        )
        result = TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            classification_service=_OneTransactionClassifier(session, safety),
            ordinary_task_service=task_counter,
            timeline_append=timeline,
            clock=lambda: NOW,
        ).run(command or _command(actor, plant, trigger))
    _assert_created(result)
    assert (len(model.requests), len(safety.requests), task_counter.calls) == (1, 1, 1)
    return result


def _restore(database, actor, plant):
    with database.session() as session:
        FarmService(session).restore_plant(actor, plant_id=plant.plant_id)


def _runtime_audit_count(timeline):
    return sum(event.event_type == "agent_runtime_decided" for event in timeline.events)


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
    command = _command(boss, plant, trigger_task_id)
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(command)

    assert result.route_status == "task_created"
    assert result.proposed_task_kind == "check"
    assert result.classification_ref is not None
    assert result.task_ref is not None
    assert result.failure_stage is None
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
    outbound = str(request.as_provider_payload())
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
        assert forbidden not in outbound.lower()
    assert _counts(ft012_database) == {
        "tasks": before["tasks"] + 1,
        "approvals": before["approvals"],
        "outcomes": before["outcomes"],
    }
    with ft012_database.session() as session:
        created = session.get(Task, uuid.UUID(result.task_ref.split(":", 1)[1]))
        assert created is not None
        disposition = session.get(
            OrdinaryTaskDispatchDisposition,
            created.classification_message_id,
        )
        assert disposition is not None
        assert disposition.outcome == "consumed"
        assert (
            disposition.expected_task_create_fingerprint
            == created.create_request_fingerprint
        )
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


def test_success_envelope_is_idempotent_only_through_existing_ordinary_task_service(
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
    assert first.route_status == "task_created"
    assert duplicate.result == "duplicate"
    assert f"task:{duplicate.task.task_id}" == first.task_ref


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
    assert result.route_status == ("silent" if expected_outcome == "model_silent" else "failed")
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
    assert _counts(ft012_database) == before


def test_archive_after_model_io_blocks_before_classification(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    before = _counts(ft012_database)
    model = _Executor(
        _proposal,
        model_ref="test_provider:task_follow_up_v1",
        before_return=lambda: archive_plant(
            ft012_database, boss, plant_id=plant.plant_id
        ),
    )
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(_command(boss, plant, trigger))
    assert result.runtime_outcome.outcome_kind == "publication_guard_denied"
    assert result.failure_stage == "runtime"
    assert classifier.requests == []
    assert _counts(ft012_database) == before


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


@pytest.mark.parametrize("revocation_kind", ("session", "grant"))
def test_post_model_session_or_grant_revoke_commits_terminal_denial(
    ft012_database,
    ft012_seed,
    task_timeline,
    revocation_kind,
):
    farm, boss, _membership, plant = ft012_seed
    engineer, engineer_membership = create_actor(ft012_database, farm, "engineer")
    grant_access(
        ft012_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    before = _counts(ft012_database)
    command = _command(engineer, plant, trigger)

    def revoke_current_authority():
        if revocation_kind == "grant":
            revoke_access(
                ft012_database,
                boss,
                plant_id=plant.plant_id,
                membership_id=engineer_membership.membership_id,
            )
            return
        with ft012_database.session() as session, session.begin():
            local_session = session.get(LocalSession, engineer.session_id)
            assert local_session is not None
            local_session.revoked_at = NOW

    model = _Executor(
        _proposal,
        model_ref="test_provider:task_follow_up_v1",
        before_return=revoke_current_authority,
    )
    classifier = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        denied = _runtime(
            session,
            model=model,
            classifier=classifier,
            timeline=task_timeline,
        ).run(command)

    _assert_denied(denied)
    assert len(model.requests) == 1
    assert classifier.requests == []
    assert _counts(ft012_database) == before
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 0,
        "publication_denied": 1,
        "messages": 0,
        "classifications": 0,
        "dispatches": 0,
        "tasks": 0,
    }

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
    _assert_denied(retry)
    assert retry_model.requests == retry_classifier.requests == []
    assert _counts(ft012_database) == before


def test_classifier_provider_failure_and_write_guard_denial_have_no_task_effect(
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
    assert _counts(ft012_database) == before

    # A fresh run reaches classifier I/O, then archive wins its owning write guard.
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
    assert _counts(ft012_database) == before


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
    assert _counts(ft012_database) == before


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
    descriptor = str(records[3].as_provider_value()).lower()
    assert "6.25" not in descriptor
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
    bad = {**_proposal(request), "action": "approve"}
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpModelResultV1.from_untrusted(bad, request=request)
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


def test_runtime_fingerprint_denied_retry_conflict_and_new_run_eligibility(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    expected = canonical_fingerprint(
        {
            "schema_version": 1,
            "run_id": str(command.run_id),
            "requested_at": command.requested_at.isoformat().replace("+00:00", "Z"),
            "request_id": str(boss.request_id),
            "session_id": str(boss.session_id),
            "account_id": str(boss.account_id),
            "farm_id": str(boss.farm_id),
            "membership_id": str(boss.membership_id),
            "plant_id": str(plant.plant_id),
            "trigger_kind": "task_completed",
            "trigger_task_id": str(trigger),
        }
    )
    assert task_follow_up_command_fingerprint(command) == expected

    model = _Executor(
        _proposal,
        model_ref="test_provider:task_follow_up_v1",
        before_return=lambda: archive_plant(
            ft012_database,
            boss,
            plant_id=plant.plant_id,
        ),
    )
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        first = _runtime(
            session,
            model=model,
            classifier=safety,
            timeline=task_timeline,
        ).run(command)
    _assert_denied(first)
    assert (len(model.requests), _runtime_audit_count(task_timeline), len(safety.requests)) == (
        1,
        1,
        0,
    )
    with ft012_database.session() as session:
        row = session.get(TaskFollowUpRuntimeDisposition, command.run_id)
        assert row is not None
        assert row.command_sha256 == expected
        assert row.outcome == "publication_denied"
        assert row.message_id is row.input_sha256 is None
        assert row.denial_code == "AGENT_PUBLICATION_BLOCKED"

    _restore(ft012_database, boss, plant)
    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
    )
    with ft012_database.session() as session:
        identical = _runtime(
            session,
            model=retry_model,
            classifier=retry_safety,
            timeline=task_timeline,
        ).run(command)
        conflict = _runtime(
            session,
            model=retry_model,
            classifier=retry_safety,
            timeline=task_timeline,
        ).run(replace(command, requested_at=NOW + timedelta(seconds=1)))
    _assert_denied(identical)
    _assert_local(
        conflict,
        "conflict",
        "TASK_FOLLOW_UP_RUN_CONFLICT",
    )
    assert retry_model.requests == retry_safety.requests == []
    assert _runtime_audit_count(task_timeline) == 1
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 0,
        "publication_denied": 1,
        "messages": 0,
        "classifications": 0,
        "dispatches": 0,
        "tasks": 0,
    }
    _fresh_success(ft012_database, boss, plant, trigger, task_timeline)


def test_group1_forced_advisory_collision_keeps_full_uuid_authority_isolated(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant_one = ft012_seed
    plant_two = create_active_plant(
        ft012_database,
        boss,
        plant_key=f"ft012_lock_collision_{uuid.uuid4().hex[:8]}",
    )
    triggers = (
        _seed_completed_task(ft012_database, farm, boss, plant_one, task_timeline),
        _seed_completed_task(ft012_database, farm, boss, plant_two, task_timeline),
    )
    task_timeline.events.clear()
    commands = (
        _command(boss, plant_one, triggers[0]),
        _command(boss, plant_two, triggers[1]),
    )
    model_barrier = Barrier(2)
    models = [
        _Executor(
            _proposal,
            model_ref="test_provider:task_follow_up_v1",
            before_return=lambda: model_barrier.wait(timeout=20),
        )
        for _index in range(2)
    ]
    safeties = [
        _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
        for _index in range(2)
    ]

    def denied(index):
        with ft012_database.session() as session:
            return TaskFollowUpRuntimeService(
                session,
                model_executor=models[index],
                safety_classifier_executor=safeties[index],
                authorization_guard=_AlwaysDeniedGuard(),
                timeline_append=task_timeline,
                clock=lambda: NOW,
                run_lock_key=lambda _run_id: 912_040,
            ).run(commands[index])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(denied, index) for index in range(2)]
        results = [future.result(timeout=30) for future in futures]
    assert commands[0].run_id != commands[1].run_id
    assert all(task_follow_up_command_fingerprint(item) for item in commands)
    for result in results:
        _assert_denied(result)
    assert sum(len(model.requests) for model in models) == 2
    assert _runtime_audit_count(task_timeline) == 2
    assert sum(len(safety.requests) for safety in safeties) == 0
    with ft012_database.session() as session:
        rows = list(
            session.scalars(
                select(TaskFollowUpRuntimeDisposition).where(
                    TaskFollowUpRuntimeDisposition.run_id.in_(
                        [command.run_id for command in commands]
                    )
                )
            )
        )
    assert len(rows) == 2
    assert {row.run_id for row in rows} == {command.run_id for command in commands}
    assert {row.plant_id for row in rows} == {plant_one.plant_id, plant_two.plant_id}
    assert all(row.outcome == "publication_denied" for row in rows)
    for command in commands:
        assert _authority_counts(ft012_database, run_id=command.run_id) == {
            "runtime": 1,
            "handed_off": 0,
            "publication_denied": 1,
            "messages": 0,
            "classifications": 0,
            "dispatches": 0,
            "tasks": 0,
        }
    _fresh_success(ft012_database, boss, plant_one, triggers[0], task_timeline)


def test_group2_crash_after_handoff_is_one_shot_and_retry_is_incomplete(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    with ft012_database.session() as session, pytest.raises(_ProcessStop):
        TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            classification_service=_StopBeforeClassifier(),
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(command)
    assert (len(model.requests), _runtime_audit_count(task_timeline)) == (1, 1)
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 1,
        "publication_denied": 0,
        "messages": 1,
        "classifications": 0,
        "dispatches": 0,
        "tasks": 0,
    }

    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        retry = _runtime(
            session,
            model=retry_model,
            classifier=retry_safety,
            timeline=task_timeline,
        ).run(command)
    _assert_local(
        retry,
        "incomplete",
        "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
    )
    assert retry_model.requests == retry_safety.requests == []
    assert _runtime_audit_count(task_timeline) == 1
    _fresh_success(ft012_database, boss, plant, trigger, task_timeline)


@pytest.mark.parametrize("failure_kind", ["guard", "persistence"])
def test_group3_classifier_failure_never_replays_committed_handoff(
    ft012_database,
    ft012_seed,
    task_timeline,
    failure_kind,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        classifier = SafetyGateClassificationService(
            session,
            model_executor=safety,
            authorization_guard=(
                _AlwaysDeniedGuard()
                if failure_kind == "guard"
                else DatabaseRuntimeAuthorizationGuard(session, clock=lambda: NOW)
            ),
            repository=(
                _FailingSafetyRepository(session)
                if failure_kind == "persistence"
                else None
            ),
            clock=lambda: NOW,
        )
        first = TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            classification_service=classifier,
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(command)
    assert first.route_status == "failed"
    assert first.failure_stage == "classification"
    assert (len(model.requests), _runtime_audit_count(task_timeline)) == (1, 1)
    assert len(safety.requests) == (0 if failure_kind == "guard" else 1)
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 1,
        "publication_denied": 0,
        "messages": 1,
        "classifications": 0,
        "dispatches": 0,
        "tasks": 0,
    }
    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        retry = _runtime(
            session,
            model=retry_model,
            classifier=retry_safety,
            timeline=task_timeline,
        ).run(command)
    _assert_local(
        retry,
        "incomplete",
        "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
    )
    assert retry_model.requests == retry_safety.requests == []
    _fresh_success(ft012_database, boss, plant, trigger, task_timeline)


def test_group4_classification_then_crash_returns_classification_ref_on_retry(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session, pytest.raises(_ProcessStop):
        TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            safety_classifier_executor=safety,
            ordinary_task_service=_StopBeforeTaskService(),
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(command)
    assert (len(model.requests), _runtime_audit_count(task_timeline), len(safety.requests)) == (
        1,
        1,
        1,
    )
    with ft012_database.session() as session:
        row = session.get(TaskFollowUpRuntimeDisposition, command.run_id)
        assert row is not None and row.message_id is not None
        classification_ref = f"safety_classification:{row.message_id}"
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 1,
        "publication_denied": 0,
        "messages": 1,
        "classifications": 1,
        "dispatches": 0,
        "tasks": 0,
    }
    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        retry = _runtime(
            session,
            model=retry_model,
            classifier=retry_safety,
            timeline=task_timeline,
        ).run(command)
    _assert_local(
        retry,
        "incomplete",
        "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
        classification_ref=classification_ref,
    )
    assert retry_model.requests == retry_safety.requests == []
    _fresh_success(ft012_database, boss, plant, trigger, task_timeline)


def test_group5_handed_off_retry_matrix_is_read_only_and_exact(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()

    def retry(command):
        model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
        safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
        with ft012_database.session() as session:
            task_counter = _CountingTaskService(
                TaskFollowUpService(
                    session,
                    timeline_appender=task_timeline,
                    clock=lambda: NOW,
                )
            )
            result = TaskFollowUpRuntimeService(
                session,
                model_executor=model,
                safety_classifier_executor=safety,
                ordinary_task_service=task_counter,
                timeline_append=task_timeline,
                clock=lambda: NOW,
            ).run(command)
        assert (len(model.requests), len(safety.requests), task_counter.calls) == (0, 0, 0)
        return result

    # Exact non-taskable classification, no classified dispatch.
    non_taskable_command = _command(boss, plant, trigger)
    with ft012_database.session() as session:
        non_taskable_first = _runtime(
            session,
            model=_Executor(_proposal, model_ref="test_provider:task_follow_up_v1"),
            classifier=_Executor(
                lambda _request: {
                    "schema_version": 1,
                    "candidate_classification": "safe_information",
                    "safe_task_kind": None,
                    "physical_action_kind": None,
                },
                model_ref="test_provider:safety_gate_v1",
            ),
            timeline=task_timeline,
        ).run(non_taskable_command)
    assert non_taskable_first.route_status == "not_taskable"
    assert non_taskable_first.classification_ref is not None
    _assert_local(
        retry(non_taskable_command),
        "not_taskable",
        "TASK_FOLLOW_UP_ALREADY_NOT_TASKABLE",
        classification_ref=non_taskable_first.classification_ref,
    )

    # Matching classification whose sole Task writer records immutable denial.
    denied_command = _command(boss, plant, trigger)
    denied_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    denied_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        classifier = SafetyGateClassificationService(
            session,
            model_executor=denied_safety,
            clock=lambda: NOW,
        )
        denied_first = TaskFollowUpRuntimeService(
            session,
            model_executor=denied_model,
            classification_service=_ArchiveAfterClassification(
                classifier,
                lambda: archive_plant(
                    ft012_database,
                    boss,
                    plant_id=plant.plant_id,
                ),
            ),
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(denied_command)
    assert denied_first.route_status == "failed"
    assert denied_first.failure_stage == "task"
    assert denied_first.classification_ref is not None
    _restore(ft012_database, boss, plant)
    _assert_local(
        retry(denied_command),
        "denied",
        "TASK_FOLLOW_UP_DISPATCH_DENIED",
        classification_ref=denied_first.classification_ref,
    )

    # Consumed graph returns exact Task while current, blocks under archive,
    # then reports graph failure when the consumed Task is synthetically absent.
    consumed_command = _command(boss, plant, trigger)
    consumed_first = _fresh_success(
        ft012_database,
        boss,
        plant,
        trigger,
        task_timeline,
        command=consumed_command,
    )
    _assert_local(
        retry(consumed_command),
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=consumed_first.classification_ref,
        task_ref=consumed_first.task_ref,
    )
    archive_plant(ft012_database, boss, plant_id=plant.plant_id)
    _assert_local(
        retry(consumed_command),
        "blocked",
        "TASK_FOLLOW_UP_REPLAY_BLOCKED",
    )
    _restore(ft012_database, boss, plant)
    assert consumed_first.task_ref is not None
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, uuid.UUID(consumed_first.task_ref.split(":", 1)[1]))
        assert task is not None
        session.delete(task)
    _assert_local(
        retry(consumed_command),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def _create_denied_dispatch_run(database, seed, timeline):
    farm, boss, _membership, plant = seed
    trigger = _seed_completed_task(database, farm, boss, plant, timeline)
    timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with database.session() as session:
        classifier = SafetyGateClassificationService(
            session,
            model_executor=safety,
            clock=lambda: NOW,
        )
        first = _runtime(
            session,
            model=model,
            timeline=timeline,
            classification_service=_ArchiveAfterClassification(
                classifier,
                lambda: archive_plant(
                    database,
                    boss,
                    plant_id=plant.plant_id,
                ),
            ),
        ).run(command)
    assert first.route_status == "failed"
    assert first.failure_stage == "task"
    assert first.classification_ref is not None
    assert (len(model.requests), len(safety.requests), _runtime_audit_count(timeline)) == (
        1,
        1,
        1,
    )
    _restore(database, boss, plant)
    return farm, boss, plant, trigger, command


def _read_only_retry(database, command, timeline):
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with database.session() as session:
        result = _runtime(
            session,
            model=model,
            classifier=safety,
            timeline=timeline,
        ).run(command)
    assert model.requests == safety.requests == []
    return result


def _task_create_fingerprint(task: Task) -> str:
    return canonical_fingerprint(
        {
            "schema_version": 1,
            "source_branch": "classified_message",
            "request_id": str(task.create_request_id),
            "message_id": str(task.classification_message_id),
            "task_kind": task.kind,
            "display_text": task.display_text,
            "source_refs": task.source_refs,
        }
    )


def _rewrite_task_and_commitment(session, task: Task) -> str:
    fingerprint = _task_create_fingerprint(task)
    task.create_request_fingerprint = fingerprint
    disposition = session.scalar(
        select(OrdinaryTaskDispatchDisposition).where(
            OrdinaryTaskDispatchDisposition.run_id == task.create_request_id
        )
    )
    assert disposition is not None and disposition.outcome == "consumed"
    disposition.expected_task_create_fingerprint = fingerprint
    return fingerprint


def _assert_commitment_write_once_error(error: DBAPIError) -> None:
    assert getattr(error.orig, "sqlstate", None) == "23514"
    assert getattr(getattr(error.orig, "diag", None), "constraint_name", None) == (
        "ck_ordinary_task_dispatch_commitment_write_once"
    )


def _seed_consumed_graph(database, seed, timeline):
    farm, boss, _membership, plant = seed
    trigger = _seed_completed_task(database, farm, boss, plant, timeline)
    timeline.events.clear()
    command = _command(boss, plant, trigger)
    first = _fresh_success(
        database,
        boss,
        plant,
        trigger,
        timeline,
        command=command,
    )
    assert first.task_ref is not None
    return (
        farm,
        boss,
        plant,
        trigger,
        command,
        uuid.UUID(first.task_ref.split(":", 1)[1]),
    )


def _seed_consumed_outcome_graph(database, seed, timeline, selected_indexes):
    farm, boss, _membership, plant = seed
    decision_id, _ph, _ec = _pending_decision(
        database,
        farm,
        boss,
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
            _approval_command(boss, plant, decision_id)
        ).action_task
    assert action is not None
    with database.session() as session:
        follow_up = TaskFollowUpService(
            session,
            timeline_appender=timeline,
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
    evidence = _measurement(database, boss, plant, ph="6.25", measured_at=NOW)
    with database.session() as session:
        completed = TaskFollowUpService(
            session,
            timeline_appender=timeline,
            clock=lambda: NOW,
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
    timeline.events.clear()
    command = _command(
        boss,
        plant,
        completed.task.task_id,
        trigger_kind="follow_up_outcome_recorded",
    )

    def selected_proposal(request):
        return {
            **_proposal(request),
            "source_refs": [request.source_refs[index] for index in selected_indexes],
        }

    model = _Executor(
        selected_proposal,
        model_ref="test_provider:task_follow_up_v1",
    )
    safety = _Executor(
        _safety_candidate,
        model_ref="test_provider:safety_gate_v1",
    )
    with database.session() as session:
        first = _runtime(
            session,
            model=model,
            classifier=safety,
            timeline=timeline,
        ).run(command)
    _assert_created(first)
    assert first.task_ref is not None
    assert len(model.requests) == 1
    return command, first, model.requests[0].source_refs


def test_denied_retry_rejects_same_run_task_on_alternate_classification(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, plant, trigger, command = _create_denied_dispatch_run(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    alternate_message_id = uuid.uuid4()
    refs = [
        f"message_envelope:{alternate_message_id}",
        f"safety_classification:{alternate_message_id}",
        f"task:{trigger}",
    ]
    fingerprint = canonical_fingerprint(
        {
            "schema_version": 1,
            "source_branch": "classified_message",
            "request_id": str(command.run_id),
            "message_id": str(alternate_message_id),
            "task_kind": "check",
            "display_text": "Synthetic alternate-classification Task.",
            "source_refs": refs,
        }
    )
    with ft012_database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=alternate_message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id="task_follow_up",
                classifier_version="safety_gate_v1",
                classification="safe_task_request",
                safe_task_kind="check",
                reason_code="safe_check_request",
                physical_action_kind=None,
                provider_status="completed",
                model_ref="test_provider:safety_gate_v1",
                input_sha256="a" * 64,
                result_sha256="b" * 64,
                created_at=NOW,
            )
        )
        session.add(
            Task(
                task_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                kind="check",
                status="open",
                display_text="Synthetic alternate-classification Task.",
                source_type="safe_task_request",
                source_refs=refs,
                classification_message_id=alternate_message_id,
                approval_id=None,
                parent_action_task_id=None,
                due_at=None,
                created_by_account_id=boss.account_id,
                created_by_membership_id=boss.membership_id,
                created_by_role_preset=boss.role_preset.value,
                created_by_agent_id="task_follow_up",
                created_at=NOW,
                create_request_id=command.run_id,
                create_request_fingerprint=fingerprint,
                created_event_ref={"synthetic": True},
            )
        )

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


@pytest.mark.parametrize(
    "mutated_fields",
    [
        ("created_by_account_id",),
        ("created_by_membership_id",),
        ("created_by_role_preset",),
        (
            "created_by_account_id",
            "created_by_membership_id",
            "created_by_role_preset",
        ),
    ],
    ids=["account", "membership", "role", "complete_actor"],
)
def test_consumed_retry_rejects_mutated_human_actor_attribution(
    ft012_database,
    ft012_seed,
    task_timeline,
    mutated_fields,
):
    farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    alternate_boss, _membership = create_actor(ft012_database, farm, "boss")
    values = {
        "created_by_account_id": alternate_boss.account_id,
        "created_by_membership_id": alternate_boss.membership_id,
        "created_by_role_preset": "engineer",
    }
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        for field in mutated_fields:
            setattr(task, field, values[field])

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def test_consumed_retry_rejects_corrupt_human_actor_attribution(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    alternate_boss, _membership = create_actor(ft012_database, farm, "boss")
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        task.created_by_account_id = alternate_boss.account_id
        task.created_by_membership_id = alternate_boss.membership_id
        task.created_by_role_preset = alternate_boss.role_preset.value

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def test_consumed_retry_rejects_alternate_valid_source_graph_with_recomputed_fingerprint(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, plant, trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    alternate_trigger = _seed_completed_task(
        ft012_database,
        farm,
        boss,
        plant,
        task_timeline,
    )
    assert alternate_trigger != trigger
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        task.source_refs = [*task.source_refs[:-1], f"task:{alternate_trigger}"]
        task.create_request_fingerprint = _task_create_fingerprint(task)

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


@pytest.mark.parametrize(
    "source_mutation",
    ["uppercase", "compact", "duplicate", "reordered_prefix"],
)
def test_consumed_retry_rejects_noncanonical_or_invalid_source_graph(
    ft012_database,
    ft012_seed,
    task_timeline,
    source_mutation,
):
    _farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        if source_mutation == "uppercase":
            kind, identifier = task.source_refs[-1].split(":", 1)
            task.source_refs = [*task.source_refs[:-1], f"{kind}:{identifier.upper()}"]
        elif source_mutation == "compact":
            kind, identifier = task.source_refs[-1].split(":", 1)
            task.source_refs = [
                *task.source_refs[:-1],
                f"{kind}:{identifier.replace('-', '')}",
            ]
        elif source_mutation == "duplicate":
            task.source_refs = [*task.source_refs, task.source_refs[-1]]
        else:
            task.source_refs = [
                task.source_refs[1],
                task.source_refs[0],
                *task.source_refs[2:],
            ]
        task.create_request_fingerprint = _task_create_fingerprint(task)

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


@pytest.mark.parametrize(
    "selected_indexes",
    [(0,), (0, 1), (0, 2), (0, 1, 2, 3)],
    ids=["first", "prefix_two", "ordered_sparse", "all"],
)
def test_consumed_retry_accepts_independently_rebuilt_canonical_source_subsets(
    ft012_database,
    ft012_seed,
    task_timeline,
    selected_indexes,
):
    command, first, available_refs = _seed_consumed_outcome_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
        selected_indexes,
    )
    selected_refs = tuple(available_refs[index] for index in selected_indexes)
    assert selected_refs == tuple(ref for ref in available_refs if ref in selected_refs)
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=first.classification_ref,
        task_ref=first.task_ref,
    )


@pytest.mark.parametrize(
    "commitment_corruption",
    ["wrong", "malformed", "legacy_null"],
)
def test_consumed_retry_rejects_missing_or_wrong_independent_commitment(
    ft012_database,
    ft012_seed,
    task_timeline,
    commitment_corruption,
):
    _farm, _boss, _plant, _trigger, command, _task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.engine().connect() as connection:
        connection.exec_driver_sql(
            "DROP TRIGGER trg_ordinary_task_dispatch_commitment_write_once "
            "ON ordinary_task_dispatch_dispositions"
        )
        if commitment_corruption != "wrong":
            connection.exec_driver_sql(
                "ALTER TABLE ordinary_task_dispatch_dispositions "
                "DROP CONSTRAINT "
                "ck_ordinary_task_dispatch_dispositions_commitment_matrix"
            )
        connection.commit()
    values = {
        "wrong": "e" * 64,
        "malformed": "NOT-A-LOWERCASE-SHA256",
        "legacy_null": None,
    }
    with ft012_database.session() as session, session.begin():
        disposition = session.scalar(
            select(OrdinaryTaskDispatchDisposition).where(
                OrdinaryTaskDispatchDisposition.run_id == command.run_id
            )
        )
        assert disposition is not None
        disposition.expected_task_create_fingerprint = values[
            commitment_corruption
        ]

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def test_coordinated_text_and_both_digests_are_rejected_and_rolled_back(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    _farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session:
        with pytest.raises(DBAPIError) as rejected, session.begin():
            task = session.get(Task, task_id, with_for_update=True)
            assert task is not None
            task.display_text = "Coordinated replacement of persisted Task text."
            _rewrite_task_and_commitment(session, task)
        _assert_commitment_write_once_error(rejected.value)
    with ft012_database.session() as session:
        preserved = session.get(Task, task_id)
        assert preserved is not None and preserved.classification_message_id is not None
        classification_ref = (
            f"safety_classification:{preserved.classification_message_id}"
        )
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=classification_ref,
        task_ref=f"task:{task_id}",
    )


def test_coordinated_source_subset_and_both_digests_are_rejected_and_rolled_back(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    command, first, available_refs = _seed_consumed_outcome_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
        (0,),
    )
    assert first.task_ref is not None and len(available_refs) >= 2
    task_id = uuid.UUID(first.task_ref.split(":", 1)[1])
    with ft012_database.session() as session:
        with pytest.raises(DBAPIError) as rejected, session.begin():
            task = session.get(Task, task_id, with_for_update=True)
            assert task is not None
            task.source_refs = [*task.source_refs[:2], available_refs[1]]
            _rewrite_task_and_commitment(session, task)
        _assert_commitment_write_once_error(rejected.value)
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=first.classification_ref,
        task_ref=first.task_ref,
    )


def test_coordinated_kind_classification_and_both_digests_are_rejected_and_rolled_back(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    _farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session:
        with pytest.raises(DBAPIError) as rejected, session.begin():
            task = session.get(Task, task_id, with_for_update=True)
            assert task is not None and task.classification_message_id is not None
            classification = session.get(
                SafetyClassification,
                task.classification_message_id,
                with_for_update=True,
            )
            assert classification is not None
            task.kind = "measurement"
            classification.safe_task_kind = "measurement"
            classification.reason_code = "safe_measurement_request"
            classification.result_sha256 = canonical_fingerprint(
                {
                    "schema_version": 1,
                    "message_id": str(classification.message_id),
                    "classifier_version": classification.classifier_version,
                    "classification": classification.classification,
                    "safe_task_kind": classification.safe_task_kind,
                    "reason_code": classification.reason_code,
                }
            )
            _rewrite_task_and_commitment(session, task)
        _assert_commitment_write_once_error(rejected.value)
    with ft012_database.session() as session:
        preserved = session.get(Task, task_id)
        assert preserved is not None and preserved.classification_message_id is not None
        classification_ref = (
            f"safety_classification:{preserved.classification_message_id}"
        )

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=classification_ref,
        task_ref=f"task:{task_id}",
    )


def test_task_only_fingerprint_recomputation_still_fails_closed(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    _farm, _boss, _plant, _trigger, command, task_id = _seed_consumed_graph(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        task.display_text = "Task-only fingerprint recomputation control."
        task.create_request_fingerprint = _task_create_fingerprint(task)

    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def test_corrupt_denied_dispatch_with_task_fails_closed(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, plant, trigger, command = _create_denied_dispatch_run(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session, session.begin():
        runtime = session.get(TaskFollowUpRuntimeDisposition, command.run_id)
        assert runtime is not None and runtime.message_id is not None
        session.add(
            Task(
                task_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                kind="check",
                status="open",
                display_text="Synthetic contradictory Task.",
                source_type="safe_task_request",
                source_refs=[
                    f"message_envelope:{runtime.message_id}",
                    f"safety_classification:{runtime.message_id}",
                    f"task:{trigger}",
                ],
                classification_message_id=runtime.message_id,
                approval_id=None,
                parent_action_task_id=None,
                due_at=None,
                created_by_account_id=boss.account_id,
                created_by_membership_id=boss.membership_id,
                created_by_role_preset="boss",
                created_by_agent_id="task_follow_up",
                created_at=NOW,
                create_request_id=command.run_id,
                create_request_fingerprint="d" * 64,
                created_event_ref={"synthetic": True},
            )
        )
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


@pytest.mark.parametrize("corruption", ["fingerprint", "source_graph"])
def test_corrupt_consumed_task_authority_fails_closed(
    ft012_database,
    ft012_seed,
    task_timeline,
    corruption,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    first = _fresh_success(
        ft012_database,
        boss,
        plant,
        trigger,
        task_timeline,
        command=command,
    )
    assert first.task_ref is not None
    task_id = uuid.UUID(first.task_ref.split(":", 1)[1])
    with ft012_database.session() as session, session.begin():
        task = session.get(Task, task_id, with_for_update=True)
        assert task is not None
        if corruption == "fingerprint":
            task.create_request_fingerprint = "e" * 64
        else:
            task.source_refs = [*task.source_refs[:-1], f"task:{uuid.uuid4()}"]
            task.create_request_fingerprint = canonical_fingerprint(
                {
                    "schema_version": 1,
                    "source_branch": "classified_message",
                    "request_id": str(command.run_id),
                    "message_id": str(task.classification_message_id),
                    "task_kind": task.kind,
                    "display_text": task.display_text,
                    "source_refs": task.source_refs,
                }
            )
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


@pytest.mark.parametrize(
    "corrupt_event_ref",
    [
        lambda value: {
            **value,
            "timeline_ref": f"timeline.jsonl#{uuid.uuid4()}",
        },
        lambda value: {**value, "created_at": NOW.isoformat().replace("+00:00", "Z")},
        lambda value: {
            **value,
            "created_at": NOW.astimezone(timezone(timedelta(hours=1))).isoformat(),
        },
    ],
    ids=["mismatched_uuid", "noncanonical_utc", "non_utc_timestamp"],
)
def test_corrupt_runtime_event_ref_fails_closed(
    ft012_database,
    ft012_seed,
    task_timeline,
    corrupt_event_ref,
):
    _farm, _boss, _plant, _trigger, command = _create_denied_dispatch_run(
        ft012_database,
        ft012_seed,
        task_timeline,
    )
    with ft012_database.session() as session, session.begin():
        runtime = session.get(
            TaskFollowUpRuntimeDisposition,
            command.run_id,
            with_for_update=True,
        )
        assert runtime is not None
        runtime.runtime_event_ref = corrupt_event_ref(dict(runtime.runtime_event_ref))
    _assert_local(
        _read_only_retry(ft012_database, command, task_timeline),
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )


def test_post_audit_commit_failure_is_local_failure_with_noise_only(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    audit_appended = False

    def append(event_value):
        nonlocal audit_appended
        result = task_timeline(event_value)
        if event_value.event_type == "agent_runtime_decided":
            audit_appended = True
        return result

    with ft012_database.session() as session:
        def fail_terminal_commit(_session):
            if audit_appended:
                raise RuntimeError("synthetic terminal commit failure")

        event.listen(session, "before_commit", fail_terminal_commit)
        result = TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            safety_classifier_executor=safety,
            timeline_append=append,
            clock=lambda: NOW,
        ).run(command)
    _assert_local(
        result,
        "failed",
        "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
    )
    assert (len(model.requests), _runtime_audit_count(task_timeline), len(safety.requests)) == (
        1,
        1,
        0,
    )
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 0,
        "handed_off": 0,
        "publication_denied": 0,
        "messages": 0,
        "classifications": 0,
        "dispatches": 0,
        "tasks": 0,
    }


def test_group6_lock_order_consumed_success_v1(
    ft012_database,
    ft012_seed,
    task_timeline,
):
    class TraceLog(list):
        enabled = True

        def append(self, item):
            if self.enabled:
                super().append(item)

    class QuietAssembler:
        def __init__(self, session, trace, repository):
            self._session = session
            self._trace = trace
            self._delegate = DatabaseTaskFollowUpInputAssembler(
                session,
                repository=repository,
            )

        def assemble(self, *args, **kwargs):
            self._trace.enabled = False
            try:
                result = self._delegate.assemble(*args, **kwargs)
                if self._session.in_transaction():
                    self._session.commit()
                return result
            finally:
                self._trace.enabled = True

    class QuietClassifier:
        def __init__(self, delegate, trace):
            self._delegate = delegate
            self._trace = trace

        def classify(self, command):
            self._trace.enabled = False
            try:
                return self._delegate.classify(command)
            finally:
                self._trace.enabled = True

    def advisory_is_free(key):
        with ft012_database.engine().connect() as connection:
            acquired = connection.exec_driver_sql(
                "SELECT pg_try_advisory_lock(%s)",
                (key,),
            ).scalar_one()
            if acquired:
                connection.exec_driver_sql(
                    "SELECT pg_advisory_unlock(%s)",
                    (key,),
                )
            connection.commit()
        return acquired

    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    lock_key = task_follow_up_run_lock_key(command.run_id)
    trace = TraceLog()
    rollback_calls = 0
    model = None
    safety = None
    task_counter = None

    with ft012_database.session() as session:
        def after_commit(_session):
            trace.append("commit")

        def after_rollback(_session):
            nonlocal rollback_calls
            if trace.enabled:
                rollback_calls += 1

        def before_flush(flush_session, _context, _instances):
            if any(
                isinstance(row, TaskFollowUpRuntimeDisposition)
                for row in flush_session.new
            ):
                trace.append("runtime.insert")
            if any(isinstance(row, Task) for row in flush_session.new):
                trace.append("writer.writes")

        event.listen(session, "after_commit", after_commit)
        event.listen(session, "after_rollback", after_rollback)
        event.listen(session, "before_flush", before_flush)
        runtime_repository = _TraceRepository(session, trace)
        writer_repository = _TraceRepository(session, trace, writer=True)

        def model_entry():
            assert not session.in_transaction()
            assert advisory_is_free(lock_key)
            trace.append("model")

        def safety_entry():
            assert not session.in_transaction()
            assert advisory_is_free(lock_key)
            list.append(trace, "safety")

        model = _Executor(
            _proposal,
            model_ref="test_provider:task_follow_up_v1",
            before_return=model_entry,
        )
        safety = _Executor(
            _safety_candidate,
            model_ref="test_provider:safety_gate_v1",
            before_return=safety_entry,
        )

        def append(event_value):
            trace.append(
                "runtime.audit"
                if event_value.event_type == "agent_runtime_decided"
                else "writer.audit"
            )
            return task_timeline(event_value)

        task_counter = _CountingTaskService(
            TaskFollowUpService(
                session,
                repository=writer_repository,
                timeline_appender=append,
                clock=lambda: NOW,
            )
        )
        classifier = QuietClassifier(
            SafetyGateClassificationService(
                session,
                model_executor=safety,
                clock=lambda: NOW,
            ),
            trace,
        )
        result = TaskFollowUpRuntimeService(
            session,
            model_executor=model,
            input_assembler=QuietAssembler(session, trace, runtime_repository),
            repository=runtime_repository,
            classification_service=classifier,
            ordinary_task_service=task_counter,
            timeline_append=append,
            clock=lambda: NOW,
        ).run(command)

    _assert_created(result)
    assert trace == [
        "runtime.advisory",
        "runtime.runtime",
        "runtime.classified",
        "commit",
        "model",
        "runtime.advisory",
        "runtime.runtime",
        "runtime.classified",
        "runtime.current",
        "runtime.audit",
        "runtime.insert",
        "commit",
        "safety",
        "writer.advisory",
        "writer.runtime",
        "writer.classified",
        "writer.classification",
        "writer.current",
        "writer.source",
        "writer.audit",
        "writer.writes",
        "commit",
    ]
    assert model is not None and safety is not None and task_counter is not None
    assert (len(model.requests), len(safety.requests), task_counter.calls) == (1, 1, 1)
    assert _runtime_audit_count(task_timeline) == 1
    assert [event.event_type for event in task_timeline.events] == [
        "agent_runtime_decided",
        "task_created",
    ]
    assert rollback_calls == 0
    assert _authority_counts(ft012_database, run_id=command.run_id) == {
        "runtime": 1,
        "handed_off": 1,
        "publication_denied": 0,
        "messages": 1,
        "classifications": 1,
        "dispatches": 1,
        "tasks": 1,
    }

    before = _authority_counts(ft012_database, run_id=command.run_id)
    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        retry_task = _CountingTaskService(
            TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            )
        )
        retry = TaskFollowUpRuntimeService(
            session,
            model_executor=retry_model,
            safety_classifier_executor=retry_safety,
            ordinary_task_service=retry_task,
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(command)
    _assert_local(
        retry,
        "duplicate",
        "TASK_FOLLOW_UP_ALREADY_CONSUMED",
        classification_ref=result.classification_ref,
        task_ref=result.task_ref,
    )
    assert (len(retry_model.requests), len(retry_safety.requests), retry_task.calls) == (
        0,
        0,
        0,
    )
    assert _authority_counts(ft012_database, run_id=command.run_id) == before
    fresh = _fresh_success(ft012_database, boss, plant, trigger, task_timeline)
    assert fresh.classification_ref != result.classification_ref
    assert fresh.task_ref != result.task_ref


@pytest.mark.parametrize(
    "barrier_order",
    [
        "eligible-first",
        "denied-first",
        "late-denial-first",
        "classified-writer-first",
    ],
)
def test_group7_exact_barrier_orders(
    ft012_database,
    ft012_seed,
    task_timeline,
    barrier_order,
):
    farm, boss, _membership, plant = ft012_seed
    trigger = _seed_completed_task(ft012_database, farm, boss, plant, task_timeline)
    task_timeline.events.clear()
    command = _command(boss, plant, trigger)
    model_barrier = Barrier(2)
    ready = {name: Event() for name in ("E", "D", "W", "L")}
    release = {name: Event() for name in ("E", "D", "W", "L")}
    task_ready = Event()
    task_release = Event()
    state = {}
    state_lock = Lock()
    rollback_calls = 0

    def invoke(label, *, deny_terminal, pause_task=False):
        nonlocal rollback_calls
        with ft012_database.session() as session:
            def after_rollback(_session):
                nonlocal rollback_calls
                with state_lock:
                    rollback_calls += 1

            event.listen(session, "after_rollback", after_rollback)
            repository = _PostModelGateRepository(
                session,
                ready=ready[label],
                release=release[label],
            )
            model = _Executor(
                _proposal,
                model_ref="test_provider:task_follow_up_v1",
                before_return=lambda: model_barrier.wait(timeout=20),
            )
            safety = _Executor(
                _safety_candidate,
                model_ref="test_provider:safety_gate_v1",
            )

            def before_task():
                if pause_task:
                    task_ready.set()
                    assert task_release.wait(timeout=20)

            task_counter = _CountingTaskService(
                TaskFollowUpService(
                    session,
                    timeline_appender=task_timeline,
                    clock=lambda: NOW,
                ),
                before_call=before_task,
            )
            with state_lock:
                state[label] = (model, safety, task_counter)
            return TaskFollowUpRuntimeService(
                session,
                model_executor=model,
                input_assembler=DatabaseTaskFollowUpInputAssembler(
                    session,
                    repository=repository,
                ),
                repository=repository,
                authorization_guard=(
                    _DenyOnlyUnclaimedRunGuard(session, clock=lambda: NOW)
                    if deny_terminal
                    else DatabaseRuntimeAuthorizationGuard(session, clock=lambda: NOW)
                ),
                classification_service=_OneTransactionClassifier(session, safety),
                ordinary_task_service=task_counter,
                timeline_append=task_timeline,
                clock=lambda: NOW,
            ).run(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        if barrier_order in {"eligible-first", "denied-first"}:
            futures = {
                "E": pool.submit(invoke, "E", deny_terminal=False),
                "D": pool.submit(invoke, "D", deny_terminal=True),
            }
            assert ready["E"].wait(timeout=20)
            assert ready["D"].wait(timeout=20)
            first_label = "E" if barrier_order == "eligible-first" else "D"
            second_label = "D" if first_label == "E" else "E"
            release[first_label].set()
            first = futures[first_label].result(timeout=30)
            release[second_label].set()
            second = futures[second_label].result(timeout=30)
        else:
            futures = {
                "W": pool.submit(
                    invoke,
                    "W",
                    deny_terminal=False,
                    pause_task=True,
                ),
                "L": pool.submit(invoke, "L", deny_terminal=True),
            }
            assert ready["W"].wait(timeout=20)
            assert ready["L"].wait(timeout=20)
            release["W"].set()
            assert task_ready.wait(timeout=30)
            if barrier_order == "late-denial-first":
                release["L"].set()
                first = futures["L"].result(timeout=30)
                task_release.set()
                second = futures["W"].result(timeout=30)
            else:
                task_release.set()
                first = futures["W"].result(timeout=30)
                release["L"].set()
                second = futures["L"].result(timeout=30)

    model_calls = sum(len(item[0].requests) for item in state.values())
    safety_calls = sum(len(item[1].requests) for item in state.values())
    task_calls = sum(item[2].calls for item in state.values())
    assert model_calls == 2
    assert rollback_calls == 0

    if barrier_order == "denied-first":
        _assert_denied(first)
        _assert_denied(second)
        assert first.as_value() == second.as_value()
        assert (model_calls, _runtime_audit_count(task_timeline), safety_calls, task_calls) == (
            2,
            1,
            0,
            0,
        )
        assert _authority_counts(ft012_database, run_id=command.run_id) == {
            "runtime": 1,
            "handed_off": 0,
            "publication_denied": 1,
            "messages": 0,
            "classifications": 0,
            "dispatches": 0,
            "tasks": 0,
        }
        expected_old = "denied"
        classification_ref = None
        task_ref = None
    else:
        if barrier_order == "eligible-first":
            _assert_created(first)
            classification_ref = first.classification_ref
            task_ref = first.task_ref
            _assert_local(
                second,
                "duplicate",
                "TASK_FOLLOW_UP_ALREADY_CONSUMED",
                classification_ref=classification_ref,
                task_ref=task_ref,
            )
        elif barrier_order == "late-denial-first":
            _assert_local(
                first,
                "incomplete",
                "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
                classification_ref=first.classification_ref,
            )
            _assert_created(second)
            classification_ref = second.classification_ref
            task_ref = second.task_ref
            assert first.classification_ref == classification_ref
        else:
            _assert_created(first)
            classification_ref = first.classification_ref
            task_ref = first.task_ref
            _assert_local(
                second,
                "duplicate",
                "TASK_FOLLOW_UP_ALREADY_CONSUMED",
                classification_ref=classification_ref,
                task_ref=task_ref,
            )
        assert (model_calls, _runtime_audit_count(task_timeline), safety_calls, task_calls) == (
            2,
            1,
            1,
            1,
        )
        assert [event.event_type for event in task_timeline.events] == [
            "agent_runtime_decided",
            "task_created",
        ]
        assert _authority_counts(ft012_database, run_id=command.run_id) == {
            "runtime": 1,
            "handed_off": 1,
            "publication_denied": 0,
            "messages": 1,
            "classifications": 1,
            "dispatches": 1,
            "tasks": 1,
        }
        expected_old = "duplicate"

    before_retry = _authority_counts(ft012_database, run_id=command.run_id)
    retry_model = _Executor(_proposal, model_ref="test_provider:task_follow_up_v1")
    retry_safety = _Executor(_safety_candidate, model_ref="test_provider:safety_gate_v1")
    with ft012_database.session() as session:
        retry_task = _CountingTaskService(
            TaskFollowUpService(
                session,
                timeline_appender=task_timeline,
                clock=lambda: NOW,
            )
        )
        old_run = TaskFollowUpRuntimeService(
            session,
            model_executor=retry_model,
            classification_service=_OneTransactionClassifier(session, retry_safety),
            ordinary_task_service=retry_task,
            timeline_append=task_timeline,
            clock=lambda: NOW,
        ).run(command)
    if expected_old == "denied":
        _assert_denied(old_run)
    else:
        _assert_local(
            old_run,
            "duplicate",
            "TASK_FOLLOW_UP_ALREADY_CONSUMED",
            classification_ref=classification_ref,
            task_ref=task_ref,
        )
    assert (len(retry_model.requests), len(retry_safety.requests), retry_task.calls) == (
        0,
        0,
        0,
    )
    assert _authority_counts(ft012_database, run_id=command.run_id) == before_retry

    fresh = _fresh_success(ft012_database, boss, plant, trigger, task_timeline)
    _assert_created(fresh)
    if task_ref is not None:
        assert fresh.task_ref != task_ref
