"""Provider-neutral W1 Agent Runtime service.

This module intentionally contains no provider/profile composition.  A caller
must inject a real executor through the narrow test/composition seam; absent or
invalid composition returns the closed ``runtime_not_configured`` outcome.
"""

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
from ..access_admin.context_builders import (
    ContextSourceKind,
    PlantContextCandidate,
    build_authorized_plant_context,
)
from ..access_admin.models import Account, FarmMembership, LocalSession, Plant, PlantAccessGrant
from ..access_admin.permissions import (
    MembershipStatus,
    OperationKind,
    PermissionSource,
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
    PlantStatus,
    RolePreset,
    _BoundedPlantPermissionResolver,
)
from ..plant_operations.models import DailyCheckIn, ManualMeasurement
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    AgentDefinition,
    AgentInputRecordV1,
    AgentModelResultV1,
    AgentRuntimeOutcomeV1,
    AgentRuntimeValidationError,
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    ProviderRequestV1,
    RuntimeDecision,
)


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


class InputAssemblyDenied(RuntimeError):
    """The existing authority/input seam cannot produce a legal request."""

    def __init__(self, reason_code: str = "context_denied") -> None:
        self.reason_code = reason_code
        super().__init__("Agent input context is unavailable.")


@dataclass(frozen=True, slots=True)
class AgentRunCommand:
    run_id: uuid.UUID
    requested_at: datetime
    agent_definition_id: str
    actor_context: ActorContext
    plant_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ModelExecution:
    """Only the safe model identifier and untrusted candidate cross this seam."""

    model_ref: str
    result: Mapping[str, object]


class AgentDefinitionResolver(Protocol):
    def resolve(self, agent_definition_id: str) -> AgentDefinition | None: ...


class ModelExecutor(Protocol):
    model_ref: str

    def execute(self, request: ProviderRequestV1) -> ModelExecution | Mapping[str, object]: ...


class AgentInputAssembler(Protocol):
    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        definition: AgentDefinition,
    ) -> ProviderRequestV1: ...


class RuntimeAuthorizationGuard(Protocol):
    def current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> CurrentAuthorizationScope | None: ...


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


class StaticAgentDefinitionResolver:
    """Small project-owned resolver useful for explicit non-production tests."""

    def __init__(self, definitions: Mapping[str, AgentDefinition]) -> None:
        self._definitions = dict(definitions)

    def resolve(self, agent_definition_id: str) -> AgentDefinition | None:
        value = self._definitions.get(agent_definition_id)
        return value if isinstance(value, AgentDefinition) else None


