"""Strict provider and service values for FT-009 Plant State trust."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
from types import MappingProxyType
import uuid

from ..agent_runtime.contracts import AgentRuntimeOutcomeV1


OBSERVATION_KEYS = frozenset(
    {
        "image_quality",
        "leaf_color_change",
        "leaf_spots",
        "wilting",
        "growth_change",
        "root_color_change",
        "root_damage",
        "other_visible_change",
    }
)
TRUST_STATUSES = frozenset(
    {"unknown", "observed", "hypothesis", "conflicting", "confirmed", "rejected"}
)
_INPUT_TRUST_STATUSES = TRUST_STATUSES - {"rejected"}
_POLARITIES = frozenset({"present", "absent", "uncertain", "not_assessable"})
_SEVERITIES = frozenset({"none", "mild", "moderate", "strong", "unknown"})
_ASSESSMENT_KINDS = frozenset({"trend", "conflict", "unknown"})
_DIRECTIONS = frozenset(
    {"increasing", "decreasing", "stable", "mixed", "not_applicable"}
)
_SAFE_REF_KINDS = frozenset({"plant", "photo", "plant_state_record"})
_SOURCE_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[0-9a-f-]{36}\Z")


class PlantStateValidationError(ValueError):
    """A strict Plant State value failed closed validation."""

    def __init__(self) -> None:
        super().__init__("Plant State contract validation failed.")


@dataclass(frozen=True, slots=True)
class PlantStateDefinitionV1:
    agent_id: str = "plant_state"
    competence: str = "Plant trend, conflict, and unknown assessment from trusted records"
    instructions: str = (
        "Assess only the supplied Plant state records. Return exactly one strict "
        "PlantStateModelResultV1. Do not confirm state, recommend actions, create "
        "tasks, or invent evidence."
    )
    allowed_decisions: tuple[str, ...] = ("speak", "clarify", "silent")
    output_schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.agent_id != "plant_state"
            or not isinstance(self.competence, str)
            or self.competence != self.competence.strip()
            or not 1 <= len(self.competence) <= 2000
            or not isinstance(self.instructions, str)
            or self.instructions != self.instructions.strip()
            or not 1 <= len(self.instructions) <= 10_000
            or self.allowed_decisions != ("speak", "clarify", "silent")
            or self.output_schema_version != 1
        ):
            raise PlantStateValidationError()

    def as_provider_value(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "competence": self.competence,
            "instructions": self.instructions,
            "allowed_decisions": list(self.allowed_decisions),
            "output_schema": {
                "name": "PlantStateModelResultV1",
                "schema_version": 1,
                "strict": True,
            },
        }


PLANT_STATE_DEFINITION_V1 = PlantStateDefinitionV1()


@dataclass(frozen=True, slots=True)
class PlantStateInputRecordV1:
    source_ref: str
    payload: Mapping[str, object]
    record_type: str = "plant_state_record"

    def __post_init__(self) -> None:
        if self.record_type != "plant_state_record" or not isinstance(
            self.payload, Mapping
        ):
            raise PlantStateValidationError()
        payload = dict(self.payload)
        _expect_keys(
            payload,
            {
                "state_record_id",
                "observation_key",
                "polarity",
                "severity",
                "assessment_kind",
                "direction",
                "trust_status",
                "observed_at",
                "recorded_at",
                "confidence",
                "source_refs",
            },
        )
        state_record_id = _canonical_uuid_text(payload["state_record_id"])
        if (
            self.source_ref != f"plant_state_record:{state_record_id}"
            or payload["observation_key"] not in OBSERVATION_KEYS
            or payload["polarity"] not in _POLARITIES | {None}
            or payload["severity"] not in _SEVERITIES | {None}
            or payload["assessment_kind"] not in _ASSESSMENT_KINDS | {None}
            or payload["direction"] not in _DIRECTIONS | {None}
            or payload["trust_status"] not in _INPUT_TRUST_STATUSES
            or not _utc_rfc3339(payload["observed_at"])
            or not _utc_rfc3339(payload["recorded_at"])
            or _confidence(payload["confidence"]) is None
        ):
            raise PlantStateValidationError()
        polarity = payload["polarity"]
        severity = payload["severity"]
        assessment = payload["assessment_kind"]
        direction = payload["direction"]
        if (polarity is None) != (severity is None) or (assessment is None) != (
            direction is None
        ):
            raise PlantStateValidationError()
        if (polarity is None) == (assessment is None):
            raise PlantStateValidationError()
        if assessment in {"conflict", "unknown"} and direction != "not_applicable":
            raise PlantStateValidationError()
        if assessment == "trend" and direction == "not_applicable":
            raise PlantStateValidationError()
        refs = _safe_refs(payload["source_refs"], minimum=1, maximum=4)
        payload["source_refs"] = refs
        payload["confidence"] = _confidence(payload["confidence"])
        object.__setattr__(self, "payload", MappingProxyType(payload))

    def as_provider_value(self) -> dict[str, object]:
        value = dict(self.payload)
        value["source_refs"] = list(value["source_refs"])
        return {
            "record_type": "plant_state_record",
            "source_ref": self.source_ref,
            "payload": value,
        }


@dataclass(frozen=True, slots=True)
class PlantStateProviderRequestV1:
    records: tuple[PlantStateInputRecordV1, ...]
    agent_definition: PlantStateDefinitionV1 = PLANT_STATE_DEFINITION_V1
    schema_version: int = 1

    def __post_init__(self) -> None:
        records = tuple(self.records)
        refs = tuple(item.source_ref for item in records)
        if (
            self.schema_version != 1
            or self.agent_definition != PLANT_STATE_DEFINITION_V1
            or not 1 <= len(records) <= 4
            or any(not isinstance(item, PlantStateInputRecordV1) for item in records)
            or len(refs) != len(set(refs))
        ):
            raise PlantStateValidationError()
        object.__setattr__(self, "records", records)

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(item.source_ref for item in self.records)

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "agent_definition": self.agent_definition.as_provider_value(),
            "records": [item.as_provider_value() for item in self.records],
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class PlantStateModelResultV1:
    runtime_decision: str
    assessment_kind: str | None
    observation_key: str | None
    direction: str | None
    summary: str | None
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
    ) -> "PlantStateModelResultV1":
        if not isinstance(value, Mapping):
            raise PlantStateValidationError()
        fields = dict(value)
        _expect_keys(
            fields,
            {
                "schema_version",
                "runtime_decision",
                "assessment_kind",
                "observation_key",
                "direction",
                "summary",
                "confidence",
                "source_refs",
                "reason_code",
            },
        )
        if fields["schema_version"] != 1:
            raise PlantStateValidationError()
        decision = fields["runtime_decision"]
        kind = fields["assessment_kind"]
        key = fields["observation_key"]
        direction = fields["direction"]
        summary = fields["summary"]
        confidence = fields["confidence"]
        refs = _ordered_subset(fields["source_refs"], request_source_refs)
        reason = fields["reason_code"]
        if decision == "silent":
            if (
                any(item is not None for item in (kind, key, direction, summary, confidence))
                or refs
                or reason not in {"no_material_output", "insufficient_evidence"}
            ):
                raise PlantStateValidationError()
        elif decision == "clarify":
            if (
                kind != "unknown"
                or key not in OBSERVATION_KEYS
                or direction != "not_applicable"
                or not _normalized_text(summary, 1, 1000)
                or confidence is not None
                or not refs
                or reason is not None
            ):
                raise PlantStateValidationError()
        elif decision == "speak":
            normalized_confidence = _confidence(confidence)
            if (
                kind not in _ASSESSMENT_KINDS
                or key not in OBSERVATION_KEYS
                or direction not in _DIRECTIONS
                or not _normalized_text(summary, 1, 1000)
                or normalized_confidence is None
                or not refs
                or reason is not None
                or (kind == "trend" and direction == "not_applicable")
                or (kind in {"conflict", "unknown"} and direction != "not_applicable")
            ):
                raise PlantStateValidationError()
            confidence = normalized_confidence
        else:
            raise PlantStateValidationError()
        return cls(
            runtime_decision=str(decision),
            assessment_kind=kind if isinstance(kind, str) else None,
            observation_key=key if isinstance(key, str) else None,
            direction=direction if isinstance(direction, str) else None,
            summary=summary if isinstance(summary, str) else None,
            confidence=confidence if isinstance(confidence, float) else None,
            source_refs=refs,
            reason_code=reason if isinstance(reason, str) else None,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "runtime_decision": self.runtime_decision,
            "assessment_kind": self.assessment_kind,
            "observation_key": self.observation_key,
            "direction": self.direction,
            "summary": self.summary,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class PlantStateAssessmentCandidateV1:
    run_id: uuid.UUID
    message_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    assessment_kind: str
    observation_key: str
    direction: str
    summary: str
    confidence: float
    source_refs: tuple[str, ...]
    observed_at: datetime
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or not _uuid4(self.message_id)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.assessment_kind not in _ASSESSMENT_KINDS
            or self.observation_key not in OBSERVATION_KEYS
            or self.direction not in _DIRECTIONS
            or not _normalized_text(self.summary, 1, 1000)
            or _confidence(self.confidence) is None
            or not _utc_datetime(self.observed_at)
            or self.source_refs
            != _safe_refs(self.source_refs, minimum=1, maximum=4)
            or (
                self.assessment_kind == "trend"
                and self.direction == "not_applicable"
            )
            or (
                self.assessment_kind in {"conflict", "unknown"}
                and self.direction != "not_applicable"
            )
        ):
            raise PlantStateValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "message_id": str(self.message_id),
            "farm_id": str(self.farm_id),
            "plant_id": str(self.plant_id),
            "assessment_kind": self.assessment_kind,
            "observation_key": self.observation_key,
            "direction": self.direction,
            "summary": self.summary,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "observed_at": _timestamp(self.observed_at),
        }


@dataclass(frozen=True, slots=True)
class PlantStateRuntimeOutcomeV1:
    runtime_outcome: AgentRuntimeOutcomeV1
    state_candidate: PlantStateAssessmentCandidateV1 | None

    def __post_init__(self) -> None:
        outcome = self.runtime_outcome
        candidate = self.state_candidate
        if not isinstance(outcome, AgentRuntimeOutcomeV1):
            raise PlantStateValidationError()
        if candidate is not None and (
            outcome.outcome_kind != "envelope_ready"
            or outcome.final_decision != "speak"
            or outcome.message_envelope is None
            or candidate.run_id != outcome.run_id
            or candidate.message_id != outcome.message_envelope.message_id
        ):
            raise PlantStateValidationError()
        if (outcome.final_decision == "speak") != (candidate is not None):
            raise PlantStateValidationError()

    def __getattr__(self, name: str):
        return getattr(self.runtime_outcome, name)

    def as_value(self) -> dict[str, object]:
        value = self.runtime_outcome.as_value()
        value["plant_state_candidate"] = (
            self.state_candidate.as_value() if self.state_candidate is not None else None
        )
        return value


def validate_structural_assessment(
    records: Sequence[object],
    *,
    assessment_kind: str,
    observation_key: str,
    direction: str,
) -> bool:
    """Validate model labels against persisted record structure only."""

    if not records or any(
        getattr(item, "observation_key", None) != observation_key for item in records
    ):
        return False
    if assessment_kind == "conflict":
        if direction != "not_applicable":
            return False
        polarities = {getattr(item, "polarity", None) for item in records}
        return (
            {"present", "absent"}.issubset(polarities)
            or any(getattr(item, "trust_status", None) == "conflicting" for item in records)
        )
    if assessment_kind == "unknown":
        return direction == "not_applicable" and any(
            getattr(item, "trust_status", None) == "unknown"
            or getattr(item, "polarity", None) in {"uncertain", "not_assessable"}
            or getattr(item, "assessment_kind", None) == "unknown"
            for item in records
        )
    if assessment_kind != "trend" or direction == "not_applicable" or len(records) < 2:
        return False
    severity_values = {"none": 0, "mild": 1, "moderate": 2, "strong": 3}
    values: list[int] = []
    for item in records:
        severity = getattr(item, "severity", None)
        if severity not in severity_values:
            return False
        values.append(severity_values[severity])
    if direction == "increasing":
        return all(a <= b for a, b in zip(values, values[1:])) and any(
            a < b for a, b in zip(values, values[1:])
        )
    if direction == "decreasing":
        return all(a >= b for a, b in zip(values, values[1:])) and any(
            a > b for a, b in zip(values, values[1:])
        )
    if direction == "stable":
        return len(set(values)) == 1
    if direction == "mixed":
        increasing = all(a <= b for a, b in zip(values, values[1:]))
        decreasing = all(a >= b for a, b in zip(values, values[1:]))
        stable = len(set(values)) == 1
        return not increasing and not decreasing and not stable
    return False


def _expect_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise PlantStateValidationError()


def _canonical_uuid_text(value: object) -> uuid.UUID:
    if not isinstance(value, str):
        raise PlantStateValidationError()
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise PlantStateValidationError() from None
    if str(parsed) != value:
        raise PlantStateValidationError()
    return parsed


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _safe_ref(value: object) -> bool:
    if not isinstance(value, str) or _SOURCE_REF_RE.fullmatch(value) is None:
        return False
    kind, identifier = value.split(":", 1)
    if kind not in _SAFE_REF_KINDS:
        return False
    try:
        return str(uuid.UUID(identifier)) == identifier
    except (TypeError, ValueError, AttributeError):
        return False


def _safe_refs(value: object, *, minimum: int, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise PlantStateValidationError()
    refs = tuple(value)
    if (
        not minimum <= len(refs) <= maximum
        or len(refs) != len(set(refs))
        or any(not _safe_ref(item) for item in refs)
    ):
        raise PlantStateValidationError()
    return refs


def _ordered_subset(value: object, request_refs: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PlantStateValidationError()
    refs = tuple(value)
    if len(refs) > 4 or len(refs) != len(set(refs)) or refs != tuple(
        item for item in request_refs if item in refs
    ):
        raise PlantStateValidationError()
    return refs


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    normalized = float(value)
    return normalized if math.isfinite(normalized) and 0 <= normalized <= 1 else None


def _normalized_text(value: object, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and minimum <= len(value) <= maximum
    )


def _utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timezone.utc.utcoffset(value)
    )


def _utc_rfc3339(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return _utc_datetime(parsed)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "OBSERVATION_KEYS",
    "PLANT_STATE_DEFINITION_V1",
    "TRUST_STATUSES",
    "PlantStateAssessmentCandidateV1",
    "PlantStateDefinitionV1",
    "PlantStateInputRecordV1",
    "PlantStateModelResultV1",
    "PlantStateProviderRequestV1",
    "PlantStateRuntimeOutcomeV1",
    "PlantStateValidationError",
    "validate_structural_assessment",
]
