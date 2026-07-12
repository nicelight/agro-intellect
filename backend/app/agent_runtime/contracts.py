"""Strict project-owned value objects for the FT-007 runtime boundary.

The module deliberately uses small immutable Python value objects instead of
passing provider dictionaries through the service.  Provider output is
untrusted until ``AgentModelResultV1.from_untrusted`` accepts the complete
closed schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import math
import re
from types import MappingProxyType
from typing import Any
import uuid


_AGENT_ID_RE = re.compile(r"[a-z][a-z0-9_]{2,63}\Z")
_CLASSIFIER_VERSION_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")
_SOURCE_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[0-9a-f-]{36}\Z")

_CANDIDATE_CLAIMS = frozenset(
    {
        "observation",
        "hypothesis",
        "recommendation",
        "clarification",
        "task_request",
        "safety_block",
        "team_signal",
    }
)
_SPEAK_CLAIMS = frozenset(
    {"observation", "hypothesis", "recommendation", "task_request", "team_signal"}
)
_ESCALATE_CLAIMS = frozenset({"safety_block", "team_signal"})
_SILENCE_REASONS = frozenset({"no_material_output", "insufficient_evidence"})
_OUTCOME_KINDS = frozenset(
    {
        "envelope_ready",
        "model_silent",
        "context_denied",
        "runtime_not_configured",
        "provider_failed",
        "output_invalid",
        "publication_guard_denied",
        "audit_failed",
    }
)


class AgentRuntimeValidationError(ValueError):
    """A closed runtime contract was malformed or incompatible."""

    def __init__(self, message: str = "Agent Runtime contract validation failed.") -> None:
        super().__init__(message)


class RuntimeDecision(StrEnum):
    SPEAK = "speak"
    SILENT = "silent"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Project-owned immutable definition usable by the W1 test seam."""

    agent_id: str
    competence: str
    instructions: str
    allowed_candidate_claim_types: tuple[str, ...]
    output_schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.agent_id, str)
            or _AGENT_ID_RE.fullmatch(self.agent_id) is None
            or not _is_normalized_text(self.competence, minimum=1, maximum=2000)
            or not _is_normalized_text(self.instructions, minimum=1, maximum=10000)
            or self.output_schema_version != 1
        ):
            raise AgentRuntimeValidationError()
        try:
            claims = tuple(self.allowed_candidate_claim_types)
        except TypeError:
            raise AgentRuntimeValidationError() from None
        if (
            not claims
            or len(claims) != len(set(claims))
            or not set(claims).issubset(_CANDIDATE_CLAIMS)
        ):
            raise AgentRuntimeValidationError()
        object.__setattr__(self, "allowed_candidate_claim_types", claims)

    def as_provider_value(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "competence": self.competence,
            "instructions": self.instructions,
            "allowed_candidate_claim_types": list(self.allowed_candidate_claim_types),
            "output_schema": {
                "name": "AgentModelResultV1",
                "schema_version": 1,
                "strict": True,
            },
        }