class DatabaseAgentInputAssembler:
    """Loads only canonical Plant Operations rows into ProviderRequestV1."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        definition: AgentDefinition,
    ) -> ProviderRequestV1:
        if (
            not isinstance(actor, ActorContext)
            or not isinstance(plant_id, uuid.UUID)
            or not isinstance(definition, AgentDefinition)
        ):
            raise InputAssemblyDenied()
        try:
            preflight_permission = actor.resolve_plant_permission(
                plant_id,
                OperationKind.NORMAL_READ,
            )
        except Exception:
            raise InputAssemblyDenied() from None
        if (
            preflight_permission.plant_status is not PlantStatus.ACTIVE
            or not preflight_permission.can_read
            or preflight_permission.source is PermissionSource.DENIED
        ):
            raise InputAssemblyDenied()
        plant = self._session.scalar(
            select(Plant)
            .where(Plant.farm_id == actor.farm_id, Plant.plant_id == plant_id)
            .execution_options(populate_existing=True)
        )
        if plant is None:
            raise InputAssemblyDenied()
        check_in = self._session.scalar(
            select(DailyCheckIn)
            .where(
                DailyCheckIn.farm_id == actor.farm_id,
                DailyCheckIn.plant_id == plant_id,
                DailyCheckIn.check_in_state == "completed",
            )
            .order_by(DailyCheckIn.recorded_at.desc(), DailyCheckIn.check_in_id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        latest_ph = self._session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == actor.farm_id,
                ManualMeasurement.plant_id == plant_id,
                ManualMeasurement.ph.is_not(None),
            )
            .order_by(ManualMeasurement.measured_at.desc(), ManualMeasurement.measurement_id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        latest_ec = self._session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == actor.farm_id,
                ManualMeasurement.plant_id == plant_id,
                ManualMeasurement.ec_ms_cm.is_not(None),
            )
            .order_by(ManualMeasurement.measured_at.desc(), ManualMeasurement.measurement_id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )

        try:
            records: list[AgentInputRecordV1] = [_plant_record(plant)]
            if check_in is not None:
                records.append(_check_in_record(check_in))
            if latest_ph is not None:
                records.append(_measurement_record(latest_ph))
            if latest_ec is not None and (
                latest_ph is None
                or latest_ec.measurement_id != latest_ph.measurement_id
            ):
                records.append(_measurement_record(latest_ec))
        except (AgentRuntimeValidationError, ValueError, TypeError):
            raise InputAssemblyDenied("input_contract_violation") from None

        candidates = tuple(
            PlantContextCandidate(
                plant_id=plant_id,
                source_ref=record.source_ref,
                source_kind=ContextSourceKind.DOMAIN_RECORD,
                consumable_by_agents=True,
                payload=dict(record.payload),
            )
            for record in records
        )
        context = build_authorized_plant_context(
            actor,
            plant_id=plant_id,
            operation_kind=OperationKind.NORMAL_READ,
            candidates=candidates,
        )
        if (
            context is None
            or context.authorization_scope.plant_status is not PlantStatus.ACTIVE
            or not context.authorization_scope.can_read
            or context.authorization_scope.farm_id != actor.farm_id
            or tuple(item.source_ref for item in context.records)
            != tuple(record.source_ref for record in records)
        ):
            raise InputAssemblyDenied()
        try:
            return ProviderRequestV1(
                agent_definition=definition,
                records=tuple(records),
                source_refs=tuple(record.source_ref for record in records),
            )
        except AgentRuntimeValidationError:
            raise InputAssemblyDenied("input_contract_violation") from None


class DatabaseRuntimeAuthorizationGuard:
    """Reloads current identity and Plant/grant authority after model I/O."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or _utc_now

    def current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> CurrentAuthorizationScope | None:
        if not isinstance(actor, ActorContext) or not isinstance(plant_id, uuid.UUID):
            return None
        local_session = self._session.scalar(
            select(LocalSession)
            .where(LocalSession.session_id == actor.session_id)
            .execution_options(populate_existing=True)
        )
        if (
            local_session is None
            or local_session.account_id != actor.account_id
            or local_session.revoked_at is not None
            or local_session.auth_method != "local_password"
            or _as_utc(local_session.expires_at) <= _as_utc(self._clock())
        ):
            return None
        account = self._session.scalar(
            select(Account)
            .where(Account.account_id == actor.account_id)
            .execution_options(populate_existing=True)
        )
        membership = self._session.scalar(
            select(FarmMembership)
            .where(
                FarmMembership.membership_id == actor.membership_id,
                FarmMembership.farm_id == actor.farm_id,
            )
            .execution_options(populate_existing=True)
        )
        plant = self._session.scalar(
            select(Plant)
            .where(Plant.plant_id == plant_id, Plant.farm_id == actor.farm_id)
            .execution_options(populate_existing=True)
        )
        if (
            account is None
            or membership is None
            or plant is None
            or account.account_status != "active"
            or membership.account_id != actor.account_id
            or membership.membership_status != "active"
        ):
            return None
        grant = self._session.scalar(
            select(PlantAccessGrant)
            .where(
                PlantAccessGrant.membership_id == membership.membership_id,
                PlantAccessGrant.plant_id == plant_id,
            )
            .execution_options(populate_existing=True)
        )
        try:
            role = RolePreset(membership.role_preset)
            resolver = _BoundedPlantPermissionResolver(
                farm_id=actor.farm_id,
                membership_id=membership.membership_id,
                membership_status=MembershipStatus.ACTIVE,
                role_preset=role,
                snapshot_provider=lambda **_kwargs: _current_snapshot(
                    plant=plant,
                    membership=membership,
                    grant=grant,
                ),
            )
            permission = resolver.resolve(plant_id, OperationKind.NORMAL_READ)
        except (TypeError, ValueError):
            return None
        if (
            permission.plant_status is not PlantStatus.ACTIVE
            or not permission.can_read
            or permission.source is PermissionSource.DENIED
        ):
            return None
        try:
            return CurrentAuthorizationScope(
                farm_id=actor.farm_id,
                plant_id=plant_id,
                role_preset=role.value,
                operation_kind=OperationKind.NORMAL_READ.value,
                permission_source=permission.source.value,
                grant_id=permission.grant_id,
            )
        except AgentRuntimeValidationError:
            return None


