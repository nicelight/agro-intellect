"""Strict values for the FT-009 real-photo Vision Observation boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
import re
from types import MappingProxyType
import uuid

from ..agent_runtime.contracts import (
    AgentRuntimeOutcomeV1,
    MessageEnvelopeV1,
    RuntimeDecision,
)


_SOURCE_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[0-9a-f-]{36}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_OBSERVATION_KEYS = frozenset(
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
_POLARITIES = frozenset({"present", "absent", "uncertain", "not_assessable"})
_SEVERITIES = frozenset({"none", "mild", "moderate", "strong", "unknown"})
_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_VISION_MEDIA_BYTES = 20 * 1024 * 1024


class VisionObservationValidationError(ValueError):
    """An FT-009 strict value failed closed validation."""

    def __init__(self) -> None:
        super().__init__("Vision Observation contract validation failed.")


@dataclass(frozen=True, slots=True)
class VisionObservationDefinitionV1:
    agent_id: str = "vision_observation"
    competence: str = (
        "photo quality and visible Plant observation without diagnosis or action advice"
    )
    instructions: str = (
        "Inspect only the attached accepted Plant photo. Return exactly one strict "
        "VisionObservationModelResultV1. Describe one visible finding or image quality; "
        "do not diagnose disease, recommend physical action, or invent evidence."
    )
    allowed_decisions: tuple[str, ...] = ("speak", "clarify", "silent")
    output_schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.agent_id != "vision_observation"
            or not isinstance(self.competence, str)
            or self.competence != self.competence.strip()
            or not 1 <= len(self.competence) <= 2000
            or not isinstance(self.instructions, str)
            or self.instructions != self.instructions.strip()
            or not 1 <= len(self.instructions) <= 10_000
            or self.allowed_decisions != ("speak", "clarify", "silent")
            or self.output_schema_version != 1
        ):
            raise VisionObservationValidationError()

    def as_provider_value(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "competence": self.competence,
            "instructions": self.instructions,
            "allowed_decisions": list(self.allowed_decisions),
            "output_schema": {
                "name": "VisionObservationModelResultV1",
                "schema_version": 1,
                "strict": True,
            },
        }


VISION_OBSERVATION_DEFINITION_V1 = VisionObservationDefinitionV1()


@dataclass(frozen=True, slots=True)
class VisionInputRecordV1:
    record_type: str
    source_ref: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.record_type not in {"plant", "photo"} or not isinstance(
            self.payload, Mapping
        ):
            raise VisionObservationValidationError()
        payload = dict(self.payload)
        if self.record_type == "plant":
            _expect_keys(payload, {"plant_id", "status"})
            plant_id = _canonical_uuid(payload["plant_id"])
            if self.source_ref != f"plant:{plant_id}" or payload["status"] != "active":
                raise VisionObservationValidationError()
        else:
            _expect_keys(
                payload,
                {
                    "photo_id",
                    "plant_id",
                    "photo_type",
                    "captured_at",
                    "content_type",
                    "size_bytes",
                    "sha256",
                    "local_only",
                },
            )
            photo_id = _canonical_uuid(payload["photo_id"])
            _canonical_uuid(payload["plant_id"])
            if (
                self.source_ref != f"photo:{photo_id}"
                or payload["photo_type"]
                not in {"whole_plant", "leaf_closeup", "roots", "problem_area", "other"}
                or not _utc_rfc3339(payload["captured_at"])
                or payload["content_type"] not in _CONTENT_TYPES
                or isinstance(payload["size_bytes"], bool)
                or not isinstance(payload["size_bytes"], int)
                or not 0 < payload["size_bytes"] <= MAX_VISION_MEDIA_BYTES
                or not isinstance(payload["sha256"], str)
                or _SHA256_RE.fullmatch(payload["sha256"]) is None
                or payload["local_only"] is not True
            ):
                raise VisionObservationValidationError()
        object.__setattr__(self, "payload", MappingProxyType(payload))

    def as_provider_value(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "source_ref": self.source_ref,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class VisionProviderRequestV1:
    records: tuple[VisionInputRecordV1, ...]
    agent_definition: VisionObservationDefinitionV1 = VISION_OBSERVATION_DEFINITION_V1
    schema_version: int = 1

    def __post_init__(self) -> None:
        records = tuple(self.records)
        refs = tuple(record.source_ref for record in records)
        if (
            self.schema_version != 1
            or self.agent_definition != VISION_OBSERVATION_DEFINITION_V1
            or len(records) != 2
            or tuple(record.record_type for record in records) != ("plant", "photo")
            or any(not isinstance(record, VisionInputRecordV1) for record in records)
            or len(refs) != len(set(refs))
        ):
            raise VisionObservationValidationError()
        plant_id = records[0].payload["plant_id"]
        if records[1].payload["plant_id"] != plant_id:
            raise VisionObservationValidationError()
        object.__setattr__(self, "records", records)

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(record.source_ref for record in self.records)

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "agent_definition": self.agent_definition.as_provider_value(),
            "records": [record.as_provider_value() for record in self.records],
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True, slots=True)
class VisionMediaV1:
    source_ref: str
    content_type: str
    sha256: str
    content: bytes

    def __post_init__(self) -> None:
        if (
            not _source_ref(self.source_ref, "photo")
            or self.content_type not in _CONTENT_TYPES
            or not isinstance(self.sha256, str)
            or _SHA256_RE.fullmatch(self.sha256) is None
            or not isinstance(self.content, bytes)
            or not 0 < len(self.content) <= MAX_VISION_MEDIA_BYTES
            or hashlib.sha256(self.content).hexdigest() != self.sha256
        ):
            raise VisionObservationValidationError()


@dataclass(frozen=True, slots=True)
class VisionObservationModelResultV1:
    runtime_decision: str
    observation_key: str | None
    polarity: str | None
    severity: str | None
    summary: str | None
    confidence: float | None
    reason_code: str | None
    schema_version: int = 1

    @classmethod
    def from_untrusted(
        cls,
        value: object,
    ) -> "VisionObservationModelResultV1":
        if not isinstance(value, Mapping):
            raise VisionObservationValidationError()
        fields = dict(value)
        _expect_keys(
            fields,
            {
                "schema_version",
                "runtime_decision",
                "observation_key",
                "polarity",
                "severity",
                "summary",
                "confidence",
                "reason_code",
            },
        )
        if fields["schema_version"] != 1:
            raise VisionObservationValidationError()
        decision = fields["runtime_decision"]
        key = fields["observation_key"]
        polarity = fields["polarity"]
        severity = fields["severity"]
        summary = fields["summary"]
        confidence = fields["confidence"]
        reason = fields["reason_code"]

        if decision == "silent":
            if (
                any(item is not None for item in (key, polarity, severity, summary, confidence))
                or reason != "no_material_output"
            ):
                raise VisionObservationValidationError()
        elif decision == "clarify":
            if (
                key != "image_quality"
                or polarity != "not_assessable"
                or severity != "unknown"
                or not _normalized_text(summary, 1, 1000)
                or confidence is not None
                or reason is not None
            ):
                raise VisionObservationValidationError()
        elif decision == "speak":
            normalized_confidence = _confidence(confidence)
            if (
                key not in _OBSERVATION_KEYS
                or polarity not in _POLARITIES
                or severity not in _SEVERITIES
                or not _normalized_text(summary, 1, 1000)
                or reason is not None
                or (polarity == "absent" and severity != "none")
                or (polarity == "present" and severity not in {"mild", "moderate", "strong"})
                or (polarity in {"uncertain", "not_assessable"} and severity != "unknown")
            ):
                raise VisionObservationValidationError()
            confidence = normalized_confidence
        else:
            raise VisionObservationValidationError()
        return cls(
            runtime_decision=str(decision),
            observation_key=key if isinstance(key, str) else None,
            polarity=polarity if isinstance(polarity, str) else None,
            severity=severity if isinstance(severity, str) else None,
            summary=summary if isinstance(summary, str) else None,
            confidence=confidence if isinstance(confidence, float) else None,
            reason_code=reason if isinstance(reason, str) else None,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "runtime_decision": self.runtime_decision,
            "observation_key": self.observation_key,
            "polarity": self.polarity,
            "severity": self.severity,
            "summary": self.summary,
            "confidence": self.confidence,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class VisionStateCandidateV1:
    run_id: uuid.UUID
    message_id: uuid.UUID
    observation_key: str
    polarity: str
    severity: str
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
            or self.observation_key not in _OBSERVATION_KEYS
            or self.polarity not in _POLARITIES
            or self.severity not in _SEVERITIES
            or not _normalized_text(self.summary, 1, 1000)
            or _confidence(self.confidence) != self.confidence
            or len(self.source_refs) != 1
            or not _source_ref(self.source_refs[0], "photo")
            or not _utc_datetime(self.observed_at)
            or (self.polarity == "absent" and self.severity != "none")
            or (
                self.polarity == "present"
                and self.severity not in {"mild", "moderate", "strong"}
            )
            or (
                self.polarity in {"uncertain", "not_assessable"}
                and self.severity != "unknown"
            )
        ):
            raise VisionObservationValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "message_id": str(self.message_id),
            "observation_key": self.observation_key,
            "polarity": self.polarity,
            "severity": self.severity,
            "summary": self.summary,
            "confidence": self.confidence,
            "source_refs": list(self.source_refs),
            "observed_at": _timestamp(self.observed_at),
        }


@dataclass(frozen=True, slots=True)
class VisionObservationOutcomeV1:
    runtime_outcome: AgentRuntimeOutcomeV1
    state_candidate: VisionStateCandidateV1 | None

    def __post_init__(self) -> None:
        outcome = self.runtime_outcome
        candidate = self.state_candidate
        if not isinstance(outcome, AgentRuntimeOutcomeV1):
            raise VisionObservationValidationError()
        if candidate is not None and (
            outcome.outcome_kind != "envelope_ready"
            or outcome.final_decision != "speak"
            or outcome.message_envelope is None
            or candidate.run_id != outcome.run_id
            or candidate.message_id != outcome.message_envelope.message_id
            or candidate.source_refs != outcome.message_envelope.source_refs
        ):
            raise VisionObservationValidationError()
        if (outcome.final_decision == "speak") != (candidate is not None):
            raise VisionObservationValidationError()

    def __getattr__(self, name: str):
        return getattr(self.runtime_outcome, name)

    def as_value(self) -> dict[str, object]:
        value = self.runtime_outcome.as_value()
        value["vision_state_candidate"] = (
            self.state_candidate.as_value() if self.state_candidate is not None else None
        )
        return value


def _expect_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise VisionObservationValidationError()


def _canonical_uuid(value: object) -> uuid.UUID:
    if not isinstance(value, str):
        raise VisionObservationValidationError()
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise VisionObservationValidationError() from None
    if str(parsed) != value:
        raise VisionObservationValidationError()
    return parsed


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _source_ref(value: object, expected_kind: str | None = None) -> bool:
    if not isinstance(value, str) or _SOURCE_REF_RE.fullmatch(value) is None:
        return False
    kind, identifier = value.split(":", 1)
    if kind not in {"plant", "photo"} or (
        expected_kind is not None and kind != expected_kind
    ):
        return False
    try:
        return str(uuid.UUID(identifier)) == identifier
    except (ValueError, TypeError, AttributeError):
        return False


def _normalized_text(value: object, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and minimum <= len(value) <= maximum
    )


def _confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VisionObservationValidationError()
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise VisionObservationValidationError()
    return result


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
    "MAX_VISION_MEDIA_BYTES",
    "VISION_OBSERVATION_DEFINITION_V1",
    "VisionInputRecordV1",
    "VisionMediaV1",
    "VisionObservationDefinitionV1",
    "VisionObservationModelResultV1",
    "VisionObservationOutcomeV1",
    "VisionObservationValidationError",
    "VisionProviderRequestV1",
    "VisionStateCandidateV1",
]
