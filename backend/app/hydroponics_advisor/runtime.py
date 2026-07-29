"""Provider-neutral Hydroponics Advisor over authorized PostgreSQL evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Protocol
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import Plant
from ..agent_runtime.contracts import (
    AgentRuntimeOutcomeV1,
    AgentRuntimeValidationError,
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    RuntimeDecision,
)
from ..agent_runtime.service import DatabaseRuntimeAuthorizationGuard, ModelExecution
from ..plant_operations.models import DailyCheckIn, ManualMeasurement
from ..plant_state.models import PlantStateRecord
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    AnalysisFreshnessV1,
    HydroponicsAdvisorCommandV1,
    HydroponicsAdvisorInputRecordV1,
    HydroponicsAdvisorModelResultV1,
    HydroponicsAdvisorProviderRequestV1,
    HydroponicsAdvisorValidationError,
    MeasurementFreshnessV1,
    fixed_decimal,
    measurement_request_text,
)


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")
_OUTER_REF_KINDS = frozenset(
    {"plant", "daily_checkin", "manual_measurement", "plant_state_record"}
)


class HydroponicsAdvisorInputDenied(RuntimeError):
    def __init__(self, reason_code: str = "context_denied") -> None:
        self.reason_code = reason_code
        super().__init__("Hydroponics Advisor input context is unavailable.")


@dataclass(frozen=True, slots=True)
class AssembledHydroponicsAdvisorInputV1:
    request: HydroponicsAdvisorProviderRequestV1

    def __post_init__(self) -> None:
        if not isinstance(self.request, HydroponicsAdvisorProviderRequestV1):
            raise HydroponicsAdvisorValidationError()


class HydroponicsAdvisorInputAssembler(Protocol):
    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        request_reason: str,
        analysis_goal: str,
        computed_at: datetime,
    ) -> AssembledHydroponicsAdvisorInputV1: ...


class HydroponicsAdvisorModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: HydroponicsAdvisorProviderRequestV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class DatabaseHydroponicsAdvisorInputAssembler:
    """Load the exact bounded Plant/advisor evidence from PostgreSQL."""

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
        request_reason: str,
        analysis_goal: str,
        computed_at: datetime,
    ) -> AssembledHydroponicsAdvisorInputV1:
        if not _is_utc(computed_at):
            raise HydroponicsAdvisorInputDenied("input_contract_violation")
        try:
            scope = self._authorization_guard.current_scope(actor, plant_id=plant_id)
        except Exception:
            scope = None
        if scope is None:
            raise HydroponicsAdvisorInputDenied()

        plant = self._session.scalar(
            select(Plant)
            .where(
                Plant.farm_id == scope.farm_id,
                Plant.plant_id == scope.plant_id,
                Plant.status == "active",
            )
            .execution_options(populate_existing=True)
        )
        if plant is None:
            raise HydroponicsAdvisorInputDenied()
        latest_ph = self._latest_measurement(scope, field="ph")
        latest_ec = self._latest_measurement(scope, field="ec_ms_cm")
        latest_check_in = self._session.scalar(
            select(DailyCheckIn)
            .where(
                DailyCheckIn.farm_id == scope.farm_id,
                DailyCheckIn.plant_id == scope.plant_id,
                DailyCheckIn.check_in_state == "completed",
            )
            .order_by(DailyCheckIn.recorded_at.desc(), DailyCheckIn.check_in_id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        latest_state = self._session.scalar(
            select(PlantStateRecord)
            .where(
                PlantStateRecord.farm_id == scope.farm_id,
                PlantStateRecord.plant_id == scope.plant_id,
                PlantStateRecord.trust_status != "rejected",
            )
            .order_by(
                PlantStateRecord.recorded_at.desc(),
                PlantStateRecord.state_record_id.desc(),
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )

        try:
            records = [_plant_record(plant)]
            if latest_ph is not None:
                records.append(_measurement_record(latest_ph))
            if latest_ec is not None and (
                latest_ph is None
                or latest_ec.measurement_id != latest_ph.measurement_id
            ):
                records.append(_measurement_record(latest_ec))

            context: list[tuple[datetime, str, HydroponicsAdvisorInputRecordV1]] = []
            if latest_check_in is not None:
                record = _check_in_record(latest_check_in)
                context.append(
                    (_as_utc(latest_check_in.recorded_at), record.source_ref, record)
                )
            if latest_state is not None:
                record = _plant_state_record(latest_state)
                context.append(
                    (_as_utc(latest_state.recorded_at), record.source_ref, record)
                )
            available_slots = 4 - len(records)
            selected_context = sorted(context, key=lambda item: (item[0], item[1]))[
                -available_slots:
            ]
            records.extend(item[2] for item in selected_context)

            computed_text = _timestamp(computed_at)
            ph_freshness = _freshness_value(
                latest_ph,
                field="ph",
                computed_at=computed_at,
            )
            ec_freshness = _freshness_value(
                latest_ec,
                field="ec_ms_cm",
                computed_at=computed_at,
            )
            freshness = AnalysisFreshnessV1(
                computed_at=computed_text,
                ph=ph_freshness,
                ec=ec_freshness,
                missing_or_stale=tuple(
                    name
                    for name, value in (("ph", ph_freshness), ("ec", ec_freshness))
                    if value.status != "fresh"
                ),
            )
            request = HydroponicsAdvisorProviderRequestV1(
                request_reason=request_reason,
                analysis_goal=analysis_goal,
                computed_at=computed_text,
                analysis_freshness=freshness,
                records=tuple(records),
            )
        except (HydroponicsAdvisorValidationError, TypeError, ValueError):
            raise HydroponicsAdvisorInputDenied("input_contract_violation") from None
        return AssembledHydroponicsAdvisorInputV1(request=request)

    def _latest_measurement(
        self,
        scope: CurrentAuthorizationScope,
        *,
        field: str,
    ) -> ManualMeasurement | None:
        column = (
            ManualMeasurement.ph
            if field == "ph"
            else ManualMeasurement.ec_ms_cm
        )
        return self._session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == scope.farm_id,
                ManualMeasurement.plant_id == scope.plant_id,
                column.is_not(None),
            )
            .order_by(
                ManualMeasurement.measured_at.desc(),
                ManualMeasurement.measurement_id.desc(),
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )


class _HydroponicsAdvisorMessageEnvelopeV1(MessageEnvelopeV1):
    __slots__ = ()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.message_id)
            or not _uuid4(self.run_id)
            or self.agent_id != "hydroponics_advisor"
            or not _is_utc(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision not in {RuntimeDecision.SPEAK, RuntimeDecision.CLARIFY}
            or self.candidate_claim_type
            not in {"task_request", "recommendation", "hypothesis", "clarification"}
            or not isinstance(self.candidate_output, str)
            or self.candidate_output != self.candidate_output.strip()
            or not 1 <= len(self.candidate_output) <= 1000
            or not 1 <= len(self.source_refs) <= 4
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not _outer_ref(ref) for ref in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()
        if self.runtime_decision is RuntimeDecision.CLARIFY:
            if self.candidate_claim_type != "clarification" or self.confidence is not None:
                raise AgentRuntimeValidationError()
            return
        if self.candidate_claim_type == "clarification":
            raise AgentRuntimeValidationError()
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, int | float)
            or not 0 <= float(self.confidence) <= 1
        ):
            raise AgentRuntimeValidationError()


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


class HydroponicsAdvisorRuntimeService:
    """Run one advisor attempt and return only a pending common outcome."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: HydroponicsAdvisorModelExecutor | None = None,
        input_assembler: HydroponicsAdvisorInputAssembler | None = None,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._input_assembler = input_assembler or DatabaseHydroponicsAdvisorInputAssembler(
            session,
            authorization_guard=self._authorization_guard,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender()

    def invoke(self, command: HydroponicsAdvisorCommandV1) -> AgentRuntimeOutcomeV1:
        if not isinstance(command, HydroponicsAdvisorCommandV1):
            raise HydroponicsAdvisorValidationError()
        computed_at = _as_utc(self._clock())
        if not _is_utc(computed_at):
            raise HydroponicsAdvisorValidationError()
        try:
            assembled = self._input_assembler.assemble(
                command.actor_context,
                plant_id=command.plant_id,
                request_reason=command.request_reason,
                analysis_goal=command.analysis_goal,
                computed_at=computed_at,
            )
        except HydroponicsAdvisorInputDenied as denied:
            return _context_denied(command.run_id, denied.reason_code)
        except Exception:
            return _context_denied(command.run_id, "input_contract_violation")
        self._end_transaction()

        executor = self._model_executor
        model_ref = getattr(executor, "model_ref", None)
        if (
            executor is None
            or not isinstance(model_ref, str)
            or _MODEL_REF_RE.fullmatch(model_ref) is None
        ):
            return _not_configured(command.run_id)
        try:
            execution = executor.execute(assembled.request)
        except Exception:
            return self._audit(
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
            )
        raw_result = _execution_result(execution, expected_model_ref=model_ref)
        try:
            result = HydroponicsAdvisorModelResultV1.from_untrusted(
                raw_result,
                request=assembled.request,
            )
        except HydroponicsAdvisorValidationError:
            return self._audit(
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
            )

        self._end_transaction()
        try:
            scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=command.plant_id,
            )
        except Exception:
            scope = None
        self._end_transaction()
        if scope is None:
            return self._audit(
                command=command,
                request=assembled.request,
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
        if result.runtime_decision == "silent":
            return self._audit(
                command=command,
                request=assembled.request,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code=result.reason_code or "insufficient_evidence",
                error_code=None,
                provider_call_status="completed",
                result=result,
                envelope=None,
            )

        envelope = _message_envelope(
            command=command,
            scope=scope,
            result=result,
            created_at=_as_utc(self._clock()),
        )
        return self._audit(
            command=command,
            request=assembled.request,
            model_ref=model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision=result.runtime_decision,
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            result=result,
            envelope=envelope,
        )

    def run(self, command: HydroponicsAdvisorCommandV1) -> AgentRuntimeOutcomeV1:
        return self.invoke(command)

    def _end_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()

    def _audit(
        self,
        *,
        command: HydroponicsAdvisorCommandV1,
        request: HydroponicsAdvisorProviderRequestV1,
        model_ref: str,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        result: HydroponicsAdvisorModelResultV1 | None,
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


def _plant_record(plant: Plant) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="plant",
        source_ref=f"plant:{plant.plant_id}",
        payload={"plant_id": str(plant.plant_id), "status": plant.status},
    )


def _check_in_record(check_in: DailyCheckIn) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="daily_checkin",
        source_ref=f"daily_checkin:{check_in.check_in_id}",
        payload={
            "check_in_id": str(check_in.check_in_id),
            "observed_at": _timestamp(check_in.observed_at),
            "recorded_at": _timestamp(check_in.recorded_at),
            "observation_state": check_in.observation_state,
            "observation_text": check_in.observation_text,
        },
    )