@dataclass(frozen=True, slots=True)
class AgentInputRecordV1:
    record_type: str
    source_ref: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.record_type not in {
            "plant",
            "daily_checkin",
            "manual_measurement",
        } or not isinstance(self.payload, Mapping):
            raise AgentRuntimeValidationError()
        payload = dict(self.payload)
        _validate_input_record(
            record_type=self.record_type,
            source_ref=self.source_ref,
            payload=payload,
        )
        object.__setattr__(self, "payload", MappingProxyType(payload))

    def as_provider_value(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "source_ref": self.source_ref,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class ProviderRequestV1:
    agent_definition: AgentDefinition
    records: tuple[AgentInputRecordV1, ...]
    source_refs: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        records = tuple(self.records)
        refs = tuple(self.source_refs)
        if (
            self.schema_version != 1
            or not isinstance(self.agent_definition, AgentDefinition)
            or not 1 <= len(records) <= 4
            or len(refs) != len(records)
            or len(refs) != len(set(refs))
            or any(not isinstance(record, AgentInputRecordV1) for record in records)
            or refs != tuple(record.source_ref for record in records)
        ):
            raise AgentRuntimeValidationError()
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "source_refs", refs)

    def as_provider_payload(self) -> dict[str, object]:
        """Return the sole outbound provider payload with no service metadata."""

        return {
            "schema_version": 1,
            "agent_definition": self.agent_definition.as_provider_value(),
            "records": [record.as_provider_value() for record in self.records],
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class AgentModelResultV1:
    runtime_decision: RuntimeDecision
    candidate_claim_type: str | None
    candidate_output: str | None
    confidence: float | None
    source_refs: tuple[str, ...]
    reason_code: str | None
    schema_version: int = 1

    @classmethod
    def from_untrusted(
        cls,
        value: object,
        *,
        request_source_refs: tuple[str, ...],
    ) -> "AgentModelResultV1":
        fields = _exact_mapping(
            value,
            {
                "schema_version",
                "runtime_decision",
                "candidate_claim_type",
                "candidate_output",
                "confidence",
                "source_refs",
                "reason_code",
            },
        )
        if fields["schema_version"] != 1:
            raise AgentRuntimeValidationError()
        try:
            decision = RuntimeDecision(fields["runtime_decision"])
        except (TypeError, ValueError):
            raise AgentRuntimeValidationError() from None
        refs = _model_refs(fields["source_refs"], request_source_refs)
        claim = fields["candidate_claim_type"]
        output = fields["candidate_output"]
        confidence = fields["confidence"]
        reason = fields["reason_code"]

        if decision is RuntimeDecision.SILENT:
            if (
                claim is not None
                or output is not None
                or confidence is not None
                or refs
                or reason not in _SILENCE_REASONS
            ):
                raise AgentRuntimeValidationError()
            return cls(
                runtime_decision=decision,
                candidate_claim_type=None,
                candidate_output=None,
                confidence=None,
                source_refs=(),
                reason_code=str(reason),
            )

        if reason is not None or not isinstance(claim, str) or claim not in _CANDIDATE_CLAIMS:
            raise AgentRuntimeValidationError()
        if not _is_normalized_text(output, minimum=1, maximum=2000) or not refs:
            raise AgentRuntimeValidationError()
        if decision is RuntimeDecision.SPEAK:
            if claim not in _SPEAK_CLAIMS:
                raise AgentRuntimeValidationError()
            if claim == "team_signal":
                normalized_confidence = _optional_confidence(confidence)
            else:
                normalized_confidence = _required_confidence(confidence)
        elif decision is RuntimeDecision.CLARIFY:
            if claim != "clarification" or confidence is not None:
                raise AgentRuntimeValidationError()
            normalized_confidence = None
        elif decision is RuntimeDecision.ESCALATE:
            if claim not in _ESCALATE_CLAIMS or confidence is not None:
                raise AgentRuntimeValidationError()
            normalized_confidence = None
        else:  # Defensive future-proofing for a future enum member.
            raise AgentRuntimeValidationError()
        return cls(
            runtime_decision=decision,
            candidate_claim_type=claim,
            candidate_output=output,
            confidence=normalized_confidence,
            source_refs=refs,
            reason_code=None,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "runtime_decision": self.runtime_decision.value,
            "candidate_claim_type": self.candidate_claim_type,
            "candidate_output": self.candidate_output,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class CurrentAuthorizationScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    role_preset: str
    operation_kind: str
    permission_source: str
    grant_id: uuid.UUID | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.role_preset not in {"boss", "engineer", "consultant"}
            or self.operation_kind != "normal_read"
            or self.permission_source not in {"boss_role", "plant_access_grant"}
            or (
                self.permission_source == "boss_role" and self.grant_id is not None
            )
            or (
                self.permission_source == "plant_access_grant"
                and not isinstance(self.grant_id, uuid.UUID)
            )
        ):
            raise AgentRuntimeValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "farm_id": _uuid_text(self.farm_id),
            "plant_id": _uuid_text(self.plant_id),
            "role_preset": self.role_preset,
            "operation_kind": "normal_read",
            "permission_source": self.permission_source,
            "grant_id": _uuid_text(self.grant_id) if self.grant_id else None,
        }