class AgentRuntimeService:
    """Runs one authorized, typed invocation without downstream publication."""

    def __init__(
        self,
        session: Session,
        *,
        definition_resolver: AgentDefinitionResolver,
        model_executor: ModelExecutor | None,
        input_assembler: AgentInputAssembler | None = None,
        authorization_guard: RuntimeAuthorizationGuard | None = None,
        timeline_append: TimelineAppender | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._definition_resolver = definition_resolver
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._input_assembler = input_assembler or DatabaseAgentInputAssembler(session)
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender()

    def invoke(self, command: AgentRunCommand) -> AgentRuntimeOutcomeV1:
        _validate_command(command)
        definition = self._resolve_definition(command.agent_definition_id)
        if definition is None:
            return _not_configured(command.run_id)
        try:
            request = self._input_assembler.assemble(
                command.actor_context,
                plant_id=command.plant_id,
                definition=definition,
            )
        except InputAssemblyDenied as denied:
            return _context_denied(command.run_id, denied.reason_code)
        self._end_database_transaction()

        executor = self._model_executor
        model_ref = _executor_model_ref(executor)
        if executor is None or model_ref is None:
            return _not_configured(command.run_id)
        try:
            execution = executor.execute(request)
        except Exception:
            return self._audit(
                command=command,
                definition=definition,
                request=request,
                model_ref=model_ref,
                outcome_kind="provider_failed",
                status="failed",
                final_decision=None,
                reason_code="provider_failed",
                error_code="AGENT_PROVIDER_FAILED",
                provider_call_status="failed",
                model_result=None,
                message_envelope=None,
            )

        raw_result = _execution_result(execution, expected_model_ref=model_ref)
        try:
            model_result = AgentModelResultV1.from_untrusted(
                raw_result,
                request_source_refs=request.source_refs,
            )
            if (
                model_result.candidate_claim_type is not None
                and model_result.candidate_claim_type
                not in definition.allowed_candidate_claim_types
            ):
                raise AgentRuntimeValidationError()
        except AgentRuntimeValidationError:
            return self._audit(
                command=command,
                definition=definition,
                request=request,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                final_decision=None,
                reason_code="output_invalid",
                error_code="AGENT_OUTPUT_INVALID",
                provider_call_status="completed",
                model_result=None,
                message_envelope=None,
            )

        self._end_database_transaction()
        try:
            current_scope = self._authorization_guard.current_scope(
                command.actor_context,
                plant_id=command.plant_id,
            )
        except Exception:
            current_scope = None
        self._end_database_transaction()
        if current_scope is None:
            return self._audit(
                command=command,
                definition=definition,
                request=request,
                model_ref=model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                model_result=model_result,
                message_envelope=None,
            )
        if model_result.runtime_decision is RuntimeDecision.SILENT:
            return self._audit(
                command=command,
                definition=definition,
                request=request,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code=model_result.reason_code or "insufficient_evidence",
                error_code=None,
                provider_call_status="completed",
                model_result=model_result,
                message_envelope=None,
            )
        envelope = MessageEnvelopeV1.from_model_result(
            message_id=uuid.uuid4(),
            run_id=command.run_id,
            agent_id=definition.agent_id,
            created_at=_as_utc(self._clock()),
            authorization_scope=current_scope,
            result=model_result,
        )
        return self._audit(
            command=command,
            definition=definition,
            request=request,
            model_ref=model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision=model_result.runtime_decision.value,
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            model_result=model_result,
            message_envelope=envelope,
        )

    def run(self, command: AgentRunCommand) -> AgentRuntimeOutcomeV1:
        """Compatibility alias for callers that name the operation ``run``."""

        return self.invoke(command)

    def _resolve_definition(self, definition_id: str) -> AgentDefinition | None:
        try:
            definition = self._definition_resolver.resolve(definition_id)
        except Exception:
            return None
        return definition if isinstance(definition, AgentDefinition) else None

    def _end_database_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()

    def _audit(
        self,
        *,
        command: AgentRunCommand,
        definition: AgentDefinition,
        request: ProviderRequestV1,
        model_ref: str,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        model_result: AgentModelResultV1 | None,
        message_envelope: MessageEnvelopeV1 | None,
    ) -> AgentRuntimeOutcomeV1:
        event = _runtime_event(
            command=command,
            definition=definition,
            request=request,
            model_ref=model_ref,
            outcome_kind=outcome_kind,
            status=status,
            final_decision=final_decision,
            reason_code=reason_code,
            error_code=error_code,
            model_result=model_result,
            message_envelope=message_envelope,
        )
        try:
            event_ref = self._timeline_append(event)
            if not _event_ref_is_valid(event_ref):
                raise ValueError("Timeline append returned an invalid ref.")
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
            message_envelope=message_envelope,
            event_ref=dict(event_ref),
            model_ref=model_ref,
            provider_call_status=provider_call_status,
            audit_status="appended",
        )


