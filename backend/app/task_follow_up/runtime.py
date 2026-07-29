"""Provider-neutral Task and Follow-up Agent orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..agent_runtime.contracts import (
    AgentRuntimeOutcomeV1,
    AgentRuntimeValidationError,
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    RuntimeDecision,
)
from ..agent_runtime.service import DatabaseRuntimeAuthorizationGuard, ModelExecution
from ..safety_gate import (
    SafetyClassificationOutcomeV1,
    SafetyGateClassificationCommandV1,
    SafetyGateClassificationService,
    SafetyGateModelExecutor,
)
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    ClassifiedMessageTaskCommandV1,
    TaskKind,
    canonical_fingerprint,
    timestamp_text,
)
from .models import Outcome, Task
from .repository import (
    CurrentTaskScope,
    TaskFollowUpRepository,
    task_follow_up_run_lock_key,
)
from .runtime_contracts import (
    ORDINARY_TASK_KINDS,
    TaskFollowUpCommandV1,
    TaskFollowUpInputRecordV1,
    TaskFollowUpInvocationResultV1,
    TaskFollowUpModelResultV1,
    TaskFollowUpProviderRequestV1,
    TaskFollowUpRunResultV1,
    TaskFollowUpRuntimeValidationError,
)
from .service import TaskFollowUpService


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")
_ENVELOPE_REF_KINDS = frozenset(
    {"task", "outcome", "manual_measurement", "daily_checkin", "plant_state_record"}
)


class TaskFollowUpInputDenied(RuntimeError):
    def __init__(self, reason_code: str = "context_denied") -> None:
        self.reason_code = reason_code
        super().__init__("Task Follow-Up input context is unavailable.")


@dataclass(frozen=True, slots=True)
class AssembledTaskFollowUpInputV1:
    request: TaskFollowUpProviderRequestV1

    def __post_init__(self) -> None:
        if not isinstance(self.request, TaskFollowUpProviderRequestV1):
            raise TaskFollowUpRuntimeValidationError()


class TaskFollowUpInputAssembler(Protocol):
    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        trigger_kind: str,
        trigger_task_id: uuid.UUID,
        selected_at: datetime,
    ) -> AssembledTaskFollowUpInputV1: ...


class TaskFollowUpModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: TaskFollowUpProviderRequestV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class TaskFollowUpClassificationService(Protocol):
    def classify(
        self,
        command: SafetyGateClassificationCommandV1,
    ) -> SafetyClassificationOutcomeV1: ...


class DatabaseTaskFollowUpInputAssembler:
    """Load only the trigger Task, Outcome, and safe evidence descriptors."""

    def __init__(
        self,
        session: Session,
        *,
        repository: TaskFollowUpRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or TaskFollowUpRepository(session)

    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        trigger_kind: str,
        trigger_task_id: uuid.UUID,
        selected_at: datetime,
    ) -> AssembledTaskFollowUpInputV1:
        try:
            scope = self._repository.lock_current_scope(
                actor,
                plant_id=plant_id,
                now=selected_at,
            )
        except Exception:
            scope = None
        if not _scope_can_run(scope, actor=actor, plant_id=plant_id):
            raise TaskFollowUpInputDenied()
        assert scope is not None
        task = self._repository.task(trigger_task_id)
        if (
            task is None
            or task.farm_id != scope.farm_id
            or task.plant_id != scope.plant_id
            or not _trigger_matches(trigger_kind, task)
        ):
            raise TaskFollowUpInputDenied("input_contract_violation")

        outcome = self._repository.outcome_for_follow_up(task.task_id)
        if trigger_kind == "follow_up_outcome_recorded" and outcome is None:
            raise TaskFollowUpInputDenied("input_contract_violation")
        if outcome is not None and (
            outcome.farm_id != scope.farm_id or outcome.plant_id != scope.plant_id
        ):
            raise TaskFollowUpInputDenied("input_contract_violation")

        parent = (
            self._repository.task(task.parent_action_task_id)
            if task.parent_action_task_id is not None
            else None
        )
        if parent is not None and (
            parent.kind != "action"
            or parent.farm_id != scope.farm_id
            or parent.plant_id != scope.plant_id
        ):
            raise TaskFollowUpInputDenied("input_contract_violation")

        try:
            records = [_task_record(task)]
            if outcome is not None:
                records.append(_outcome_record(outcome))
            if parent is not None and len(records) < 4:
                records.append(_task_record(parent))
            if outcome is not None and len(records) < 4:
                evidence = self._first_evidence_record(
                    outcome,
                    farm_id=scope.farm_id,
                    plant_id=scope.plant_id,
                )
                if evidence is not None:
                    records.append(evidence)
            allowed = list(ORDINARY_TASK_KINDS)
            if task.kind == "action":
                allowed.remove("follow_up")
            request = TaskFollowUpProviderRequestV1(
                trigger_kind=trigger_kind,
                allowed_task_kinds=tuple(allowed),
                records=tuple(records),
            )
        except (TaskFollowUpRuntimeValidationError, TypeError, ValueError):
            raise TaskFollowUpInputDenied("input_contract_violation") from None
        return AssembledTaskFollowUpInputV1(request=request)

    def _first_evidence_record(
        self,
        outcome: Outcome,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> TaskFollowUpInputRecordV1 | None:
        for ref in outcome.evidence_refs:
            row = self._repository.evidence_for_ref(ref)
            if row is None:
                raise TaskFollowUpInputDenied("input_contract_violation")
            if (
                getattr(row, "farm_id", None) != farm_id
                or getattr(row, "plant_id", None) != plant_id
            ):
                raise TaskFollowUpInputDenied("input_contract_violation")
            return _evidence_record(ref, row)
        return None


class _TaskFollowUpMessageEnvelopeV1(MessageEnvelopeV1):
    __slots__ = ()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.message_id)
            or not _uuid4(self.run_id)
            or self.agent_id != "task_follow_up"
            or not _is_utc(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision is not RuntimeDecision.SPEAK
            or self.candidate_claim_type != "task_request"
            or isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int | float)
            or not 0 <= float(self.confidence) <= 1
            or not isinstance(self.candidate_output, str)
            or self.candidate_output != self.candidate_output.strip()
            or not 1 <= len(self.candidate_output) <= 1000
            or not 1 <= len(self.source_refs) <= 4
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not _envelope_ref(ref) for ref in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()


@dataclass(frozen=True, slots=True)
class _ModelStageResult:
    outcome: AgentRuntimeOutcomeV1 | None
    request: TaskFollowUpProviderRequestV1 | None
    model_result: TaskFollowUpModelResultV1 | None
    model_ref: str | None


@dataclass(frozen=True, slots=True)
class _CommittedHandoff:
    outcome: AgentRuntimeOutcomeV1
    model_result: TaskFollowUpModelResultV1


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


class TaskFollowUpRuntimeService:
    """Run the competence, classify its envelope, and use the sole Task writer."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: TaskFollowUpModelExecutor | None = None,
        safety_classifier_executor: SafetyGateModelExecutor | None = None,
        input_assembler: TaskFollowUpInputAssembler | None = None,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        classification_service: TaskFollowUpClassificationService | None = None,
        ordinary_task_service: TaskFollowUpService | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
        repository: TaskFollowUpRepository | None = None,
        run_lock_key: Callable[[uuid.UUID], int] | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._repository = repository or TaskFollowUpRepository(session)
        self._run_lock_key = run_lock_key or task_follow_up_run_lock_key
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._input_assembler = input_assembler or DatabaseTaskFollowUpInputAssembler(
            session,
            repository=self._repository,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._classification_service = classification_service or SafetyGateClassificationService(
            session,
            model_executor=safety_classifier_executor,
            clock=self._clock,
        )
        self._ordinary_task_service = ordinary_task_service or TaskFollowUpService(
            session,
            timeline_appender=self._timeline_append,
            clock=self._clock,
            run_lock_key=self._run_lock_key,
        )

    def run(self, command: TaskFollowUpCommandV1) -> TaskFollowUpInvocationResultV1:
        if not isinstance(command, TaskFollowUpCommandV1):
            raise TaskFollowUpRuntimeValidationError()
        stage = self._invoke_model(command)
        if stage.outcome is not None:
            return _result_for_runtime_outcome(command.run_id, stage.outcome)
        assert stage.request is not None
        assert stage.model_result is not None
        assert stage.model_ref is not None
        finalized = self._finalize_model_result(
            command,
            request=stage.request,
            result=stage.model_result,
            model_ref=stage.model_ref,
        )
        if not isinstance(finalized, _CommittedHandoff):
            return finalized
        outcome = finalized.outcome
        result = finalized.model_result
        assert result.proposed_task_kind is not None
        envelope = outcome.message_envelope
        assert envelope is not None

        self._rollback_active()
        try:
            classified = self._classification_service.classify(
                SafetyGateClassificationCommandV1(
                    classification_run_id=uuid.uuid4(),
                    requested_at=_as_utc(self._clock()),
                    actor_context=command.actor_context,
                    message_envelope=envelope,
                )
            )
        except Exception:
            classified = None
        self._rollback_active()
        if (
            classified is None
            or not classified.authoritative
            or classified.provider_status != "completed"
            or classified.classification_result is None
        ):
            return _failed_run(
                command.run_id,
                outcome,
                stage="classification",
                proposed_kind=result.proposed_task_kind,
            )
        classification = classified.classification_result
        classification_ref = f"safety_classification:{classification.message_id}"
        if (
            classification.classification != "safe_task_request"
            or classification.safe_task_kind != result.proposed_task_kind
        ):
            return TaskFollowUpRunResultV1(
                run_id=command.run_id,
                runtime_outcome=outcome,
                route_status="not_taskable",
                proposed_task_kind=result.proposed_task_kind,
                classification_ref=classification_ref,
                task_ref=None,
                failure_stage=None,
            )

        try:
            created = self._ordinary_task_service.create_ordinary_task(
                ClassifiedMessageTaskCommandV1(
                    actor_context=command.actor_context,
                    message_envelope=envelope,
                    classification=classification,
                    task_kind=TaskKind(result.proposed_task_kind),
                )
            )
        except Exception:
            return _failed_run(
                command.run_id,
                outcome,
                stage="task",
                proposed_kind=result.proposed_task_kind,
                classification_ref=classification_ref,
            )
        return TaskFollowUpRunResultV1(
            run_id=command.run_id,
            runtime_outcome=outcome,
            route_status=(
                "task_created" if created.result == "created" else "task_duplicate"
            ),
            proposed_task_kind=result.proposed_task_kind,
            classification_ref=classification_ref,
            task_ref=f"task:{created.task.task_id}",
            failure_stage=None,
        )

    def invoke(
        self,
        command: TaskFollowUpCommandV1,
    ) -> TaskFollowUpInvocationResultV1:
        return self.run(command)

    def _finalize_model_result(
        self,
        command: TaskFollowUpCommandV1,
        *,
        request: TaskFollowUpProviderRequestV1,
        result: TaskFollowUpModelResultV1,
        model_ref: str,
    ) -> TaskFollowUpInvocationResultV1 | _CommittedHandoff:
        """Recheck current authority, audit, and prepare one transient handoff."""

        self._rollback_active()
        try:
            with self._session.begin():
                scope = self._locked_current_scope(command)
        except Exception:
            self._rollback_active()
            scope = None

        if scope is None:
            outcome = self._audit(
                command=command,
                request=request,
                model_ref=model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                result=result,
                envelope=None,
            )
            return _failed_run(command.run_id, outcome, stage="runtime")

        if result.runtime_decision == "silent":
            common_silence_reason = (
                "insufficient_evidence"
                if result.reason_code == "no_new_task"
                else result.reason_code or "insufficient_evidence"
            )
            outcome = self._audit(
                command=command,
                request=request,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code=common_silence_reason,
                error_code=None,
                provider_call_status="completed",
                result=result,
                envelope=None,
            )
            if outcome.outcome_kind == "audit_failed":
                return _failed_run(command.run_id, outcome, stage="runtime")
            return TaskFollowUpRunResultV1(
                run_id=command.run_id,
                runtime_outcome=outcome,
                route_status="silent",
                proposed_task_kind=None,
                classification_ref=None,
                task_ref=None,
                failure_stage=None,
            )

        envelope = _message_envelope(
            command=command,
            scope=scope,
            result=result,
            created_at=_as_utc(self._clock()),
        )
        outcome = self._audit(
            command=command,
            request=request,
            model_ref=model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision="speak",
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            result=result,
            envelope=envelope,
        )
        if outcome.outcome_kind == "audit_failed":
            return _failed_run(command.run_id, outcome, stage="runtime")
        return _CommittedHandoff(outcome, result)

    def _invoke_model(self, command: TaskFollowUpCommandV1) -> _ModelStageResult:
        selected_at = _as_utc(self._clock())
        try:
            assembled = self._input_assembler.assemble(
                command.actor_context,
                plant_id=command.plant_id,
                trigger_kind=command.trigger_kind,
                trigger_task_id=command.trigger_task_id,
                selected_at=selected_at,
            )
        except TaskFollowUpInputDenied as denied:
            self._rollback_active()
            return _ModelStageResult(
                _context_denied(command.run_id, denied.reason_code),
                None,
                None,
                None,
            )
        except Exception:
            self._rollback_active()
            return _ModelStageResult(
                _context_denied(command.run_id, "input_contract_violation"),
                None,
                None,
                None,
            )
        try:
            self._commit_active()
        except SQLAlchemyError:
            self._rollback_active()
            return _ModelStageResult(
                _context_denied(command.run_id, "input_contract_violation"),
                None,
                None,
                None,
            )

        executor = self._model_executor
        model_ref = getattr(executor, "model_ref", None)
        if (
            executor is None
            or not isinstance(model_ref, str)
            or _MODEL_REF_RE.fullmatch(model_ref) is None
        ):
            return _ModelStageResult(
                _not_configured(command.run_id),
                None,
                None,
                None,
            )
        try:
            execution = executor.execute(assembled.request)
        except Exception:
            return _ModelStageResult(
                self._audit(
                    command=command,
                    request=assembled.request,
                    model_ref=model_ref,
                    outcome_kind="provider_failed",
                    status="failed",
                    final_decision=None,
                    reason_code="provider_failed",
                    error_code="AGENT_PROVIDER_FAILED",
                    provider_call_status="failed",
                    result=None,
                    envelope=None,
                ),
                None,
                None,
                None,
            )
        raw = _execution_result(execution, expected_model_ref=model_ref)
        try:
            result = TaskFollowUpModelResultV1.from_untrusted(
                raw,
                request=assembled.request,
            )
        except TaskFollowUpRuntimeValidationError:
            return _ModelStageResult(
                self._audit(
                    command=command,
                    request=assembled.request,
                    model_ref=model_ref,
                    outcome_kind="output_invalid",
                    status="blocked",
                    final_decision=None,
                    reason_code="output_invalid",
                    error_code="AGENT_OUTPUT_INVALID",
                    provider_call_status="completed",
                    result=None,
                    envelope=None,
                ),
                None,
                None,
                None,
            )
        return _ModelStageResult(
            None,
            assembled.request,
            result,
            model_ref,
        )

    def _locked_current_scope(
        self,
        command: TaskFollowUpCommandV1,
    ) -> CurrentAuthorizationScope | None:
        try:
            task_scope = self._repository.lock_current_scope(
                command.actor_context,
                plant_id=command.plant_id,
                now=_as_utc(self._clock()),
            )
            common_scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=command.plant_id,
            )
        except Exception:
            common_scope = None
            task_scope = None
        if (
            common_scope is None
            or not _scope_can_run(
                task_scope,
                actor=command.actor_context,
                plant_id=command.plant_id,
            )
            or common_scope.farm_id != command.actor_context.farm_id
            or common_scope.plant_id != command.plant_id
        ):
            return None
        return common_scope

    def _audit(
        self,
        *,
        command: TaskFollowUpCommandV1,
        request: TaskFollowUpProviderRequestV1,
        model_ref: str,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        result: TaskFollowUpModelResultV1 | None,
        envelope: MessageEnvelopeV1 | None,
    ) -> AgentRuntimeOutcomeV1:
        event = _runtime_event(
            command=command,
            request=request,
            model_ref=model_ref,
            outcome_kind=outcome_kind,
            status=status,
            final_decision=final_decision,
            reason_code=reason_code,
            error_code=error_code,
            result=result,
            envelope=envelope,
        )
        try:
            event_ref = self._timeline_append(event)
            if not _event_ref_valid(event_ref):
                raise ValueError
        except Exception:
            return AgentRuntimeOutcomeV1(
                run_id=command.run_id,
                outcome_kind="audit_failed",
                status="failed",
                final_decision=None,
                reason_code="audit_failed",
                error_code="AGENT_AUDIT_FAILED",
                message_envelope=None,
                event_ref=None,
                model_ref=model_ref,
                provider_call_status=provider_call_status,
                audit_status="failed",
            )
        return AgentRuntimeOutcomeV1(
            run_id=command.run_id,
            outcome_kind=outcome_kind,
            status=status,
            final_decision=final_decision,
            reason_code=reason_code,
            error_code=error_code,
            message_envelope=envelope,
            event_ref=dict(event_ref),
            model_ref=model_ref,
            provider_call_status=provider_call_status,
            audit_status="appended",
        )

    def _commit_active(self) -> None:
        if self._session.in_transaction():
            self._session.commit()

    def _rollback_active(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


def task_follow_up_command_fingerprint(command: TaskFollowUpCommandV1) -> str:
    if not isinstance(command, TaskFollowUpCommandV1):
        raise TaskFollowUpRuntimeValidationError()
    actor = command.actor_context
    return canonical_fingerprint(
        {
            "schema_version": 1,
            "run_id": str(command.run_id),
            "requested_at": timestamp_text(command.requested_at),
            "request_id": str(actor.request_id),
            "session_id": str(actor.session_id),
            "account_id": str(actor.account_id),
            "farm_id": str(actor.farm_id),
            "membership_id": str(actor.membership_id),
            "plant_id": str(command.plant_id),
            "trigger_kind": command.trigger_kind,
            "trigger_task_id": str(command.trigger_task_id),
        }
    )


def _result_for_runtime_outcome(
    run_id: uuid.UUID,
    outcome: AgentRuntimeOutcomeV1,
) -> TaskFollowUpRunResultV1:
    if outcome.outcome_kind == "model_silent":
        return TaskFollowUpRunResultV1(
            run_id=run_id,
            runtime_outcome=outcome,
            route_status="silent",
            proposed_task_kind=None,
            classification_ref=None,
            task_ref=None,
            failure_stage=None,
        )
    return _failed_run(run_id, outcome, stage="runtime")


def _task_record(task: Task) -> TaskFollowUpInputRecordV1:
    return TaskFollowUpInputRecordV1(
        record_type="task",
        source_ref=f"task:{task.task_id}",
        payload={
            "task_id": str(task.task_id),
            "kind": task.kind,
            "status": task.status,
            "source_type": task.source_type,
            "due_at": _timestamp(task.due_at) if task.due_at is not None else None,
            "created_at": _timestamp(task.created_at),
            "completed_at": (
                _timestamp(task.completed_at) if task.completed_at is not None else None
            ),
            "parent_action_task_ref": (
                f"task:{task.parent_action_task_id}"
                if task.parent_action_task_id is not None
                else None
            ),
            "quoted_task_text": task.display_text,
        },
    )


def _outcome_record(outcome: Outcome) -> TaskFollowUpInputRecordV1:
    return TaskFollowUpInputRecordV1(
        record_type="outcome",
        source_ref=f"outcome:{outcome.outcome_id}",
        payload={
            "outcome_id": str(outcome.outcome_id),
            "follow_up_task_ref": f"task:{outcome.follow_up_task_id}",
            "value": outcome.value,
            "recorded_at": _timestamp(outcome.recorded_at),
            "evidence_refs": list(outcome.evidence_refs),
        },
    )


def _evidence_record(ref: str, row: object) -> TaskFollowUpInputRecordV1:
    kind = ref.split(":", 1)[0]
    if kind == "manual_measurement":
        payload = {
            "evidence_kind": kind,
            "record_ref": ref,
            "recorded_at": _timestamp(getattr(row, "recorded_at")),
        }
    else:
        payload = {
            "evidence_kind": kind,
            "record_ref": ref,
            "observed_at": _timestamp(getattr(row, "observed_at")),
        }
    return TaskFollowUpInputRecordV1(
        record_type="evidence_ref",
        source_ref=ref,
        payload=payload,
    )


def _trigger_matches(trigger_kind: str, task: Task) -> bool:
    if trigger_kind == "task_completed":
        return task.status == "completed"
    if trigger_kind == "follow_up_outcome_recorded":
        return task.kind == "follow_up" and task.status == "completed"
    return trigger_kind == "manual_review"


def _scope_can_run(
    scope: CurrentTaskScope | None,
    *,
    actor: ActorContext,
    plant_id: uuid.UUID,
) -> bool:
    return (
        scope is not None
        and scope.farm_id == actor.farm_id
        and scope.plant_id == plant_id
        and scope.plant_status == "active"
        and scope.can_read
        and scope.can_mutate_tasks
    )


def _message_envelope(
    *,
    command: TaskFollowUpCommandV1,
    scope: CurrentAuthorizationScope,
    result: TaskFollowUpModelResultV1,
    created_at: datetime,
) -> MessageEnvelopeV1:
    assert result.proposed_task_kind is not None
    assert result.candidate_output is not None
    assert result.confidence is not None
    return _TaskFollowUpMessageEnvelopeV1(
        message_id=uuid.uuid4(),
        run_id=command.run_id,
        agent_id="task_follow_up",
        created_at=created_at,
        farm_id=scope.farm_id,
        plant_id=scope.plant_id,
        runtime_decision=RuntimeDecision.SPEAK,
        candidate_claim_type="task_request",
        confidence=result.confidence,
        source_refs=result.source_refs,
        candidate_output=result.candidate_output,
        authorization_scope=scope,
    )


def _runtime_event(
    *,
    command: TaskFollowUpCommandV1,
    request: TaskFollowUpProviderRequestV1,
    model_ref: str,
    outcome_kind: str,
    status: str,
    final_decision: str | None,
    reason_code: str,
    error_code: str | None,
    result: TaskFollowUpModelResultV1 | None,
    envelope: MessageEnvelopeV1 | None,
) -> TimelineEvent:
    return TimelineEvent(
        farm_id=command.actor_context.farm_id,
        plant_id=command.plant_id,
        actor_ref={
            "account_id": str(command.actor_context.account_id),
            "membership_id": str(command.actor_context.membership_id),
            "role_preset": command.actor_context.role_preset.value,
        },
        event_type="agent_runtime_decided",
        source_type="agent_runtime_attempt",
        source_id=command.run_id,
        source_refs={"input_refs": list(request.source_refs)},
        payload_summary={
            "agent_id": "task_follow_up",
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "candidate_decision": result.runtime_decision if result else None,
            "final_decision": final_decision,
            "outcome_status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "message_id": str(envelope.message_id) if envelope else None,
            "candidate_claim_type": "task_request" if envelope else None,
            "source_ref_count": len(request.source_refs),
        },
    )


def _failed_run(
    run_id: uuid.UUID,
    outcome: AgentRuntimeOutcomeV1,
    *,
    stage: str,
    proposed_kind: str | None = None,
    classification_ref: str | None = None,
) -> TaskFollowUpRunResultV1:
    return TaskFollowUpRunResultV1(
        run_id=run_id,
        runtime_outcome=outcome,
        route_status="failed",
        proposed_task_kind=proposed_kind,
        classification_ref=classification_ref,
        task_ref=None,
        failure_stage=stage,
    )


def _execution_result(execution: object, *, expected_model_ref: str) -> object:
    if isinstance(execution, ModelExecution):
        return execution.result if execution.model_ref == expected_model_ref else None
    return execution if isinstance(execution, Mapping) else None


def _context_denied(run_id: uuid.UUID, reason_code: str) -> AgentRuntimeOutcomeV1:
    safe_reason = (
        reason_code
        if reason_code in {"context_denied", "input_contract_violation"}
        else "input_contract_violation"
    )
    return AgentRuntimeOutcomeV1(
        run_id=run_id,
        outcome_kind="context_denied",
        status="blocked",
        final_decision=None,
        reason_code=safe_reason,
        error_code="AGENT_CONTEXT_DENIED",
        message_envelope=None,
        event_ref=None,
        model_ref=None,
        provider_call_status="not_attempted",
        audit_status="not_attempted",
    )


def _not_configured(run_id: uuid.UUID) -> AgentRuntimeOutcomeV1:
    return AgentRuntimeOutcomeV1(
        run_id=run_id,
        outcome_kind="runtime_not_configured",
        status="failed",
        final_decision=None,
        reason_code="runtime_not_configured",
        error_code="AGENT_RUNTIME_NOT_CONFIGURED",
        message_envelope=None,
        event_ref=None,
        model_ref=None,
        provider_call_status="not_attempted",
        audit_status="not_attempted",
    )


def _event_ref_valid(value: object) -> bool:
    if (
        not isinstance(value, Mapping)
        or set(value) != {
            "timeline_event_id",
            "timeline_ref",
            "event_type",
            "created_at",
        }
        or value.get("event_type") != "agent_runtime_decided"
    ):
        return False
    try:
        event_id = uuid.UUID(str(value["timeline_event_id"]))
    except (TypeError, ValueError):
        return False
    event_id_text = str(event_id)
    if event_id.version != 4 or value["timeline_event_id"] != event_id_text:
        return False
    if value.get("timeline_ref") != f"timeline.jsonl#{event_id_text}":
        return False
    created_at = value.get("created_at")
    if not isinstance(created_at, str):
        return False
    try:
        parsed_created_at = datetime.fromisoformat(created_at)
    except ValueError:
        return False
    return _is_utc(parsed_created_at) and parsed_created_at.isoformat() == created_at


def _envelope_ref(value: object) -> bool:
    if not isinstance(value, str) or ":" not in value:
        return False
    kind, identifier = value.split(":", 1)
    if kind not in _ENVELOPE_REF_KINDS:
        return False
    try:
        return str(uuid.UUID(identifier)) == identifier
    except (TypeError, ValueError, AttributeError):
        return False


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _is_utc(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timezone.utc.utcoffset(value)
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AssembledTaskFollowUpInputV1",
    "DatabaseTaskFollowUpInputAssembler",
    "TaskFollowUpClassificationService",
    "TaskFollowUpInputAssembler",
    "TaskFollowUpInputDenied",
    "TaskFollowUpModelExecutor",
    "TaskFollowUpRuntimeService",
    "task_follow_up_command_fingerprint",
]
