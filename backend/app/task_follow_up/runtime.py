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
    normalized_display_text,
    timestamp_text,
)
from .models import Outcome, Task, TaskFollowUpRuntimeDisposition
from .repository import (
    CurrentTaskScope,
    TaskFollowUpRepository,
    task_follow_up_run_lock_key,
)
from .runtime_contracts import (
    ORDINARY_TASK_KINDS,
    TaskFollowUpCommandV1,
    TaskFollowUpDispositionResultV1,
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
                follow_up = self._repository.follow_up_for_action(task.task_id)
                if follow_up is not None and follow_up.status == "open":
                    allowed.remove("follow_up")
            request = TaskFollowUpProviderRequestV1(
                trigger_kind=trigger_kind,
                allowed_task_kinds=tuple(allowed),
                records=tuple(records),
                source_refs=tuple(record.source_ref for record in records),
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


class _RuntimeAuditFailed(RuntimeError):
    def __init__(self, outcome: AgentRuntimeOutcomeV1) -> None:
        self.outcome = outcome
        super().__init__("Task Follow-Up runtime audit failed.")


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
        command_sha256 = task_follow_up_command_fingerprint(command)
        preflight = self._runtime_preflight(
            command,
            command_sha256=command_sha256,
        )
        if preflight is not None:
            return preflight
        stage = self._invoke_model(command)
        if stage.outcome is not None:
            return _result_for_runtime_outcome(command.run_id, stage.outcome)
        assert stage.request is not None
        assert stage.model_result is not None
        assert stage.model_ref is not None
        finalized = self._finalize_model_result(
            command,
            command_sha256=command_sha256,
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

    def _runtime_preflight(
        self,
        command: TaskFollowUpCommandV1,
        *,
        command_sha256: str,
    ) -> TaskFollowUpInvocationResultV1 | None:
        self._rollback_active()
        try:
            with self._session.begin():
                self._acquire_run_lock(command.run_id)
                runtime_disposition = self._repository.runtime_disposition_for_run(
                    command.run_id,
                    for_update=True,
                )
                dispatch_disposition = self._repository.dispatch_disposition_for_run(
                    command.run_id,
                    for_update=True,
                )
                if runtime_disposition is None and dispatch_disposition is None:
                    return None
                if runtime_disposition is None:
                    return _disposition_failed(command.run_id)
                return self._resolve_runtime_disposition(
                    command,
                    command_sha256=command_sha256,
                    runtime_disposition=runtime_disposition,
                    dispatch_disposition=dispatch_disposition,
                )
        except Exception:
            self._rollback_active()
            return _disposition_failed(command.run_id)

    def _finalize_model_result(
        self,
        command: TaskFollowUpCommandV1,
        *,
        command_sha256: str,
        request: TaskFollowUpProviderRequestV1,
        result: TaskFollowUpModelResultV1,
        model_ref: str,
    ) -> TaskFollowUpInvocationResultV1 | _CommittedHandoff:
        self._rollback_active()
        finalized: TaskFollowUpInvocationResultV1 | _CommittedHandoff
        try:
            with self._session.begin():
                self._acquire_run_lock(command.run_id)
                runtime_disposition = self._repository.runtime_disposition_for_run(
                    command.run_id,
                    for_update=True,
                )
                dispatch_disposition = self._repository.dispatch_disposition_for_run(
                    command.run_id,
                    for_update=True,
                )
                if runtime_disposition is not None:
                    finalized = self._resolve_runtime_disposition(
                        command,
                        command_sha256=command_sha256,
                        runtime_disposition=runtime_disposition,
                        dispatch_disposition=dispatch_disposition,
                    )
                elif dispatch_disposition is not None:
                    finalized = _disposition_failed(command.run_id)
                else:
                    scope = self._locked_current_scope(command)
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
                        self._require_audited(outcome)
                        self._session.add(
                            TaskFollowUpRuntimeDisposition(
                                run_id=command.run_id,
                                farm_id=command.actor_context.farm_id,
                                plant_id=command.plant_id,
                                command_sha256=command_sha256,
                                outcome="publication_denied",
                                message_id=None,
                                input_sha256=None,
                                denial_code="AGENT_PUBLICATION_BLOCKED",
                                model_ref=model_ref,
                                runtime_event_ref=dict(outcome.event_ref or {}),
                                recorded_at=_as_utc(self._clock()),
                            )
                        )
                        self._session.flush()
                        finalized = _failed_run(
                            command.run_id,
                            outcome,
                            stage="runtime",
                        )
                    elif result.runtime_decision == "silent":
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
                        self._require_audited(outcome)
                        finalized = TaskFollowUpRunResultV1(
                            run_id=command.run_id,
                            runtime_outcome=outcome,
                            route_status="silent",
                            proposed_task_kind=None,
                            classification_ref=None,
                            task_ref=None,
                            failure_stage=None,
                        )
                    else:
                        envelope = _message_envelope(
                            command=command,
                            scope=scope,
                            result=result,
                            created_at=_as_utc(self._clock()),
                        )
                        input_sha256 = canonical_fingerprint(envelope.as_value())
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
                        self._require_audited(outcome)
                        self._session.add(
                            TaskFollowUpRuntimeDisposition(
                                run_id=command.run_id,
                                farm_id=envelope.farm_id,
                                plant_id=envelope.plant_id,
                                command_sha256=command_sha256,
                                outcome="envelope_handed_off",
                                message_id=envelope.message_id,
                                input_sha256=input_sha256,
                                denial_code=None,
                                model_ref=model_ref,
                                runtime_event_ref=dict(outcome.event_ref or {}),
                                recorded_at=_as_utc(self._clock()),
                            )
                        )
                        self._session.flush()
                        finalized = _CommittedHandoff(outcome, result)
            return finalized
        except _RuntimeAuditFailed as failed:
            self._rollback_active()
            return _failed_run(command.run_id, failed.outcome, stage="runtime")
        except Exception:
            self._rollback_active()
            return _disposition_failed(command.run_id)

    def _resolve_runtime_disposition(
        self,
        command: TaskFollowUpCommandV1,
        *,
        command_sha256: str,
        runtime_disposition: TaskFollowUpRuntimeDisposition,
        dispatch_disposition: object | None,
    ) -> TaskFollowUpInvocationResultV1:
        row = runtime_disposition
        if row.command_sha256 != command_sha256:
            return _disposition_conflict(command.run_id)
        if (
            row.run_id != command.run_id
            or row.farm_id != command.actor_context.farm_id
            or row.plant_id != command.plant_id
            or _MODEL_REF_RE.fullmatch(row.model_ref) is None
            or not _event_ref_valid(row.runtime_event_ref)
        ):
            return _disposition_failed(command.run_id)
        if row.outcome == "publication_denied":
            if (
                dispatch_disposition is not None
                or self._repository.task_for_create_request(command.run_id)
                is not None
                or row.message_id is not None
                or row.input_sha256 is not None
                or row.denial_code != "AGENT_PUBLICATION_BLOCKED"
            ):
                return _disposition_failed(command.run_id)
            outcome = AgentRuntimeOutcomeV1(
                run_id=command.run_id,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                message_envelope=None,
                event_ref=dict(row.runtime_event_ref),
                model_ref=row.model_ref,
                provider_call_status="completed",
                audit_status="appended",
            )
            return _failed_run(command.run_id, outcome, stage="runtime")
        if (
            row.outcome != "envelope_handed_off"
            or not _uuid4(row.message_id)
            or not isinstance(row.input_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", row.input_sha256) is None
            or row.denial_code is not None
        ):
            return _disposition_failed(command.run_id)
        return self._resolve_handed_off(
            command,
            row=row,
            dispatch_disposition=dispatch_disposition,
        )

    def _resolve_handed_off(
        self,
        command: TaskFollowUpCommandV1,
        *,
        row: TaskFollowUpRuntimeDisposition,
        dispatch_disposition: object | None,
    ) -> TaskFollowUpDispositionResultV1:
        assert row.message_id is not None
        message_disposition = self._repository.dispatch_disposition_for_message(
            row.message_id,
            for_update=True,
        )
        if (
            dispatch_disposition is not None
            and message_disposition is not None
            and getattr(dispatch_disposition, "classification_message_id", None)
            != message_disposition.classification_message_id
        ):
            return _disposition_failed(command.run_id)
        dispatch = dispatch_disposition or message_disposition
        classification = self._repository.safety_classification(
            row.message_id,
            for_update=True,
        )
        if classification is None:
            if dispatch is not None:
                return _disposition_failed(command.run_id)
            return _disposition_incomplete(command.run_id, None)
        if (
            classification.message_id != row.message_id
            or classification.farm_id != row.farm_id
            or classification.plant_id != row.plant_id
            or classification.origin_agent_id != "task_follow_up"
            or classification.input_sha256 != row.input_sha256
        ):
            return _disposition_failed(command.run_id)
        classification_ref = f"safety_classification:{classification.message_id}"
        taskable = (
            classification.classification == "safe_task_request"
            and classification.safe_task_kind in ORDINARY_TASK_KINDS
        )
        if dispatch is None:
            if taskable:
                return _disposition_incomplete(command.run_id, classification_ref)
            return TaskFollowUpDispositionResultV1(
                run_id=command.run_id,
                result_status="not_taskable",
                result_code="TASK_FOLLOW_UP_ALREADY_NOT_TASKABLE",
                classification_ref=classification_ref,
                task_ref=None,
            )
        if (
            getattr(dispatch, "classification_message_id", None) != row.message_id
            or getattr(dispatch, "run_id", None) != row.run_id
            or getattr(dispatch, "farm_id", None) != row.farm_id
            or getattr(dispatch, "plant_id", None) != row.plant_id
            or getattr(dispatch, "input_sha256", None) != row.input_sha256
        ):
            return _disposition_failed(command.run_id)
        if dispatch.outcome == "denied":
            if (
                getattr(dispatch, "expected_task_create_fingerprint", None)
                is not None
                or dispatch.denial_code not in {
                "TASK_SCOPE_NOT_FOUND",
                "TASK_COMMAND_FORBIDDEN",
                "TASK_PLANT_NOT_ACTIVE",
                }
            ):
                return _disposition_failed(command.run_id)
            if (
                self._repository.task_for_create_request(row.run_id) is not None
                or self._repository.task_for_classification(
                    row.message_id,
                    for_update=True,
                )
                is not None
            ):
                return _disposition_failed(command.run_id)
            return TaskFollowUpDispositionResultV1(
                run_id=command.run_id,
                result_status="denied",
                result_code="TASK_FOLLOW_UP_DISPATCH_DENIED",
                classification_ref=classification_ref,
                task_ref=None,
            )
        if dispatch.outcome != "consumed" or dispatch.denial_code is not None:
            return _disposition_failed(command.run_id)
        scope = self._locked_current_scope(command)
        if scope is None:
            return TaskFollowUpDispositionResultV1(
                run_id=command.run_id,
                result_status="blocked",
                result_code="TASK_FOLLOW_UP_REPLAY_BLOCKED",
                classification_ref=None,
                task_ref=None,
            )
        task = self._repository.task_for_classification(
            row.message_id,
            for_update=True,
        )
        if (
            task is None
            or not taskable
            or not self._exact_consumed_task(
                command,
                task,
                row=row,
                classification=classification,
                dispatch=dispatch,
            )
        ):
            return _disposition_failed(command.run_id)
        return TaskFollowUpDispositionResultV1(
            run_id=command.run_id,
            result_status="duplicate",
            result_code="TASK_FOLLOW_UP_ALREADY_CONSUMED",
            classification_ref=classification_ref,
            task_ref=f"task:{task.task_id}",
        )

    def _exact_consumed_task(
        self,
        command: TaskFollowUpCommandV1,
        task: Task,
        *,
        row: TaskFollowUpRuntimeDisposition,
        classification: object,
        dispatch: object,
    ) -> bool:
        task_kind = getattr(classification, "safe_task_kind", None)
        reason_code = {
            "check": "safe_check_request",
            "measurement": "safe_measurement_request",
            "follow_up": "safe_follow_up_request",
        }.get(task_kind)
        if (
            reason_code is None
            or getattr(classification, "classifier_version", None)
            != "safety_gate_v1"
            or getattr(classification, "classification", None)
            != "safe_task_request"
            or getattr(classification, "reason_code", None) != reason_code
            or getattr(classification, "physical_action_kind", None) is not None
            or getattr(classification, "provider_status", None) != "completed"
            or getattr(classification, "input_sha256", None) != row.input_sha256
        ):
            return False

        available_source_refs = self._expected_request_source_refs(command)
        refs = task.source_refs
        expected_prefix = [
            f"message_envelope:{row.message_id}",
            f"safety_classification:{row.message_id}",
        ]
        if (
            available_source_refs is None
            or row.run_id != command.run_id
            or row.farm_id != command.actor_context.farm_id
            or row.plant_id != command.plant_id
            or task.farm_id != row.farm_id
            or task.plant_id != row.plant_id
            or task.kind != task_kind
            or task.source_type != "safe_task_request"
            or task.classification_message_id != row.message_id
            or task.create_request_id != row.run_id
            or task.created_by_account_id != command.actor_context.account_id
            or task.created_by_membership_id != command.actor_context.membership_id
            or task.created_by_role_preset
            != command.actor_context.role_preset.value
            or task.created_by_agent_id != "task_follow_up"
            or not isinstance(refs, list)
            or not 3 <= len(refs) <= 6
            or refs[:2] != expected_prefix
            or len(refs) != len(set(refs))
        ):
            return False
        source_refs = tuple(refs[2:])
        if (
            not 1 <= len(source_refs) <= 4
            or source_refs
            != tuple(ref for ref in available_source_refs if ref in source_refs)
            or any(not _envelope_ref(ref) for ref in source_refs)
        ):
            return False
        if any(
            not self._repository.lock_task_follow_up_source_ref(
                ref,
                farm_id=row.farm_id,
                plant_id=row.plant_id,
            )
            for ref in source_refs
        ):
            return False
        try:
            expected_display_text = normalized_display_text(task.display_text)
        except Exception:
            return False
        if (
            task.display_text != expected_display_text
            or not 1 <= len(expected_display_text) <= 1000
        ):
            return False
        expected_refs = [*expected_prefix, *source_refs]
        expected_fingerprint = canonical_fingerprint(
            {
                "schema_version": 1,
                "source_branch": "classified_message",
                "request_id": str(command.run_id),
                "message_id": str(getattr(classification, "message_id", "")),
                "task_kind": task_kind,
                "display_text": expected_display_text,
                "source_refs": expected_refs,
            }
        )
        commitment = getattr(
            dispatch,
            "expected_task_create_fingerprint",
            None,
        )
        return (
            isinstance(commitment, str)
            and re.fullmatch(r"[0-9a-f]{64}", commitment) is not None
            and commitment == task.create_request_fingerprint
            and commitment == expected_fingerprint
        )

    def _expected_request_source_refs(
        self,
        command: TaskFollowUpCommandV1,
    ) -> tuple[str, ...] | None:
        """Rebuild the writer's canonical source universe without Task fields."""

        try:
            assembled = DatabaseTaskFollowUpInputAssembler(
                self._session,
                repository=self._repository,
            ).assemble(
                command.actor_context,
                plant_id=command.plant_id,
                trigger_kind=command.trigger_kind,
                trigger_task_id=command.trigger_task_id,
                selected_at=_as_utc(self._clock()),
            )
        except Exception:
            return None
        refs = assembled.request.source_refs
        if not 1 <= len(refs) <= 4 or any(not _envelope_ref(ref) for ref in refs):
            return None
        return refs

    def _acquire_run_lock(self, run_id: uuid.UUID) -> None:
        self._repository.acquire_task_follow_up_run_lock(
            run_id,
            lock_key=self._run_lock_key(run_id),
        )

    @staticmethod
    def _require_audited(outcome: AgentRuntimeOutcomeV1) -> None:
        if outcome.outcome_kind == "audit_failed":
            raise _RuntimeAuditFailed(outcome)

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


def _disposition_conflict(run_id: uuid.UUID) -> TaskFollowUpDispositionResultV1:
    return TaskFollowUpDispositionResultV1(
        run_id=run_id,
        result_status="conflict",
        result_code="TASK_FOLLOW_UP_RUN_CONFLICT",
        classification_ref=None,
        task_ref=None,
    )


def _disposition_failed(run_id: uuid.UUID) -> TaskFollowUpDispositionResultV1:
    return TaskFollowUpDispositionResultV1(
        run_id=run_id,
        result_status="failed",
        result_code="TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED",
        classification_ref=None,
        task_ref=None,
    )


def _disposition_incomplete(
    run_id: uuid.UUID,
    classification_ref: str | None,
) -> TaskFollowUpDispositionResultV1:
    return TaskFollowUpDispositionResultV1(
        run_id=run_id,
        result_status="incomplete",
        result_code="TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
        classification_ref=classification_ref,
        task_ref=None,
    )


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