@dataclass(frozen=True, slots=True)
class MessageEnvelopeV1:
    message_id: uuid.UUID
    run_id: uuid.UUID
    agent_id: str
    created_at: datetime
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    runtime_decision: RuntimeDecision
    candidate_claim_type: str
    confidence: float | None
    source_refs: tuple[str, ...]
    candidate_output: str
    authorization_scope: CurrentAuthorizationScope
    schema_version: int = 1
    publication_state: str = "pending_classification"
    consumable_by_agents: bool = False

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _is_uuid4(self.message_id)
            or not _is_uuid4(self.run_id)
            or _AGENT_ID_RE.fullmatch(self.agent_id) is None
            or not _is_utc_datetime(self.created_at)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.runtime_decision is RuntimeDecision.SILENT
            or self.candidate_claim_type not in _CANDIDATE_CLAIMS
            or not _is_normalized_text(self.candidate_output, minimum=1, maximum=2000)
            or not 1 <= len(self.source_refs) <= 4
            or len(self.source_refs) != len(set(self.source_refs))
            or any(not _safe_input_ref(item) for item in self.source_refs)
            or self.publication_state != "pending_classification"
            or self.consumable_by_agents is not False
            or not isinstance(self.authorization_scope, CurrentAuthorizationScope)
            or self.authorization_scope.farm_id != self.farm_id
            or self.authorization_scope.plant_id != self.plant_id
        ):
            raise AgentRuntimeValidationError()
        _validate_decision_claim_confidence(
            self.runtime_decision,
            self.candidate_claim_type,
            self.confidence,
        )

    @classmethod
    def from_model_result(
        cls,
        *,
        message_id: uuid.UUID,
        run_id: uuid.UUID,
        agent_id: str,
        created_at: datetime,
        authorization_scope: CurrentAuthorizationScope,
        result: AgentModelResultV1,
    ) -> "MessageEnvelopeV1":
        if (
            result.runtime_decision is RuntimeDecision.SILENT
            or result.candidate_claim_type is None
            or result.candidate_output is None
        ):
            raise AgentRuntimeValidationError()
        return cls(
            message_id=message_id,
            run_id=run_id,
            agent_id=agent_id,
            created_at=created_at,
            farm_id=authorization_scope.farm_id,
            plant_id=authorization_scope.plant_id,
            runtime_decision=result.runtime_decision,
            candidate_claim_type=result.candidate_claim_type,
            confidence=result.confidence,
            source_refs=result.source_refs,
            candidate_output=result.candidate_output,
            authorization_scope=authorization_scope,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "message_id": _uuid_text(self.message_id),
            "run_id": _uuid_text(self.run_id),
            "agent_id": self.agent_id,
            "created_at": _timestamp_text(self.created_at),
            "farm_id": _uuid_text(self.farm_id),
            "plant_id": _uuid_text(self.plant_id),
            "runtime_decision": self.runtime_decision.value,
            "candidate_claim_type": self.candidate_claim_type,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "candidate_output": self.candidate_output,
            "publication_state": "pending_classification",
            "consumable_by_agents": False,
            "authorization_scope": self.authorization_scope.as_value(),
        }


