"""Authorized FT-009 Vision Observation invocation over one accepted photo."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Protocol
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import Plant
from ..access_admin.permissions import OperationKind, PermissionSource, PlantStatus
from ..agent_runtime.contracts import (
    AgentModelResultV1,
    AgentRuntimeOutcomeV1,
    AgentRuntimeValidationError,
    CurrentAuthorizationScope,
    MessageEnvelopeV1,
    RuntimeDecision,
)
from ..agent_runtime.service import DatabaseRuntimeAuthorizationGuard, ModelExecution
from ..config import AppSettings
from ..photo_intake.models import PhotoCatalogItem
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .contracts import (
    MAX_VISION_MEDIA_BYTES,
    VISION_OBSERVATION_DEFINITION_V1,
    VisionInputRecordV1,
    VisionMediaV1,
    VisionObservationModelResultV1,
    VisionObservationOutcomeV1,
    VisionObservationValidationError,
    VisionProviderRequestV1,
    VisionStateCandidateV1,
)


_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


class VisionInputDenied(RuntimeError):
    def __init__(self, reason_code: str = "input_contract_violation") -> None:
        self.reason_code = reason_code
        super().__init__("Vision input context is unavailable.")


@dataclass(frozen=True, slots=True)
class VisionObservationCommand:
    run_id: uuid.UUID
    requested_at: datetime
    actor_context: ActorContext
    plant_id: uuid.UUID
    photo_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class AssembledVisionInputV1:
    request: VisionProviderRequestV1
    media: VisionMediaV1
    observed_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.request, VisionProviderRequestV1)
            or not isinstance(self.media, VisionMediaV1)
            or self.request.source_refs[1] != self.media.source_ref
            or not _is_utc(self.observed_at)
        ):
            raise VisionObservationValidationError()


class VisionInputAssembler(Protocol):
    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> AssembledVisionInputV1: ...


class VisionModelExecutor(Protocol):
    model_ref: str

    def execute(
        self,
        request: VisionProviderRequestV1,
        media: VisionMediaV1,
    ) -> ModelExecution | Mapping[str, object]: ...


class DatabaseVisionInputAssembler:
    """Load current catalog authority and freshly verify the original bytes."""

    def __init__(
        self,
        session: Session,
        *,
        settings: AppSettings | None = None,
    ) -> None:
        self._session = session
        self._artifact_root = Path(
            (settings or AppSettings.from_env()).local_artifact_root
        )

    def assemble(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> AssembledVisionInputV1:
        if (
            not isinstance(actor, ActorContext)
            or not isinstance(plant_id, uuid.UUID)
            or not isinstance(photo_id, uuid.UUID)
        ):
            raise VisionInputDenied()
        try:
            permission = actor.resolve_plant_permission(
                plant_id,
                OperationKind.NORMAL_READ,
            )
        except Exception:
            raise VisionInputDenied() from None
        if (
            permission.plant_status is not PlantStatus.ACTIVE
            or not permission.can_read
            or permission.source is PermissionSource.DENIED
        ):
            raise VisionInputDenied()
        plant = self._session.scalar(
            select(Plant)
            .where(Plant.farm_id == actor.farm_id, Plant.plant_id == plant_id)
            .execution_options(populate_existing=True)
        )
        photo = self._session.scalar(
            select(PhotoCatalogItem)
            .where(
                PhotoCatalogItem.farm_id == actor.farm_id,
                PhotoCatalogItem.plant_id == plant_id,
                PhotoCatalogItem.photo_id == photo_id,
            )
            .execution_options(populate_existing=True)
        )
        if plant is None or plant.status != "active" or photo is None:
            raise VisionInputDenied()
        try:
            content = self._read_verified_original(photo)
            plant_record = VisionInputRecordV1(
                record_type="plant",
                source_ref=f"plant:{plant_id}",
                payload={"plant_id": str(plant_id), "status": "active"},
            )
            photo_record = VisionInputRecordV1(
                record_type="photo",
                source_ref=f"photo:{photo_id}",
                payload={
                    "photo_id": str(photo_id),
                    "plant_id": str(plant_id),
                    "photo_type": photo.photo_type,
                    "captured_at": _timestamp(photo.captured_at),
                    "content_type": photo.content_type,
                    "size_bytes": photo.size_bytes,
                    "sha256": photo.sha256,
                    "local_only": True,
                },
            )
            request = VisionProviderRequestV1(
                records=(plant_record, photo_record),
                source_refs=(plant_record.source_ref, photo_record.source_ref),
            )
            media = VisionMediaV1(
                source_ref=photo_record.source_ref,
                content_type=photo.content_type,
                sha256=photo.sha256,
                content=content,
            )
            return AssembledVisionInputV1(
                request=request,
                media=media,
                observed_at=_as_utc(photo.captured_at),
            )
        except (OSError, ValueError, TypeError, VisionObservationValidationError):
            raise VisionInputDenied() from None

    def _read_verified_original(self, photo: PhotoCatalogItem) -> bytes:
        if (
            photo.content_type not in {"image/jpeg", "image/png", "image/webp"}
            or isinstance(photo.size_bytes, bool)
            or not isinstance(photo.size_bytes, int)
            or not 0 < photo.size_bytes <= MAX_VISION_MEDIA_BYTES
            or not isinstance(photo.sha256, str)
            or len(photo.sha256) != 64
        ):
            raise VisionInputDenied()
        ref = photo.original_file_ref
        if not isinstance(ref, str) or not ref:
            raise VisionInputDenied()
        pure = PurePosixPath(ref)
        if pure.is_absolute() or ".." in pure.parts:
            raise VisionInputDenied()
        root = self._artifact_root.resolve()
        path = (root / Path(*pure.parts)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise VisionInputDenied()
        expected_extension = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }[photo.content_type]
        expected_ref = (
            f"plants/{photo.plant_id}/photos/{photo.photo_id}/"
            f"original.{expected_extension}"
        )
        if ref != expected_ref:
            raise VisionInputDenied()
        content = path.read_bytes()
        if (
            len(content) != photo.size_bytes
            or hashlib.sha256(content).hexdigest() != photo.sha256
        ):
            raise VisionInputDenied()
        return content


class _VisionMessageEnvelopeV1(MessageEnvelopeV1):
    """The standard envelope shape with the registered Vision photo ref union."""

    __slots__ = ()

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.message_id)
            or not _uuid4(self.run_id)
            or self.agent_id != "vision_observation"
            or not _is_utc(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision not in {RuntimeDecision.SPEAK, RuntimeDecision.CLARIFY}
            or self.candidate_claim_type
            not in {"observation", "hypothesis", "clarification"}
            or not isinstance(self.candidate_output, str)
            or self.candidate_output != self.candidate_output.strip()
            or not 1 <= len(self.candidate_output) <= 2000
            or not 1 <= len(self.source_refs) <= 2
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not _vision_ref(item) for item in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()
        if self.runtime_decision is RuntimeDecision.SPEAK:
            if (
                self.candidate_claim_type not in {"observation", "hypothesis"}
                or isinstance(self.confidence, bool)
                or not isinstance(self.confidence, int | float)
                or not 0 <= float(self.confidence) <= 1
            ):
                raise AgentRuntimeValidationError()
        elif self.candidate_claim_type != "clarification" or self.confidence is not None:
            raise AgentRuntimeValidationError()


TimelineAppender = Callable[[TimelineEvent], Mapping[str, object]]
Clock = Callable[[], datetime]


class VisionObservationService:
    """Run one Vision observation without persistence or publication effects."""

    def __init__(
        self,
        session: Session,
        *,
        model_executor: VisionModelExecutor | None,
        input_assembler: VisionInputAssembler | None = None,
        authorization_guard: DatabaseRuntimeAuthorizationGuard | None = None,
        timeline_append: TimelineAppender | None = None,
        settings: AppSettings | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._model_executor = model_executor
        self._clock = clock or _utc_now
        self._input_assembler = input_assembler or DatabaseVisionInputAssembler(
            session,
            settings=settings,
        )
        self._authorization_guard = authorization_guard or DatabaseRuntimeAuthorizationGuard(
            session,
            clock=self._clock,
        )
        self._timeline_append = timeline_append or TimelineJsonlAppender(settings)

    def invoke(self, command: VisionObservationCommand) -> VisionObservationOutcomeV1:
        _validate_command(command)
        try:
            assembled = self._input_assembler.assemble(
                command.actor_context,
                plant_id=command.plant_id,
                photo_id=command.photo_id,
            )
        except VisionInputDenied as denied:
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
            execution = executor.execute(assembled.request, assembled.media)
        except Exception:
            return self._audit(
                command=command,
                assembled=assembled,
                model_ref=model_ref,
                outcome_kind="provider_failed",
                status="failed",
                final_decision=None,
                reason_code="provider_failed",
                error_code="AGENT_PROVIDER_FAILED",
                provider_call_status="failed",
                model_result=None,
                envelope=None,
                candidate=None,
            )
        raw_result = _execution_result(execution, expected_model_ref=model_ref)
        try:
            result = VisionObservationModelResultV1.from_untrusted(
                raw_result,
                request_source_refs=assembled.request.source_refs,
            )
            envelope_result = _as_envelope_result(result)
        except (VisionObservationValidationError, AgentRuntimeValidationError):
            return self._audit(
                command=command,
                assembled=assembled,
                model_ref=model_ref,
                outcome_kind="output_invalid",
                status="blocked",
                final_decision=None,
                reason_code="output_invalid",
                error_code="AGENT_OUTPUT_INVALID",
                provider_call_status="completed",
                model_result=None,
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
        self._end_transaction()
        if scope is None:
            return self._audit(
                command=command,
                assembled=assembled,
                model_ref=model_ref,
                outcome_kind="publication_guard_denied",
                status="blocked",
                final_decision=None,
                reason_code="publication_guard_denied",
                error_code="AGENT_PUBLICATION_BLOCKED",
                provider_call_status="completed",
                model_result=result,
                envelope=None,
                candidate=None,
            )
        if result.runtime_decision == "silent":
            return self._audit(
                command=command,
                assembled=assembled,
                model_ref=model_ref,
                outcome_kind="model_silent",
                status="silent",
                final_decision="silent",
                reason_code="no_material_output",
                error_code=None,
                provider_call_status="completed",
                model_result=result,
                envelope=None,
                candidate=None,
            )

        message_id = uuid.uuid4()
        envelope = _VisionMessageEnvelopeV1.from_model_result(
            message_id=message_id,
            run_id=command.run_id,
            agent_id="vision_observation",
            created_at=_as_utc(self._clock()),
            authorization_scope=scope,
            result=envelope_result,
        )
        candidate = None
        if result.runtime_decision == "speak":
            assert result.observation_key is not None
            assert result.polarity is not None
            assert result.severity is not None
            assert result.summary is not None
            assert result.confidence is not None
            candidate = VisionStateCandidateV1(
                run_id=command.run_id,
                message_id=message_id,
                observation_key=result.observation_key,
                polarity=result.polarity,
                severity=result.severity,
                summary=result.summary,
                confidence=result.confidence,
                source_refs=result.source_refs,
                observed_at=assembled.observed_at,
            )
        return self._audit(
            command=command,
            assembled=assembled,
            model_ref=model_ref,
            outcome_kind="envelope_ready",
            status="envelope_ready",
            final_decision=result.runtime_decision,
            reason_code="envelope_ready",
            error_code=None,
            provider_call_status="completed",
            model_result=result,
            envelope=envelope,
            candidate=candidate,
        )

    def run(self, command: VisionObservationCommand) -> VisionObservationOutcomeV1:
        return self.invoke(command)

    def _end_transaction(self) -> None:
        if self._session.in_transaction():
            self._session.rollback()

    def _audit(
        self,
        *,
        command: VisionObservationCommand,
        assembled: AssembledVisionInputV1,
        model_ref: str,
        outcome_kind: str,
        status: str,
        final_decision: str | None,
        reason_code: str,
        error_code: str | None,
        provider_call_status: str,
        model_result: VisionObservationModelResultV1 | None,
        envelope: MessageEnvelopeV1 | None,
        candidate: VisionStateCandidateV1 | None,
    ) -> VisionObservationOutcomeV1:
        event = _runtime_event(
            command=command,
            model_ref=model_ref,
            outcome_kind=outcome_kind,
            status=status,
            final_decision=final_decision,
            reason_code=reason_code,
            error_code=error_code,
            model_result=model_result,
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
        runtime = AgentRuntimeOutcomeV1(
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
        return VisionObservationOutcomeV1(runtime_outcome=runtime, state_candidate=candidate)


def _as_envelope_result(result: VisionObservationModelResultV1) -> AgentModelResultV1:
    if result.runtime_decision == "speak":
        claim = (
            "observation"
            if result.polarity in {"present", "absent"}
            and result.confidence is not None
            and result.confidence >= 0.50
            else "hypothesis"
        )
        payload = {
            "schema_version": 1,
            "runtime_decision": "speak",
            "candidate_claim_type": claim,
            "candidate_output": result.summary,
            "confidence": result.confidence,
            "source_refs": list(result.source_refs),
            "reason_code": None,
        }
    elif result.runtime_decision == "clarify":
        payload = {
            "schema_version": 1,
            "runtime_decision": "clarify",
            "candidate_claim_type": "clarification",
            "candidate_output": result.summary,
            "confidence": None,
            "source_refs": list(result.source_refs),
            "reason_code": None,
        }
    else:
        payload = {
            "schema_version": 1,
            "runtime_decision": "silent",
            "candidate_claim_type": None,
            "candidate_output": None,
            "confidence": None,
            "source_refs": [],
            "reason_code": "no_material_output",
        }
    return AgentModelResultV1.from_untrusted(
        payload,
        request_source_refs=(
            # Generic parsing checks subset/order but does not narrow registered
            # competence-specific source kinds.
            *result.source_refs,
        ),
    )


def _runtime_event(
    *,
    command: VisionObservationCommand,
    model_ref: str,
    outcome_kind: str,
    status: str,
    final_decision: str | None,
    reason_code: str,
    error_code: str | None,
    model_result: VisionObservationModelResultV1 | None,
    envelope: MessageEnvelopeV1 | None,
) -> TimelineEvent:
    candidate_decision = model_result.runtime_decision if model_result else None
    candidate_claim = None
    if model_result is not None and model_result.runtime_decision == "speak":
        candidate_claim = (
            "observation"
            if model_result.polarity in {"present", "absent"}
            and model_result.confidence is not None
            and model_result.confidence >= 0.50
            else "hypothesis"
        )
    elif model_result is not None and model_result.runtime_decision == "clarify":
        candidate_claim = "clarification"
    # The shared FT-007 Timeline event v1 has a closed generic input-ref union.
    # Record the active Plant ref only; the Vision photo ref stays in the strict
    # request/envelope/candidate and never becomes a path or binary audit value.
    input_refs = [f"plant:{command.plant_id}"]
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
        source_refs={"input_refs": input_refs},
        payload_summary={
            "agent_id": "vision_observation",
            "model_ref": model_ref,
            "outcome_kind": outcome_kind,
            "candidate_decision": candidate_decision,
            "final_decision": final_decision,
            "outcome_status": status,
            "reason_code": reason_code,
            "error_code": error_code,
            "message_id": str(envelope.message_id) if envelope is not None else None,
            "candidate_claim_type": candidate_claim,
            "source_ref_count": len(input_refs),
        },
    )


def _validate_command(command: object) -> None:
    if (
        not isinstance(command, VisionObservationCommand)
        or not _uuid4(command.run_id)
        or not _is_utc(command.requested_at)
        or not isinstance(command.actor_context, ActorContext)
        or not isinstance(command.plant_id, uuid.UUID)
        or not isinstance(command.photo_id, uuid.UUID)
    ):
        raise VisionObservationValidationError()


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


def _wrap(runtime: AgentRuntimeOutcomeV1) -> VisionObservationOutcomeV1:
    return VisionObservationOutcomeV1(runtime_outcome=runtime, state_candidate=None)


def _event_ref_valid(value: object) -> bool:
    if not isinstance(value, Mapping) or value.get("event_type") != "agent_runtime_decided":
        return False
    try:
        uuid.UUID(str(value["timeline_event_id"]))
    except (KeyError, ValueError, TypeError):
        return False
    return (
        isinstance(value.get("timeline_ref"), str)
        and str(value["timeline_ref"]).startswith("timeline.jsonl#")
        and isinstance(value.get("created_at"), str)
    )


def _vision_ref(value: object) -> bool:
    if not isinstance(value, str) or ":" not in value:
        return False
    kind, identifier = value.split(":", 1)
    if kind not in {"plant", "photo"}:
        return False
    try:
        return str(uuid.UUID(identifier)) == identifier
    except (ValueError, TypeError, AttributeError):
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
    "AssembledVisionInputV1",
    "DatabaseVisionInputAssembler",
    "VisionInputAssembler",
    "VisionInputDenied",
    "VisionModelExecutor",
    "VisionObservationCommand",
    "VisionObservationService",
]