def _plant_record(plant: Plant) -> AgentInputRecordV1:
    return AgentInputRecordV1(
        record_type="plant",
        source_ref=f"plant:{plant.plant_id}",
        payload={"plant_id": str(plant.plant_id), "status": plant.status},
    )


def _check_in_record(check_in: DailyCheckIn) -> AgentInputRecordV1:
    return AgentInputRecordV1(
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


def _measurement_record(measurement: ManualMeasurement) -> AgentInputRecordV1:
    return AgentInputRecordV1(
        record_type="manual_measurement",
        source_ref=f"manual_measurement:{measurement.measurement_id}",
        payload={
            "measurement_id": str(measurement.measurement_id),
            "measured_at": _timestamp(measurement.measured_at),
            "recorded_at": _timestamp(measurement.recorded_at),
            "ph": format(measurement.ph, ".2f") if measurement.ph is not None else None,
            "ec_ms_cm": format(measurement.ec_ms_cm, ".3f")
            if measurement.ec_ms_cm is not None
            else None,
            "source_type": measurement.source_type,
            "trust_status": measurement.trust_status,
        },
    )


def _current_snapshot(
    *,
    plant: Plant,
    membership: FarmMembership,
    grant: PlantAccessGrant | None,
) -> PlantAccessSnapshot:
    grant_snapshot = None
    if grant is not None:
        grant_snapshot = PlantGrantSnapshot(
            grant_id=grant.grant_id,
            membership_id=grant.membership_id,
            farm_id=membership.farm_id,
            plant_id=grant.plant_id,
            status=grant.status,
            plant_approve_actions=grant.plant_approve_actions,
        )
    return PlantAccessSnapshot(
        plant=PlantSnapshot(
            plant_id=plant.plant_id,
            farm_id=plant.farm_id,
            status=plant.status,
        ),
        grant=grant_snapshot,
    )


def _validate_command(command: object) -> None:
    if (
        not isinstance(command, AgentRunCommand)
        or not isinstance(command.run_id, uuid.UUID)
        or command.run_id.version != 4
        or not isinstance(command.requested_at, datetime)
        or command.requested_at.tzinfo is None
        or not isinstance(command.agent_definition_id, str)
        or not command.agent_definition_id.strip()
        or not isinstance(command.actor_context, ActorContext)
        or not isinstance(command.plant_id, uuid.UUID)
    ):
        raise AgentRuntimeValidationError()


def _context_denied(run_id: uuid.UUID, reason_code: str) -> AgentRuntimeOutcomeV1:
    safe_reason = reason_code if reason_code in {"context_denied", "input_contract_violation"} else "context_denied"
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


def _executor_model_ref(executor: ModelExecutor | None) -> str | None:
    if executor is None:
        return None
    value = getattr(executor, "model_ref", None)
    return value if isinstance(value, str) and _MODEL_REF_RE.fullmatch(value) else None


def _execution_result(execution: object, *, expected_model_ref: str) -> object:
    if isinstance(execution, ModelExecution):
        return execution.result if execution.model_ref == expected_model_ref else None
    return execution if isinstance(execution, Mapping) else None


def _runtime_event(
    *,
    command: AgentRunCommand,
    definition: AgentDefinition,
    request: ProviderRequestV1,
    model_ref: str,
    outcome_kind: str,
    status: str,
    final_decision: str | None,
    reason_code: str,
    error_code: str | None,
    model_result: AgentModelResultV1 | None,
    message_envelope: MessageEnvelopeV1 | None,
) -> TimelineEvent:
    candidate_decision = model_result.runtime_decision.value if model_result else None
    candidate_claim = model_result.candidate_claim_type if model_result else None
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
            "agent_id": definition.agent_id,
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "candidate_decision": candidate_decision,
            "final_decision": final_decision,
            "outcome_status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "message_id": str(message_envelope.message_id)
            if message_envelope is not None
            else None,
            "candidate_claim_type": candidate_claim,
            "source_ref_count": len(request.source_refs),
        },
    )


def _event_ref_is_valid(value: object) -> bool:
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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AgentDefinitionResolver",
    "AgentInputAssembler",
    "AgentRunCommand",
    "AgentRuntimeService",
    "DatabaseAgentInputAssembler",
    "DatabaseRuntimeAuthorizationGuard",
    "InputAssemblyDenied",
    "ModelExecution",
    "ModelExecutor",
    "RuntimeAuthorizationGuard",
    "StaticAgentDefinitionResolver",
]
