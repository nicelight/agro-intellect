"""Transactional FT-012 ordinary-task, approval, completion, and Outcome loop."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import re
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..agent_runtime.contracts import MessageEnvelopeV1
from ..safety_gate.models import SafetyActionDecision, SafetyClassification
from ..timeline.writer import TimelineAppendError, TimelineEvent, TimelineJsonlAppender
from .contracts import (
    ApprovalDecisionCommandV1,
    ApprovalDecisionResultV1,
    ApprovalStatus,
    ClassifiedMessageTaskCommandV1,
    CompleteTaskCommandV1,
    CompleteTaskResultV1,
    OrdinaryTaskCreateResultV1,
    OutcomeValue,
    RecordOutcomeCommandV1,
    RecordOutcomeResultV1,
    TaskFollowUpError,
    TaskFollowUpErrorCode,
    TaskKind,
    canonical_fingerprint,
    normalized_display_text,
    ordered_unique,
    timestamp_text,
)
from .models import (
    Approval,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    Task,
    TaskFollowUpRuntimeDisposition,
)
from .repository import (
    CurrentTaskScope,
    TaskFollowUpRepository,
    task_follow_up_run_lock_key,
)


_ACTION_TEXT = {
    "ph_adjustment": "Выполнить одобренную ручную корректировку pH и отметить завершение.",
    "ec_adjustment": "Выполнить одобренную ручную корректировку EC и отметить завершение.",
    "solution_change": "Выполнить одобренную ручную замену питательного раствора и отметить завершение.",
}
_FOLLOW_UP_TEXT = (
    "Зафиксировать результат одобренного ручного действия и приложить доступные доказательства."
)
_ORDINARY_REQUEST_CONSTRAINTS = {
    "uq_ordinary_task_dispatch_dispositions_run",
    "uq_tasks_create_request",
}


class TaskFollowUpService:
    def __init__(
        self,
        session: Session,
        *,
        repository: TaskFollowUpRepository | None = None,
        timeline_appender=None,
        clock=None,
        run_lock_key: Callable[[uuid.UUID], int] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or TaskFollowUpRepository(session)
        self._timeline = timeline_appender or TimelineJsonlAppender()
        self._clock = clock or _utc_now
        self._run_lock_key = run_lock_key or task_follow_up_run_lock_key

    def create_ordinary_task(
        self, command: ClassifiedMessageTaskCommandV1
    ) -> OrdinaryTaskCreateResultV1:
        if not isinstance(command, ClassifiedMessageTaskCommandV1):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
        envelope = command.message_envelope
        now = _utc(self._clock())
        refs = ordered_unique(
            (
                f"message_envelope:{envelope.message_id}",
                f"safety_classification:{envelope.message_id}",
                *envelope.source_refs,
            )
        )
        display_text = normalized_display_text(envelope.candidate_output)
        input_sha256 = canonical_fingerprint(envelope.as_value())
        fingerprint = canonical_fingerprint(
            {
                "schema_version": 1,
                "source_branch": "classified_message",
                "request_id": str(envelope.run_id),
                "message_id": str(envelope.message_id),
                "task_kind": command.task_kind.value,
                "display_text": display_text,
                "source_refs": list(refs),
            }
        )
        denial_code: TaskFollowUpErrorCode | None = None
        try:
            with self._session.begin():
                runtime_disposition = None
                if envelope.agent_id == "task_follow_up":
                    self._repository.acquire_task_follow_up_run_lock(
                        envelope.run_id,
                        lock_key=self._run_lock_key(envelope.run_id),
                    )
                    runtime_disposition = (
                        self._repository.runtime_disposition_for_run(
                            envelope.run_id,
                            for_update=True,
                        )
                    )
                    message_disposition = (
                        self._repository.dispatch_disposition_for_message(
                            envelope.message_id,
                            for_update=True,
                        )
                    )
                    run_disposition = self._repository.dispatch_disposition_for_run(
                        envelope.run_id,
                        for_update=True,
                    )
                else:
                    message_disposition = None
                    run_disposition = None
                classification = self._repository.safety_classification(
                    envelope.message_id, for_update=True
                )
                self._validate_classified_source(command, classification)
                assert classification is not None
                if runtime_disposition is not None or envelope.agent_id == "task_follow_up":
                    self._validate_runtime_handoff(
                        envelope,
                        runtime_disposition,
                        input_sha256=input_sha256,
                    )
                if envelope.agent_id != "task_follow_up":
                    message_disposition = (
                        self._repository.dispatch_disposition_for_message(
                            envelope.message_id,
                            for_update=True,
                        )
                    )
                    run_disposition = self._repository.dispatch_disposition_for_run(
                        envelope.run_id,
                        for_update=True,
                    )
                if message_disposition is not None or run_disposition is not None:
                    return self._resolve_dispatch_disposition(
                        command,
                        message_disposition=message_disposition,
                        run_disposition=run_disposition,
                        refs=refs,
                        display_text=display_text,
                        input_sha256=input_sha256,
                        fingerprint=fingerprint,
                        now=now,
                    )

                if classification.input_sha256 != input_sha256:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)

                scope = self._repository.lock_current_scope(
                    command.actor_context, plant_id=envelope.plant_id, now=now
                )
                denial_code = self._scope_denial_code(scope)
                disposition = OrdinaryTaskDispatchDisposition(
                    classification_message_id=envelope.message_id,
                    run_id=envelope.run_id,
                    farm_id=envelope.farm_id,
                    plant_id=envelope.plant_id,
                    input_sha256=input_sha256,
                    outcome="denied" if denial_code is not None else "consumed",
                    expected_task_create_fingerprint=(
                        None if denial_code is not None else fingerprint
                    ),
                    denial_code=denial_code.value if denial_code is not None else None,
                    recorded_at=now,
                )
                self._session.add(disposition)

                if denial_code is None:
                    assert scope is not None
                    if scope.farm_id != envelope.farm_id:
                        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
                    for ref in envelope.source_refs:
                        resolver = (
                            self._repository.lock_task_follow_up_source_ref
                            if envelope.agent_id == "task_follow_up"
                            else self._repository.lock_authoritative_ref
                        )
                        if not resolver(
                            ref,
                            farm_id=envelope.farm_id,
                            plant_id=envelope.plant_id,
                        ):
                            raise TaskFollowUpError(
                                TaskFollowUpErrorCode.TASK_SOURCE_INVALID
                            )
                    if (
                        self._repository.task_for_classification(
                            envelope.message_id, for_update=True
                        )
                        is not None
                        or self._repository.task_for_create_request(envelope.run_id)
                        is not None
                    ):
                        raise TaskFollowUpError(
                            TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
                        )
                    task = Task(
                        task_id=uuid.uuid4(),
                        farm_id=envelope.farm_id,
                        plant_id=envelope.plant_id,
                        kind=command.task_kind.value,
                        status="open",
                        display_text=display_text,
                        source_type="safe_task_request",
                        source_refs=list(refs),
                        classification_message_id=envelope.message_id,
                        approval_id=None,
                        parent_action_task_id=None,
                        due_at=None,
                        created_by_account_id=command.actor_context.account_id,
                        created_by_membership_id=command.actor_context.membership_id,
                        created_by_role_preset=scope.role_preset,
                        created_by_agent_id=envelope.agent_id,
                        created_at=now,
                        create_request_id=envelope.run_id,
                        create_request_fingerprint=fingerprint,
                        created_event_ref={},
                    )
                    task.created_event_ref = self._append_task_created(
                        task, command.actor_context
                    )
                    self._session.add(task)
                self._session.flush()
            if denial_code is not None:
                raise TaskFollowUpError(denial_code)
            return OrdinaryTaskCreateResultV1("created", task)
        except TaskFollowUpError:
            self._rollback()
            raise
        except TimelineAppendError:
            self._rollback()
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_AUDIT_FAILED) from None
        except IntegrityError as error:
            self._rollback()
            return self._recover_ordinary_request_loss(
                command,
                error=error,
                refs=refs,
                display_text=display_text,
                input_sha256=input_sha256,
                fingerprint=fingerprint,
                now=now,
            )
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def materialize_pending_approval(
        self, safety_decision_id: uuid.UUID
    ) -> Approval:
        if not isinstance(safety_decision_id, uuid.UUID):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
        try:
            with self._session.begin():
                decision = self._repository.safety_decision(
                    safety_decision_id, for_update=True
                )
                if decision is None:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
                approval, _created = self._materialize_locked(decision, require_active=True)
            return approval
        except TaskFollowUpError:
            self._rollback()
            raise
        except (IntegrityError, SQLAlchemyError):
            self._rollback()
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED) from None

    def decide_approval(
        self, command: ApprovalDecisionCommandV1
    ) -> ApprovalDecisionResultV1:
        if not isinstance(command, ApprovalDecisionCommandV1):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
        now = _utc(self._clock())
        fingerprint = canonical_fingerprint(
            {
                "schema_version": 1,
                "request_id": str(command.request_id),
                "safety_decision_id": str(command.safety_decision_id),
                "expected_version": command.expected_version,
                "decision": command.decision.value,
            }
        )
        try:
            with self._session.begin():
                scope = self._require_scope(
                    command.actor_context, command.plant_id, now=now, mutation=True
                )
                if not scope.can_approve_actions:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN)
                decision = self._repository.safety_decision(
                    command.safety_decision_id, for_update=True
                )
                if decision is None or decision.plant_id != command.plant_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
                approval, _created = self._materialize_locked(decision, require_active=False)
                approval = self._repository.approval_for_decision(
                    decision.decision_id, for_update=True
                ) or approval
                if approval.status != "pending":
                    if (
                        approval.status == command.decision.value
                        and approval.decision_request_id == command.request_id
                        and approval.decision_request_fingerprint == fingerprint
                    ):
                        action = self._repository.task_for_approval(
                            approval.approval_id, for_update=True
                        )
                        return ApprovalDecisionResultV1("duplicate", approval, action)
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                request_owner = self._repository.approval_for_request(command.request_id)
                if request_owner is not None and request_owner.approval_id != approval.approval_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                if command.expected_version != approval.record_version:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                self._validate_current_approval(decision, approval, now=now)

                action = None
                approval.status = command.decision.value
                approval.record_version = 2
                approval.decided_at = now
                approval.decision_actor_account_id = command.actor_context.account_id
                approval.decision_actor_membership_id = command.actor_context.membership_id
                approval.decision_actor_role_preset = scope.role_preset
                approval.decision_permission_source = scope.permission_source
                approval.decision_grant_id = scope.grant_id
                approval.decision_request_id = command.request_id
                approval.decision_request_fingerprint = fingerprint
                if command.decision is ApprovalStatus.APPROVED:
                    action = self._new_action_task(approval, command, scope=scope, now=now)
                    approval.decision_event_ref = self._append_approval_decided(
                        approval, command.actor_context, action_task_id=action.task_id
                    )
                    action.created_event_ref = self._append_task_created(
                        action, command.actor_context
                    )
                    self._session.add(action)
                else:
                    approval.decision_event_ref = self._append_approval_decided(
                        approval, command.actor_context, action_task_id=None
                    )
                self._session.flush()
            return ApprovalDecisionResultV1("created", approval, action)
        except TaskFollowUpError:
            self._rollback()
            raise
        except TimelineAppendError:
            self._rollback()
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_AUDIT_FAILED) from None
        except IntegrityError as error:
            self._rollback()
            return self._recover_approval_request_loss(
                command, error=error, fingerprint=fingerprint
            )
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def complete_task(self, command: CompleteTaskCommandV1) -> CompleteTaskResultV1:
        if not isinstance(command, CompleteTaskCommandV1):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
        now = _utc(self._clock())
        fingerprint = canonical_fingerprint(
            {
                "schema_version": 1,
                "request_id": str(command.request_id),
                "task_id": str(command.task_id),
            }
        )
        try:
            with self._session.begin():
                scope = self._require_scope(
                    command.actor_context, command.plant_id, now=now, mutation=True
                )
                task = self._repository.task(command.task_id, for_update=True)
                if task is None or task.plant_id != command.plant_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
                if task.status == "completed":
                    if (
                        task.completion_request_id == command.request_id
                        and task.completion_request_fingerprint == fingerprint
                    ):
                        follow_up = self._repository.follow_up_for_action(
                            task.task_id, for_update=True
                        )
                        return CompleteTaskResultV1("duplicate", task, follow_up)
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                request_owner = self._repository.task_for_completion_request(command.request_id)
                if request_owner is not None and request_owner.task_id != task.task_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                if task.kind == "follow_up":
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_INVALID_TRANSITION)
                task.status = "completed"
                task.completed_at = now
                task.completed_by_account_id = command.actor_context.account_id
                task.completed_by_membership_id = command.actor_context.membership_id
                task.completed_by_role_preset = scope.role_preset
                task.completion_request_id = command.request_id
                task.completion_request_fingerprint = fingerprint
                task.completed_event_ref = self._append_task_completed(
                    task, command.actor_context, completion_kind=(
                        "action" if task.kind == "action" else "ordinary"
                    )
                )
                follow_up = None
                if task.kind == "action":
                    follow_up = Task(
                        task_id=uuid.uuid4(), farm_id=task.farm_id,
                        plant_id=task.plant_id, kind="follow_up", status="open",
                        display_text=_FOLLOW_UP_TEXT,
                        source_type="automatic_follow_up",
                        source_refs=[f"task:{task.task_id}"],
                        classification_message_id=None, approval_id=None,
                        parent_action_task_id=task.task_id,
                        due_at=now + timedelta(hours=48),
                        created_by_account_id=command.actor_context.account_id,
                        created_by_membership_id=command.actor_context.membership_id,
                        created_by_role_preset=scope.role_preset,
                        created_by_agent_id=None, created_at=now,
                        create_request_id=None, create_request_fingerprint=None,
                        created_event_ref={},
                    )
                    follow_up.created_event_ref = self._append_task_created(
                        follow_up, command.actor_context
                    )
                    self._session.add(follow_up)
                self._session.flush()
            return CompleteTaskResultV1("created", task, follow_up)
        except TaskFollowUpError:
            self._rollback()
            raise
        except TimelineAppendError:
            self._rollback()
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_AUDIT_FAILED) from None
        except IntegrityError as error:
            self._rollback()
            return self._recover_completion_request_loss(
                command, error=error, fingerprint=fingerprint
            )
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def record_outcome(
        self, command: RecordOutcomeCommandV1
    ) -> RecordOutcomeResultV1:
        if not isinstance(command, RecordOutcomeCommandV1):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
        if command.value is not OutcomeValue.NO_DATA and not command.evidence_refs:
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_EVIDENCE_REQUIRED)
        now = _utc(self._clock())
        fingerprint = canonical_fingerprint(
            {
                "schema_version": 1,
                "request_id": str(command.request_id),
                "follow_up_task_id": str(command.follow_up_task_id),
                "value": command.value.value,
                "evidence_refs": list(command.evidence_refs),
            }
        )
        try:
            with self._session.begin():
                scope = self._require_scope(
                    command.actor_context, command.plant_id, now=now, mutation=True
                )
                task = self._repository.task(command.follow_up_task_id, for_update=True)
                if task is None or task.plant_id != command.plant_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
                if task.kind != "follow_up":
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_INVALID_TRANSITION)
                if task.parent_action_task_id is not None:
                    parent = self._repository.task(task.parent_action_task_id, for_update=True)
                    if parent is None or parent.kind != "action" or parent.status != "completed":
                        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
                existing = self._repository.outcome_for_follow_up(
                    task.task_id, for_update=True
                )
                if existing is not None or task.status == "completed":
                    if (
                        existing is not None
                        and existing.request_id == command.request_id
                        and existing.request_fingerprint == fingerprint
                        and existing.value == command.value.value
                        and existing.evidence_refs == list(command.evidence_refs)
                    ):
                        return RecordOutcomeResultV1("duplicate", task, existing)
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                request_owner = self._repository.outcome_for_request(command.request_id)
                if request_owner is not None and request_owner.follow_up_task_id != task.task_id:
                    raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
                for ref in command.evidence_refs:
                    if not self._repository.lock_authoritative_ref(
                        ref, farm_id=task.farm_id, plant_id=task.plant_id
                    ):
                        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_EVIDENCE_REQUIRED)
                outcome = Outcome(
                    outcome_id=uuid.uuid4(), follow_up_task_id=task.task_id,
                    farm_id=task.farm_id, plant_id=task.plant_id,
                    value=command.value.value,
                    evidence_refs=list(command.evidence_refs), recorded_at=now,
                    recorded_by_account_id=command.actor_context.account_id,
                    recorded_by_membership_id=command.actor_context.membership_id,
                    recorded_by_role_preset=scope.role_preset,
                    request_id=command.request_id,
                    request_fingerprint=fingerprint,
                    outcome_event_ref={}, task_completed_event_ref={},
                )
                task.status = "completed"
                task.completed_at = now
                task.completed_by_account_id = command.actor_context.account_id
                task.completed_by_membership_id = command.actor_context.membership_id
                task.completed_by_role_preset = scope.role_preset
                task.completion_request_id = command.request_id
                task.completion_request_fingerprint = fingerprint
                task.completed_event_ref = self._append_task_completed(
                    task, command.actor_context, completion_kind="outcome"
                )
                outcome.task_completed_event_ref = task.completed_event_ref
                outcome.outcome_event_ref = self._append_outcome(outcome, command.actor_context)
                self._session.add(outcome)
                self._session.flush()
            return RecordOutcomeResultV1("created", task, outcome)
        except TaskFollowUpError:
            self._rollback()
            raise
        except TimelineAppendError:
            self._rollback()
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_AUDIT_FAILED) from None
        except IntegrityError as error:
            self._rollback()
            return self._recover_outcome_request_loss(
                command, error=error, fingerprint=fingerprint
            )
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def list_tasks(
        self, actor, *, plant_id: uuid.UUID, status: str | None,
        kind: str | None, limit: int,
    ) -> list[tuple[Task, Outcome | None]]:
        now = _utc(self._clock())
        with self._session.begin():
            scope = self._require_scope(actor, plant_id, now=now, mutation=False)
            rows = self._repository.list_tasks(
                farm_id=scope.farm_id, plant_id=plant_id,
                status=status, kind=kind, limit=limit,
            )
            return [
                (row, self._repository.outcome_for_follow_up(row.task_id))
                for row in rows
            ]

    def list_approvals(
        self, actor, *, plant_id: uuid.UUID, status: str | None, limit: int,
    ) -> list[Approval]:
        now = _utc(self._clock())
        with self._session.begin():
            scope = self._require_scope(actor, plant_id, now=now, mutation=False)
            return self._repository.list_approvals(
                farm_id=scope.farm_id, plant_id=plant_id, status=status, limit=limit
            )

    def _require_scope(self, actor, plant_id, *, now, mutation) -> CurrentTaskScope:
        scope = self._repository.lock_current_scope(actor, plant_id=plant_id, now=now)
        if scope is None or not scope.can_read:
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
        if scope.plant_status != "active":
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE)
        if mutation and not scope.can_mutate_tasks:
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN)
        return scope

    def _validate_classified_source(
        self,
        command: ClassifiedMessageTaskCommandV1,
        row: SafetyClassification | None,
    ) -> None:
        envelope = command.message_envelope
        classification = command.classification
        if (
            row is None
            or row.message_id != envelope.message_id
            or row.farm_id != envelope.farm_id
            or row.plant_id != envelope.plant_id
            or row.origin_agent_id != envelope.agent_id
            or row.origin_agent_id == "companion"
            or row.classification != "safe_task_request"
            or row.safe_task_kind != command.task_kind.value
            or classification.message_id != envelope.message_id
            or classification.classification != row.classification
            or classification.safe_task_kind != row.safe_task_kind
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)

    @staticmethod
    def _validate_runtime_handoff(
        envelope: MessageEnvelopeV1,
        disposition: TaskFollowUpRuntimeDisposition | None,
        *,
        input_sha256: str,
    ) -> None:
        if (
            disposition is None
            or disposition.run_id != envelope.run_id
            or disposition.farm_id != envelope.farm_id
            or disposition.plant_id != envelope.plant_id
            or disposition.outcome != "envelope_handed_off"
            or disposition.message_id != envelope.message_id
            or disposition.input_sha256 != input_sha256
            or disposition.denial_code is not None
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)

    @staticmethod
    def _scope_denial_code(
        scope: CurrentTaskScope | None,
    ) -> TaskFollowUpErrorCode | None:
        if scope is None or not scope.can_read:
            return TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND
        if scope.plant_status != "active":
            return TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE
        if not scope.can_mutate_tasks:
            return TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN
        return None

    def _resolve_dispatch_disposition(
        self,
        command: ClassifiedMessageTaskCommandV1,
        *,
        message_disposition: OrdinaryTaskDispatchDisposition | None,
        run_disposition: OrdinaryTaskDispatchDisposition | None,
        refs: tuple[str, ...],
        display_text: str,
        input_sha256: str,
        fingerprint: str,
        now: datetime,
        repository: TaskFollowUpRepository | None = None,
    ) -> OrdinaryTaskCreateResultV1:
        repository = repository or self._repository
        if (
            message_disposition is not None
            and run_disposition is not None
            and message_disposition.classification_message_id
            != run_disposition.classification_message_id
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
        disposition = message_disposition or run_disposition
        assert disposition is not None
        envelope = command.message_envelope
        if (
            disposition.classification_message_id != envelope.message_id
            or disposition.run_id != envelope.run_id
            or disposition.farm_id != envelope.farm_id
            or disposition.plant_id != envelope.plant_id
            or disposition.input_sha256 != input_sha256
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)

        if disposition.outcome == "denied":
            if disposition.expected_task_create_fingerprint is not None:
                raise TaskFollowUpError(
                    TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                )
            task = repository.task_for_classification(
                envelope.message_id, for_update=True
            )
            if task is not None:
                raise TaskFollowUpError(
                    TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                )
            try:
                code = TaskFollowUpErrorCode(disposition.denial_code)
            except ValueError:
                raise TaskFollowUpError(
                    TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                ) from None
            if code not in {
                TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND,
                TaskFollowUpErrorCode.TASK_COMMAND_FORBIDDEN,
                TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE,
            }:
                raise TaskFollowUpError(
                    TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                )
            raise TaskFollowUpError(code)
        if (
            disposition.outcome != "consumed"
            or disposition.denial_code is not None
            or not isinstance(
                disposition.expected_task_create_fingerprint,
                str,
            )
            or re.fullmatch(
                r"[0-9a-f]{64}",
                disposition.expected_task_create_fingerprint,
            )
            is None
            or disposition.expected_task_create_fingerprint != fingerprint
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)

        scope = self._require_scope(
            command.actor_context, envelope.plant_id, now=now, mutation=True
        )
        task = repository.task_for_classification(
            envelope.message_id, for_update=True
        )
        if scope.farm_id != envelope.farm_id or task is None:
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED)
        self._require_identical_ordinary(
            task,
            command,
            refs=refs,
            display_text=display_text,
            fingerprint=fingerprint,
        )
        return OrdinaryTaskCreateResultV1("duplicate", task)

    def _recover_ordinary_request_loss(
        self,
        command: ClassifiedMessageTaskCommandV1,
        *,
        error: IntegrityError,
        refs: tuple[str, ...],
        display_text: str,
        input_sha256: str,
        fingerprint: str,
        now: datetime,
    ) -> OrdinaryTaskCreateResultV1:
        if _constraint_name(error) not in _ORDINARY_REQUEST_CONSTRAINTS:
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None
        clean_repository = TaskFollowUpRepository(self._session)
        try:
            with self._session.begin():
                if command.message_envelope.agent_id == "task_follow_up":
                    clean_repository.acquire_task_follow_up_run_lock(
                        command.message_envelope.run_id,
                        lock_key=self._run_lock_key(
                            command.message_envelope.run_id
                        ),
                    )
                    runtime_disposition = clean_repository.runtime_disposition_for_run(
                        command.message_envelope.run_id,
                        for_update=True,
                    )
                    message_disposition = (
                        clean_repository.dispatch_disposition_for_message(
                            command.message_envelope.message_id,
                            for_update=True,
                        )
                    )
                    run_disposition = clean_repository.dispatch_disposition_for_run(
                        command.message_envelope.run_id,
                        for_update=True,
                    )
                    self._validate_runtime_handoff(
                        command.message_envelope,
                        runtime_disposition,
                        input_sha256=input_sha256,
                    )
                classification = clean_repository.safety_classification(
                    command.message_envelope.message_id, for_update=True
                )
                self._validate_classified_source(command, classification)
                if command.message_envelope.agent_id != "task_follow_up":
                    message_disposition = (
                        clean_repository.dispatch_disposition_for_message(
                            command.message_envelope.message_id,
                            for_update=True,
                        )
                    )
                    run_disposition = clean_repository.dispatch_disposition_for_run(
                        command.message_envelope.run_id,
                        for_update=True,
                    )
                if message_disposition is None and run_disposition is None:
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                    )
                return self._resolve_dispatch_disposition(
                    command,
                    message_disposition=message_disposition,
                    run_disposition=run_disposition,
                    refs=refs,
                    display_text=display_text,
                    input_sha256=input_sha256,
                    fingerprint=fingerprint,
                    now=now,
                    repository=clean_repository,
                )
        except TaskFollowUpError:
            self._rollback()
            raise
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def _recover_approval_request_loss(
        self,
        command: ApprovalDecisionCommandV1,
        *,
        error: IntegrityError,
        fingerprint: str,
    ) -> ApprovalDecisionResultV1:
        if _constraint_name(error) != "uq_approvals_decision_request":
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None
        clean_repository = TaskFollowUpRepository(self._session)
        try:
            with self._session.begin():
                owner = clean_repository.approval_for_request(command.request_id)
                if owner is None:
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                    )
                if (
                    owner.safety_decision_id != command.safety_decision_id
                    or owner.status != command.decision.value
                    or owner.decision_request_fingerprint != fingerprint
                ):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
                    )
                action = clean_repository.task_for_approval(
                    owner.approval_id, for_update=True
                )
                if (owner.status == "approved") != (action is not None):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                    )
                return ApprovalDecisionResultV1("duplicate", owner, action)
        except TaskFollowUpError:
            self._rollback()
            raise
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def _recover_completion_request_loss(
        self,
        command: CompleteTaskCommandV1,
        *,
        error: IntegrityError,
        fingerprint: str,
    ) -> CompleteTaskResultV1:
        if _constraint_name(error) != "uq_tasks_completion_request":
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None
        clean_repository = TaskFollowUpRepository(self._session)
        try:
            with self._session.begin():
                owner = clean_repository.task_for_completion_request(
                    command.request_id
                )
                if owner is None:
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                    )
                if (
                    owner.task_id != command.task_id
                    or owner.status != "completed"
                    or owner.completion_request_fingerprint != fingerprint
                ):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
                    )
                follow_up = clean_repository.follow_up_for_action(
                    owner.task_id, for_update=True
                )
                return CompleteTaskResultV1("duplicate", owner, follow_up)
        except TaskFollowUpError:
            self._rollback()
            raise
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def _recover_outcome_request_loss(
        self,
        command: RecordOutcomeCommandV1,
        *,
        error: IntegrityError,
        fingerprint: str,
    ) -> RecordOutcomeResultV1:
        if _constraint_name(error) not in {
            "uq_tasks_completion_request",
            "uq_outcomes_request",
        }:
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None
        clean_repository = TaskFollowUpRepository(self._session)
        try:
            with self._session.begin():
                task_owner = clean_repository.task_for_completion_request(
                    command.request_id
                )
                outcome_owner = clean_repository.outcome_for_request(
                    command.request_id
                )
                if task_owner is not None and (
                    task_owner.task_id != command.follow_up_task_id
                    or task_owner.completion_request_fingerprint != fingerprint
                ):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
                    )
                if outcome_owner is not None and (
                    outcome_owner.follow_up_task_id != command.follow_up_task_id
                    or outcome_owner.request_fingerprint != fingerprint
                    or outcome_owner.value != command.value.value
                    or outcome_owner.evidence_refs != list(command.evidence_refs)
                ):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_VERSION_CONFLICT
                    )
                if (
                    task_owner is None
                    or outcome_owner is None
                    or task_owner.status != "completed"
                    or outcome_owner.follow_up_task_id != task_owner.task_id
                ):
                    raise TaskFollowUpError(
                        TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
                    )
                return RecordOutcomeResultV1(
                    "duplicate", task_owner, outcome_owner
                )
        except TaskFollowUpError:
            self._rollback()
            raise
        except SQLAlchemyError:
            self._rollback()
            raise TaskFollowUpError(
                TaskFollowUpErrorCode.TASK_PERSISTENCE_FAILED
            ) from None

    def _materialize_locked(
        self, decision: SafetyActionDecision, *, require_active: bool
    ) -> tuple[Approval, bool]:
        if (
            decision.safety_status != "pending_human_approval"
            or decision.reason_code != "ready_for_human_approval"
            or decision.action_kind not in _ACTION_TEXT
            or decision.expires_at is None
            or decision.ph_measurement_id is None
            or decision.ec_measurement_id is None
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
        if require_active:
            from ..access_admin.models import Plant
            plant = self._session.get(Plant, decision.plant_id, with_for_update=True)
            if plant is None or plant.farm_id != decision.farm_id:
                raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SCOPE_NOT_FOUND)
            if plant.status != "active":
                raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_PLANT_NOT_ACTIVE)
        refs = ordered_unique(
            (
                f"safety_decision:{decision.decision_id}",
                f"manual_measurement:{decision.ph_measurement_id}",
                f"manual_measurement:{decision.ec_measurement_id}",
            )
        )
        existing = self._repository.approval_for_decision(
            decision.decision_id, for_update=True
        )
        if existing is not None:
            if (
                existing.farm_id != decision.farm_id
                or existing.plant_id != decision.plant_id
                or existing.action_kind != decision.action_kind
                or _utc(existing.valid_until) != _utc(decision.expires_at)
                or existing.source_refs != list(refs)
            ):
                raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)
            return existing, False
        approval = Approval(
            approval_id=uuid.uuid4(), safety_decision_id=decision.decision_id,
            farm_id=decision.farm_id, plant_id=decision.plant_id,
            action_kind=decision.action_kind, status="pending", record_version=1,
            valid_until=_utc(decision.expires_at), source_refs=list(refs),
            created_at=_utc(self._clock()),
        )
        self._session.add(approval)
        self._session.flush()
        return approval, True

    def _validate_current_approval(
        self, decision: SafetyActionDecision, approval: Approval, *, now: datetime
    ) -> None:
        if (
            decision.safety_status != "pending_human_approval"
            or decision.reason_code != "ready_for_human_approval"
            or decision.plant_id != approval.plant_id
            or decision.action_kind != approval.action_kind
            or _utc(decision.expires_at) != _utc(approval.valid_until)
            or now > _utc(approval.valid_until)
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.APPROVAL_NOT_CURRENT)
        ph = self._repository.lock_measurement(decision.ph_measurement_id)
        ec = self._repository.lock_measurement(decision.ec_measurement_id)
        if (
            ph is None or ec is None
            or ph.farm_id != decision.farm_id or ec.farm_id != decision.farm_id
            or ph.plant_id != decision.plant_id or ec.plant_id != decision.plant_id
            or ph.ph is None or ec.ec_ms_cm is None
            or _utc(ph.measured_at) != _utc(decision.ph_measured_at)
            or _utc(ec.measured_at) != _utc(decision.ec_measured_at)
            or not now - timedelta(hours=2) <= _utc(ph.measured_at) <= now
            or not now - timedelta(hours=2) <= _utc(ec.measured_at) <= now
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.APPROVAL_NOT_CURRENT)

    def _require_identical_ordinary(
        self, task, command, *, refs, display_text, fingerprint
    ) -> None:
        envelope = command.message_envelope
        if not (
            task.farm_id == envelope.farm_id
            and task.plant_id == envelope.plant_id
            and task.kind == command.task_kind.value
            and task.source_type == "safe_task_request"
            and task.source_refs == list(refs)
            and task.display_text == display_text
            and task.create_request_id == envelope.run_id
            and task.create_request_fingerprint == fingerprint
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_VERSION_CONFLICT)

    def _new_action_task(self, approval, command, *, scope, now) -> Task:
        return Task(
            task_id=uuid.uuid4(), farm_id=approval.farm_id,
            plant_id=approval.plant_id, kind="action", status="open",
            display_text=_ACTION_TEXT[approval.action_kind],
            source_type="approved_action",
            source_refs=[f"approval:{approval.approval_id}", *approval.source_refs],
            classification_message_id=None, approval_id=approval.approval_id,
            parent_action_task_id=None, due_at=None,
            created_by_account_id=command.actor_context.account_id,
            created_by_membership_id=command.actor_context.membership_id,
            created_by_role_preset=scope.role_preset,
            created_by_agent_id=None, created_at=now,
            create_request_id=None, create_request_fingerprint=None,
            created_event_ref={},
        )

    def _append_task_created(self, task: Task, actor) -> dict[str, object]:
        return self._emit(TimelineEvent(
            farm_id=task.farm_id, plant_id=task.plant_id,
            actor_ref=_actor_ref(actor), event_type="task_created",
            source_type="task", source_id=task.task_id,
            source_refs={"record_refs": list(task.source_refs)},
            payload_summary={
                "task_kind": task.kind, "task_source_type": task.source_type,
                "due_at": timestamp_text(task.due_at) if task.due_at else None,
                "source_ref_count": len(task.source_refs),
            },
        ))

    def _append_task_completed(self, task, actor, *, completion_kind):
        return self._emit(TimelineEvent(
            farm_id=task.farm_id, plant_id=task.plant_id,
            actor_ref=_actor_ref(actor), event_type="task_completed",
            source_type="task", source_id=task.task_id,
            source_refs={"record_refs": list(task.source_refs)},
            payload_summary={
                "task_kind": task.kind, "completion_kind": completion_kind,
                "source_ref_count": len(task.source_refs),
            },
        ))

    def _append_approval_decided(self, approval, actor, *, action_task_id):
        payload_summary = {
            "decision": approval.status,
            "action_kind": approval.action_kind,
            "record_version": 2,
        }
        if approval.status == "approved":
            if not isinstance(action_task_id, uuid.UUID):
                raise TimelineAppendError
            payload_summary["action_task_id"] = str(action_task_id)
        elif action_task_id is not None:
            raise TimelineAppendError
        return self._emit(TimelineEvent(
            farm_id=approval.farm_id, plant_id=approval.plant_id,
            actor_ref=_actor_ref(actor), event_type="approval_decided",
            source_type="approval", source_id=approval.approval_id,
            source_refs={"record_refs": list(approval.source_refs)},
            payload_summary=payload_summary,
        ))

    def _append_outcome(self, outcome, actor):
        return self._emit(TimelineEvent(
            farm_id=outcome.farm_id, plant_id=outcome.plant_id,
            actor_ref=_actor_ref(actor), event_type="follow_up_outcome_recorded",
            source_type="outcome", source_id=outcome.outcome_id,
            source_refs={"record_refs": list(outcome.evidence_refs)},
            payload_summary={
                "follow_up_task_id": str(outcome.follow_up_task_id),
                "outcome_value": outcome.value,
                "evidence_ref_count": len(outcome.evidence_refs),
            },
        ))

    def _emit(self, event: TimelineEvent) -> dict[str, object]:
        try:
            ref = self._timeline(event)
        except Exception:
            raise TimelineAppendError from None
        if not isinstance(ref, dict):
            raise TimelineAppendError
        return ref

    def _rollback(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()


def _actor_ref(actor) -> dict[str, object]:
    return {
        "account_id": str(actor.account_id),
        "membership_id": str(actor.membership_id),
        "role_preset": actor.role_preset.value,
    }


def _utc(value: datetime | None) -> datetime:
    if not isinstance(value, datetime):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if normalized.utcoffset() is None:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
    return normalized.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(getattr(error, "orig", None), "diag", None)
    value = getattr(diagnostic, "constraint_name", None)
    return value if isinstance(value, str) and value else None


__all__ = ["TaskFollowUpService"]
