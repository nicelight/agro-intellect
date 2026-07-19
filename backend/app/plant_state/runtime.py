"""Provider-neutral Plant State assessment over authorized PostgreSQL records."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Protocol
import uuid

from sqlalchemy import select
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
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    PlantStateAssessmentCandidateV1,
    PlantStateInputRecordV1,
    PlantStateModelResultV1,
    PlantStateProviderRequestV1,
    PlantStateRuntimeOutcomeV1,
    PlantStateValidationError,
    validate_structural_assessment,
)
from .models import PlantStateRecord


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


class PlantStateInputDenied(RuntimeError):
    def __init__(self, reason_code: str = "context_denied") -> None:
        self.reason_code = reason_code
        super().__init__("Plant State input context is unavailable.")


@dataclass(frozen=True, slots=True)
class PlantStateCommand:
    run_id: uuid.UUID
    requested_at: datetime
    actor_context: ActorContext
    plant_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class AssembledPlantStateInputV1:
    request: PlantStateProviderRequestV1

    def __post_init__(self) -> None:
        if not isinstance(self.request, PlantStateProviderRequestV1):
            raise PlantStateValidationError()


class PlantStateInputAssembler(Protocol):
    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> AssembledPlantStateInputV1: ...


class PlantStateModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: PlantStateProviderRequestV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class DatabasePlantStateInputAssembler:
    def __init__(self, session: Session, *, authorization_guard=None) -> None:
        self._session = session
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session
        )

    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> AssembledPlantStateInputV1:
        try:
            scope = self._authorization_guard.current_scope(actor, plant_id=plant_id)
        except Exception:
            scope = None
        if scope is None:
            raise PlantStateInputDenied()
        rows = list(
            self._session.scalars(
                select(PlantStateRecord)
                .where(
                    PlantStateRecord.farm_id == scope.farm_id,
                    PlantStateRecord.plant_id == plant_id,
                    PlantStateRecord.trust_status != "rejected",
                )
                .order_by(
                    PlantStateRecord.recorded_at.desc(),
                    PlantStateRecord.state_record_id.desc(),
                )
                .limit(4)
                .execution_options(populate_existing=True)
            )
        )
        if not rows:
            raise PlantStateInputDenied()
        rows.reverse()
        try:
            records = tuple(_input_record(item) for item in rows)
            request = PlantStateProviderRequestV1(
                records=records,
                source_refs=tuple(item.source_ref for item in records),
            )
        except (PlantStateValidationError, TypeError, ValueError):
            raise PlantStateInputDenied("input_contract_violation") from None
        return AssembledPlantStateInputV1(request=request)


class _PlantStateMessageEnvelopeV1(MessageEnvelopeV1):
    __slots__ = ()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.message_id)
            or not _uuid4(self.run_id)
            or self.agent_id != "plant_state"
            or not _is_utc(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision not in {RuntimeDecision.SPEAK, RuntimeDecision.CLARIFY}
            or self.candidate_claim_type not in {"hypothesis", "clarification"}
            or not isinstance(self.candidate_output, str)
            or self.candidate_output != self.candidate_output.strip()
            or not 1 <= len(self.candidate_output) <= 1000
            or not 1 <= len(self.source_refs) <= 4
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not _state_record_ref(item) for item in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()
        if self.runtime_decision is RuntimeDecision.SPEAK:
            if (
                self.candidate_claim_type != "hypothesis"
                or isinstance(self.confidence, bool)
                or not isinstance(self.confidence, int | float)
                or not 0 <= float(self.confidence) <= 1
            ):
                raise AgentRuntimeValidationError()
        elif self.candidate_claim_type != "clarification" or self.confidence is not None:
            raise AgentRuntimeValidationError()


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]


class PlantStateRuntimeService:
    def __init__(
        self,
        session: Session,
        *,
        model_executor: PlantStateModelExecutor | None = None,
        input_assembler: PlantStateInputAssembler | None = None,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        timeline_append: TimelineAppender | None = None,
        clock=None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._input_assembler = input_assembler or DatabasePlantStateInputAssembler(
            session,
            authorization_guard=self._authorization_guard,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender()

    def invoke(self, command: PlantStateCommand) -> PlantStateRuntimeOutcomeV1:
        _validate_command(command)
        try:
            assembled = self._input_assembler.assemble(
                command.actor_context,
                plant_id=command.plant_id,
            )
        except PlantStateInputDenied as denied:
            return _wrap(_context_denied(command.run_id, denied.reason_code))
        except Exception:
            return _wrap(_context_denied(command.run_id, "input_contract_violation"))
        self._end_transaction()

        executor = self._model_executor
        model_ref = getattr(executor, "model_ref", None)
        if (
            executor is None
            or not isinstance(model_ref, str)
            or _MODEL_REF_RE.fullmatch(model_ref) is None
        ):
            return _wrap(_not_configured(command.run_id))
        try:
            execution = executor.execute(assembled.request)
        except Exception:
            return self._audit(
                command=command,
                model_ref=model_ref,
                outcome_kind="provider_failed",
                status="failed",
                final_decision=None,
                reason_code="provider_failed",
                error_code="AGENT_PROVIDER_FAILED",
                provider_call_status="failed",
                result=None,
                envelope=None,
                candidate=None,
            )
        raw_result = _execution_result(execution, expected_model_ref=model_ref)
        try:
            result = PlantStateModelResultV1.from_untrusted(
                raw_result,
                request_source_refs=assembled.request.source_refs,
            )
        except PlantStateValidationError:
            return self._audit(
                command=command,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                final_decision=None,
                reason_code="output_invalid",
                error_code="AGENT_OUTPUT_INVALID",
                provider_call_status="completed",
                result=None,
                envelope=None,
                candidate=None,
            )

        self._end_transaction()
        try:
            scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=command.plant_id,
            )
        except Exception:
            scope = None
        if scope is None:
            self._end_transaction()
            return self._audit(
                command=command,
                model_ref=model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                result=result,
                envelope=None,
                candidate=None,
            )
        if result.runtime_decision == "silent":
            self._end_transaction()
            return self._audit(
                command=command,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code=result.reason_code or "insufficient_evidence",
                error_code=None,
                provider_call_status="completed",
                result=result,
                envelope=None,
                candidate=None,
            )
        referenced = self._reload_referenced(command, result)
        self._end_transaction()
        if referenced is None or not validate_structural_assessment(
            referenced,
            assessment_kind=result.assessment_kind or "",
            observation_key=result.observation_key or "",
            direction=result.direction or "",
        ):
            return self._audit(
                command=command,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                final_decision=None,
                reason_code="output_invalid",
                error_code="AGENT_OUTPUT_INVALID",
                provider_call_status="completed",
                result=None,
                envelope=None,
                candidate=None,
            )

        assert result.summary is not None
        message_id = uuid.uuid4()
        decision = (
            RuntimeDecision.SPEAK
            if result.runtime_decision == "speak"
            else RuntimeDecision.CLARIFY
        )
        envelope = _PlantStateMessageEnvelopeV1(
            message_id=message_id,
            run_id=command.run_id,
            agent_id="plant_state",
            created_at=_as_utc(self._clock()),
            farm_id=scope.farm_id,
            plant_id=scope.plant_id,
            runtime_decision=decision,
            candidate_claim_type=(
                "hypothesis" if decision is RuntimeDecision.SPEAK else "clarification"
            ),
            confidence=result.confidence,
            source_refs=result.source_refs,
            candidate_output=result.summary,
            authorization_scope=scope,
        )
        candidate = None
        if result.runtime_decision == "speak":
            assert result.assessment_kind is not None
            assert result.observation_key is not None
            assert result.direction is not None
            assert result.confidence is not None
            candidate = PlantStateAssessmentCandidateV1(
                run_id=command.run_id,
                message_id=message_id,
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                assessment_kind=result.assessment_kind,
                observation_key=result.observation_key,
                direction=result.direction,
                summary=result.summary,
                confidence=result.confidence,
                source_refs=result.source_refs,
                observed_at=max(_as_utc(item.observed_at) for item in referenced),
            )
        return self._audit(
            command=command,
            model_ref=model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision=result.runtime_decision,
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            result=result,
            envelope=envelope,
            candidate=candidate,
        )

    def run(self, command: PlantStateCommand) -> PlantStateRuntimeOutcomeV1:
        return self.invoke(command)

    def _reload_referenced(
        self,
        command: PlantStateCommand,
        result: PlantStateModelResultV1,
    ) -> list[PlantStateRecord] | None:
        ids = [_record_id(item) for item in result.source_refs]
        if any(item is None for item in ids):
            return None
        rows = list(
            self._session.scalars(
                select(PlantStateRecord).where(
                    PlantStateRecord.farm_id == command.actor_context.farm_id,
                    PlantStateRecord.plant_id == command.plant_id,
                    PlantStateRecord.state_record_id.in_(ids),
                    PlantStateRecord.trust_status != "rejected",
                )
            )
        )
        by_id = {item.state_record_id: item for item in rows}
        ordered = [by_id.get(item) for item in ids]
        return None if any(item is None for item in ordered) else [
            item for item in ordered if item is not None
        ]

    def _end_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()

    def _audit(
        self,
        *,
        command: PlantStateCommand,
        model_ref: str,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        result: PlantStateModelResultV1 | None,
        envelope: MessageEnvelopeV1 | None,
        candidate: PlantStateAssessmentCandidateV1 | None,
    ) -> PlantStateRuntimeOutcomeV1:
        event = _runtime_event(
            command=command,
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
            return _wrap(
                AgentRuntimeOutcomeV1(
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
            )
        return PlantStateRuntimeOutcomeV1(
            runtime_outcome=AgentRuntimeOutcomeV1(
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
            ),
            state_candidate=candidate,
        )


def _input_record(record: PlantStateRecord) -> PlantStateInputRecordV1:
    return PlantStateInputRecordV1(
        source_ref=f"plant_state_record:{record.state_record_id}",
        payload={
            "state_record_id": str(record.state_record_id),
            "observation_key": record.observation_key,
            "polarity": record.polarity,
            "severity": record.severity,
            "assessment_kind": record.assessment_kind,
            "direction": record.direction,
            "trust_status": record.trust_status,
            "observed_at": _timestamp(record.observed_at),
            "recorded_at": _timestamp(record.recorded_at),
            "confidence": float(record.confidence),
            "source_refs": list(record.source_refs),
        },
    )


def _runtime_event(
    *,
    command: PlantStateCommand,
    model_ref: str,
    outcome_kind: str,
    status: str,
    final_decision: str | None,
    reason_code: str,
    error_code: str | None,
    result: PlantStateModelResultV1 | None,
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
        source_refs={"input_refs": [f"plant:{command.plant_id}"]},
        payload_summary={
            "agent_id": "plant_state",
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "candidate_decision": result.runtime_decision if result else None,
            "final_decision": final_decision,
            "outcome_status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "message_id": str(envelope.message_id) if envelope else None,
            "candidate_claim_type": (
                "hypothesis"
                if result is not None and result.runtime_decision == "speak"
                else "clarification"
                if result is not None and result.runtime_decision == "clarify"
                else None
            ),
            "source_ref_count": len(result.source_refs) if result else 0,
        },
    )


def _validate_command(command: object) -> None:
    if (
        not isinstance(command, PlantStateCommand)
        or not _uuid4(command.run_id)
        or not _is_utc(command.requested_at)
        or not isinstance(command.actor_context, ActorContext)
        or not isinstance(command.plant_id, uuid.UUID)
    ):
        raise PlantStateValidationError()


def _execution_result(execution: object, *, expected_model_ref: str) -> object:
    if isinstance(execution, ModelExecution):
        return execution.result if execution.model_ref == expected_model_ref else None
    return execution if isinstance(execution, Mapping) else None


def _context_denied(run_id: uuid.UUID, reason_code: str) -> AgentRuntimeOutcomeV1:
    safe_reason = reason_code if reason_code in {
        "context_denied",
        "input_contract_violation",
    } else "input_contract_violation"
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


def _wrap(outcome: AgentRuntimeOutcomeV1) -> PlantStateRuntimeOutcomeV1:
    return PlantStateRuntimeOutcomeV1(runtime_outcome=outcome, state_candidate=None)


def _record_id(value: str) -> uuid.UUID | None:
    if not _state_record_ref(value):
        return None
    return uuid.UUID(value.split(":", 1)[1])


def _state_record_ref(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("plant_state_record:"):
        return False
    try:
        parsed = uuid.UUID(value.split(":", 1)[1])
    except (TypeError, ValueError, AttributeError):
        return False
    return value == f"plant_state_record:{parsed}"


def _event_ref_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("event_type") != "agent_runtime_decided":
        return False
    try:
        uuid.UUID(str(value["timeline_event_id"]))
    except (KeyError, TypeError, ValueError):
        return False
    return (
        isinstance(value.get("timeline_ref"), str)
        and str(value["timeline_ref"]).startswith("timeline.jsonl#")
        and isinstance(value.get("created_at"), str)
    )


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
    "AssembledPlantStateInputV1",
    "DatabasePlantStateInputAssembler",
    "PlantStateCommand",
    "PlantStateInputAssembler",
    "PlantStateInputDenied",
    "PlantStateModelExecutor",
    "PlantStateRuntimeService",
]