@dataclass(frozen=True, slots=True)
class SafetyClassificationResultV1:
    message_id: uuid.UUID
    classifier_version: str
    classification: str
    safe_task_kind: str | None
    reason_code: str
    schema_version: int = 1

    @classmethod
    def from_untrusted(cls, value: object) -> "SafetyClassificationResultV1":
        fields = _exact_mapping(
            value,
            {
                "schema_version",
                "message_id",
                "classifier_version",
                "classification",
                "safe_task_kind",
                "reason_code",
            },
        )
        message_id = _parse_canonical_uuid(fields["message_id"])
        classifier_version = fields["classifier_version"]
        classification = fields["classification"]
        task_kind = fields["safe_task_kind"]
        reason = fields["reason_code"]
        if (
            fields["schema_version"] != 1
            or not isinstance(classifier_version, str)
            or _CLASSIFIER_VERSION_RE.fullmatch(classifier_version) is None
            or not isinstance(classification, str)
            or not isinstance(reason, str)
        ):
            raise AgentRuntimeValidationError()
        matrix = {
            "safe_information": (None, "non_physical_information"),
            "safe_task_request": (
                {"check", "measurement", "follow_up"},
                {
                    "check": "safe_check_request",
                    "measurement": "safe_measurement_request",
                    "follow_up": "safe_follow_up_request",
                },
            ),
            "physical_action": (None, "physical_action_detected"),
            "blocked_uncertain": (None, "classification_uncertain"),
        }
        if classification not in matrix:
            raise AgentRuntimeValidationError()
        expected_task, expected_reason = matrix[classification]
        if isinstance(expected_task, set):
            if task_kind not in expected_task or reason != expected_reason[task_kind]:
                raise AgentRuntimeValidationError()
        elif task_kind is not expected_task or reason != expected_reason:
            raise AgentRuntimeValidationError()
        return cls(
            message_id=message_id,
            classifier_version=classifier_version,
            classification=classification,
            safe_task_kind=task_kind,
            reason_code=reason,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "message_id": _uuid_text(self.message_id),
            "classifier_version": self.classifier_version,
            "classification": self.classification,
            "safe_task_kind": self.safe_task_kind,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class AgentRuntimeOutcomeV1:
    run_id: uuid.UUID
    outcome_kind: str
    status: str
    final_decision: str | None
    reason_code: str
    error_code: str | None
    message_envelope: MessageEnvelopeV1 | None
    event_ref: Mapping[str, object] | None
    model_ref: str | None
    provider_call_status: str
    audit_status: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1 or not _is_uuid4(self.run_id):
            raise AgentRuntimeValidationError()
        if self.model_ref is not None and (
            not isinstance(self.model_ref, str)
            or _MODEL_REF_RE.fullmatch(self.model_ref) is None
        ):
            raise AgentRuntimeValidationError()
        _validate_outcome_matrix(self)

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": _uuid_text(self.run_id),
            "outcome_kind": self.outcome_kind,
            "status": self.status,
            "final_decision": self.final_decision,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
            "message_envelope": self.message_envelope.as_value()
            if self.message_envelope is not None
            else None,
            "event_ref": dict(self.event_ref) if self.event_ref is not None else None,
            "model_ref": self.model_ref,
            "provider_call_status": self.provider_call_status,
            "audit_status": self.audit_status,
        }


def _validate_input_record(
    *, record_type: str, source_ref: object, payload: Mapping[str, object]
) -> None:
    if not isinstance(source_ref, str):
        raise AgentRuntimeValidationError()
    if record_type == "plant":
        _expect_keys(payload, {"plant_id", "status"})
        plant_id = _parse_canonical_uuid(payload["plant_id"])
        if source_ref != f"plant:{plant_id}" or payload["status"] != "active":
            raise AgentRuntimeValidationError()
        return
    if record_type == "daily_checkin":
        _expect_keys(
            payload,
            {
                "check_in_id",
                "observed_at",
                "recorded_at",
                "observation_state",
                "observation_text",
            },
        )
        check_in_id = _parse_canonical_uuid(payload["check_in_id"])
        if (
            source_ref != f"daily_checkin:{check_in_id}"
            or not _is_utc_rfc3339(payload["observed_at"])
            or not _is_utc_rfc3339(payload["recorded_at"])
            or payload["observation_state"]
            not in {"observed", "no_observation_provided"}
        ):
            raise AgentRuntimeValidationError()
        if payload["observation_state"] == "observed":
            if not _is_normalized_text(payload["observation_text"], minimum=1, maximum=2000):
                raise AgentRuntimeValidationError()
        elif payload["observation_text"] is not None:
            raise AgentRuntimeValidationError()
        return
    _expect_keys(
        payload,
        {
            "measurement_id",
            "measured_at",
            "recorded_at",
            "ph",
            "ec_ms_cm",
            "source_type",
            "trust_status",
        },
    )
    measurement_id = _parse_canonical_uuid(payload["measurement_id"])
    if (
        source_ref != f"manual_measurement:{measurement_id}"
        or not _is_utc_rfc3339(payload["measured_at"])
        or not _is_utc_rfc3339(payload["recorded_at"])
        or payload["source_type"] != "manual_user"
        or payload["trust_status"] != "confirmed"
        or not _is_fixed_decimal_or_none(
            payload["ph"],
            places=2,
            minimum=Decimal("0"),
            maximum=Decimal("14"),
        )
        or not _is_fixed_decimal_or_none(
            payload["ec_ms_cm"],
            places=3,
            minimum=Decimal("0"),
            maximum=None,
        )
        or (payload["ph"] is None and payload["ec_ms_cm"] is None)
    ):
        raise AgentRuntimeValidationError()