def _measurement_record(
    measurement: ManualMeasurement,
) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="manual_measurement",
        source_ref=f"manual_measurement:{measurement.measurement_id}",
        payload={
            "measurement_id": str(measurement.measurement_id),
            "measured_at": _timestamp(measurement.measured_at),
            "recorded_at": _timestamp(measurement.recorded_at),
            "ph": fixed_decimal(measurement.ph, places=2)
            if measurement.ph is not None
            else None,
            "ec_ms_cm": fixed_decimal(measurement.ec_ms_cm, places=3)
            if measurement.ec_ms_cm is not None
            else None,
            "source_type": measurement.source_type,
            "trust_status": measurement.trust_status,
        },
    )


def _plant_state_record(
    record: PlantStateRecord,
) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="plant_state_record",
        source_ref=f"plant_state_record:{record.state_record_id}",
        payload={
            "state_record_id": str(record.state_record_id),
            "record_kind": record.record_kind,
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


def _freshness_value(
    measurement: ManualMeasurement | None,
    *,
    field: str,
    computed_at: datetime,
) -> MeasurementFreshnessV1:
    if measurement is None or getattr(measurement, field) is None:
        return MeasurementFreshnessV1(
            status="missing",
            source_ref=None,
            measured_at=None,
        )
    measured_at = _as_utc(measurement.measured_at)
    computed_at = _as_utc(computed_at)
    status = (
        "fresh"
        if computed_at - timedelta(hours=24) <= measured_at <= computed_at
        else "stale"
    )
    return MeasurementFreshnessV1(
        status=status,
        source_ref=f"manual_measurement:{measurement.measurement_id}",
        measured_at=_timestamp(measured_at),
    )


def _message_envelope(
    *,
    command: HydroponicsAdvisorCommandV1,
    scope: CurrentAuthorizationScope,
    result: HydroponicsAdvisorModelResultV1,
    created_at: datetime,
) -> MessageEnvelopeV1:
    if result.advice_kind == "measurement_request":
        decision = RuntimeDecision.SPEAK
        claim = "task_request"
        confidence = 1.0
        output = measurement_request_text(result.requested_measurements)
    elif result.advice_kind == "clarification":
        decision = RuntimeDecision.CLARIFY
        claim = "clarification"
        confidence = None
        assert result.candidate_output is not None
        output = result.candidate_output
    else:
        decision = RuntimeDecision.SPEAK
        assert result.advice_kind in {"recommendation", "hypothesis"}
        claim = result.advice_kind
        confidence = result.confidence
        assert result.candidate_output is not None
        output = result.candidate_output
    return _HydroponicsAdvisorMessageEnvelopeV1(
        message_id=uuid.uuid4(),
        run_id=command.run_id,
        agent_id="hydroponics_advisor",
        created_at=created_at,
        farm_id=scope.farm_id,
        plant_id=scope.plant_id,
        runtime_decision=decision,
        candidate_claim_type=claim,
        confidence=confidence,
        source_refs=result.source_refs,
        candidate_output=output,
        authorization_scope=scope,
    )


def _runtime_event(
    *,
    command: HydroponicsAdvisorCommandV1,
    request: HydroponicsAdvisorProviderRequestV1,
    model_ref: str,
    outcome_kind: str,
    status: str,
    final_decision: str | None,
    reason_code: str,
    error_code: str | None,
    result: HydroponicsAdvisorModelResultV1 | None,
    envelope: MessageEnvelopeV1 | None,
) -> TimelineEvent:
    claim = None
    if result is not None:
        claim = {
            "measurement_request": "task_request",
            "recommendation": "recommendation",
            "hypothesis": "hypothesis",
            "clarification": "clarification",
        }.get(result.advice_kind)
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
            "agent_id": "hydroponics_advisor",
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "candidate_decision": result.runtime_decision if result else None,
            "final_decision": final_decision,
            "outcome_status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "message_id": str(envelope.message_id) if envelope else None,
            "candidate_claim_type": claim,
            "source_ref_count": len(request.source_refs),
        },
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


def _outer_ref(value: object) -> bool:
    if not isinstance(value, str) or ":" not in value:
        return False
    kind, identifier = value.split(":", 1)
    if kind not in _OUTER_REF_KINDS:
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
    "AssembledHydroponicsAdvisorInputV1",
    "DatabaseHydroponicsAdvisorInputAssembler",
    "HydroponicsAdvisorInputAssembler",
    "HydroponicsAdvisorInputDenied",
    "HydroponicsAdvisorModelExecutor",
    "HydroponicsAdvisorRuntimeService",
]