def _exact_mapping(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise AgentRuntimeValidationError()
    result = dict(value)
    _expect_keys(result, keys)
    return result


def _expect_keys(value: Mapping[str, object], keys: set[str]) -> None:
    if set(value.keys()) != keys:
        raise AgentRuntimeValidationError()


def _model_refs(value: object, request_source_refs: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AgentRuntimeValidationError()
    refs = tuple(value)
    if len(refs) > 4 or len(refs) != len(set(refs)):
        raise AgentRuntimeValidationError()
    ordered = [item for item in request_source_refs if item in refs]
    if refs != tuple(ordered):
        raise AgentRuntimeValidationError()
    return refs


def _optional_confidence(value: object) -> float | None:
    return None if value is None else _required_confidence(value)


def _required_confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise AgentRuntimeValidationError()
    normalized = float(value)
    if not math.isfinite(normalized) or not 0 <= normalized <= 1:
        raise AgentRuntimeValidationError()
    return normalized


def _validate_decision_claim_confidence(
    decision: RuntimeDecision,
    claim: str,
    confidence: float | None,
) -> None:
    if decision is RuntimeDecision.SPEAK:
        if claim not in _SPEAK_CLAIMS:
            raise AgentRuntimeValidationError()
        if claim == "team_signal":
            _optional_confidence(confidence)
        else:
            _required_confidence(confidence)
    elif decision is RuntimeDecision.CLARIFY:
        if claim != "clarification" or confidence is not None:
            raise AgentRuntimeValidationError()
    elif decision is RuntimeDecision.ESCALATE:
        if claim not in _ESCALATE_CLAIMS or confidence is not None:
            raise AgentRuntimeValidationError()
    else:
        raise AgentRuntimeValidationError()


def _validate_outcome_matrix(outcome: AgentRuntimeOutcomeV1) -> None:
    kind = outcome.outcome_kind
    if kind not in _OUTCOME_KINDS:
        raise AgentRuntimeValidationError()
    has_envelope = outcome.message_envelope is not None
    has_event = _is_event_ref(outcome.event_ref)
    common_no_provider = (
        outcome.model_ref is None
        and outcome.provider_call_status == "not_attempted"
        and outcome.audit_status == "not_attempted"
        and not has_envelope
        and not has_event
    )
    if kind == "context_denied":
        valid = (
            common_no_provider
            and outcome.status == "blocked"
            and outcome.final_decision is None
            and outcome.reason_code in {"context_denied", "input_contract_violation"}
            and outcome.error_code == "AGENT_CONTEXT_DENIED"
        )
    elif kind == "runtime_not_configured":
        valid = (
            common_no_provider
            and outcome.status == "failed"
            and outcome.final_decision is None
            and outcome.reason_code == "runtime_not_configured"
            and outcome.error_code == "AGENT_RUNTIME_NOT_CONFIGURED"
        )
    elif kind == "envelope_ready":
        valid = (
            has_envelope
            and has_event
            and outcome.status == "envelope_ready"
            and outcome.final_decision in {"speak", "clarify", "escalate"}
            and outcome.message_envelope is not None
            and outcome.message_envelope.runtime_decision.value == outcome.final_decision
            and outcome.reason_code == "envelope_ready"
            and outcome.error_code is None
            and outcome.model_ref is not None
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
        )
    elif kind == "model_silent":
        valid = (
            not has_envelope
            and has_event
            and outcome.status == "silent"
            and outcome.final_decision == "silent"
            and outcome.reason_code in _SILENCE_REASONS
            and outcome.error_code is None
            and outcome.model_ref is not None
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
        )
    elif kind == "provider_failed":
        valid = (
            not has_envelope
            and has_event
            and outcome.status == "failed"
            and outcome.final_decision is None
            and outcome.reason_code == "provider_failed"
            and outcome.error_code == "AGENT_PROVIDER_FAILED"
            and outcome.model_ref is not None
            and outcome.provider_call_status == "failed"
            and outcome.audit_status == "appended"
        )
    elif kind == "output_invalid":
        valid = (
            not has_envelope
            and has_event
            and outcome.status == "blocked"
            and outcome.final_decision is None
            and outcome.reason_code == "output_invalid"
            and outcome.error_code == "AGENT_OUTPUT_INVALID"
            and outcome.model_ref is not None
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
        )
    elif kind == "publication_guard_denied":
        valid = (
            not has_envelope
            and has_event
            and outcome.status == "blocked"
            and outcome.final_decision is None
            and outcome.reason_code == "publication_guard_denied"
            and outcome.error_code == "AGENT_PUBLICATION_BLOCKED"
            and outcome.model_ref is not None
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
        )
    else:  # audit_failed
        valid = (
            not has_envelope
            and not has_event
            and outcome.status == "failed"
            and outcome.final_decision is None
            and outcome.reason_code == "audit_failed"
            and outcome.error_code == "AGENT_AUDIT_FAILED"
            and outcome.model_ref is not None
            and outcome.provider_call_status in {"completed", "failed"}
            and outcome.audit_status == "failed"
        )
    if not valid:
        raise AgentRuntimeValidationError()


def _is_event_ref(value: object) -> bool:
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


def _parse_canonical_uuid(value: object) -> uuid.UUID:
    if not isinstance(value, str):
        raise AgentRuntimeValidationError()
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise AgentRuntimeValidationError() from None
    if str(parsed) != value:
        raise AgentRuntimeValidationError()
    return parsed


def _uuid_text(value: uuid.UUID) -> str:
    return str(value)


def _is_uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _is_utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timezone.utc.utcoffset(value)
    )


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_utc_rfc3339(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return _is_utc_datetime(parsed)


def _is_normalized_text(value: object, *, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and minimum <= len(value) <= maximum
    )


def _is_fixed_decimal_or_none(
    value: object,
    *,
    places: int,
    minimum: Decimal,
    maximum: Decimal | None,
) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return False
    if (
        not parsed.is_finite()
        or parsed < minimum
        or (maximum is not None and parsed > maximum)
    ):
        return False
    return format(parsed, f".{places}f") == value


def _safe_input_ref(value: object) -> bool:
    if not isinstance(value, str) or _SOURCE_REF_RE.fullmatch(value) is None:
        return False
    kind, identifier = value.split(":", maxsplit=1)
    if kind not in {"plant", "daily_checkin", "manual_measurement"}:
        return False
    try:
        _parse_canonical_uuid(identifier)
    except AgentRuntimeValidationError:
        return False
    return True


__all__ = [
    "AgentDefinition",
    "AgentInputRecordV1",
    "AgentModelResultV1",
    "AgentRuntimeOutcomeV1",
    "AgentRuntimeValidationError",
    "CurrentAuthorizationScope",
    "MessageEnvelopeV1",
    "ProviderRequestV1",
    "RuntimeDecision",
    "SafetyClassificationResultV1",
]
