"""Strict provider-neutral value objects for the Hydroponics Advisor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import math
import re
from types import MappingProxyType
import uuid

from ..access_admin.actor_context import ActorContext
from ..agent_runtime.contracts import AgentInputRecordV1, AgentRuntimeValidationError
from ..agent_runtime.roster import CANONICAL_ROSTER_V1


REQUEST_REASONS = frozenset(
    {"daily_checkin", "plant_state_update", "manual_review"}
)
ANALYSIS_GOALS = frozenset(
    {
        "general_hydroponics_review",
        "solution_related_review",
        "missing_data_review",
    }
)
MEASUREMENT_NAMES = ("ph", "ec")
_FRESHNESS_STATUSES = frozenset({"fresh", "stale", "missing"})
_ADVICE_KINDS = frozenset(
    {"recommendation", "hypothesis", "measurement_request", "clarification"}
)
_SILENCE_REASONS = frozenset({"no_material_output", "insufficient_evidence"})
_TRUST_STATUSES = frozenset(
    {"unknown", "observed", "hypothesis", "conflicting", "confirmed"}
)
_POLARITIES = frozenset({"present", "absent", "uncertain", "not_assessable"})
_SEVERITIES = frozenset({"none", "mild", "moderate", "strong", "unknown"})
_ASSESSMENT_KINDS = frozenset({"trend", "conflict", "unknown"})
_DIRECTIONS = frozenset(
    {"increasing", "decreasing", "stable", "mixed", "not_applicable"}
)
_SOURCE_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[0-9a-f-]{36}\Z")
_HYDROPONICS_ADVISOR_ROSTER_ENTRY = next(
    item for item in CANONICAL_ROSTER_V1 if item.agent_id == "hydroponics_advisor"
)


class HydroponicsAdvisorValidationError(ValueError):
    """A strict advisor command, request, or result failed validation."""

    def __init__(self) -> None:
        super().__init__("Hydroponics Advisor contract validation failed.")


@dataclass(frozen=True, slots=True)
class HydroponicsAdvisorCommandV1:
    run_id: uuid.UUID
    requested_at: datetime
    actor_context: ActorContext
    plant_id: uuid.UUID
    request_reason: str
    analysis_goal: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or not _utc_datetime(self.requested_at)
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.plant_id, uuid.UUID)
            or self.request_reason not in REQUEST_REASONS
            or self.analysis_goal not in ANALYSIS_GOALS
        ):
            raise HydroponicsAdvisorValidationError()


@dataclass(frozen=True, slots=True)
class HydroponicsAdvisorDefinitionV1:
    agent_id: str = _HYDROPONICS_ADVISOR_ROSTER_ENTRY.agent_id
    competence: str = _HYDROPONICS_ADVISOR_ROSTER_ENTRY.competence_summary
    instructions: str = (
        "Use only the supplied typed Plant evidence and project-computed freshness. "
        "Return exactly one strict HydroponicsAdvisorModelResultV1. Never invent "
        "measurements, authorize actions, create tasks, or override Safety policy."
    )
    allowed_decisions: tuple[str, ...] = ("speak", "clarify", "silent")
    output_schema_version: int = (
        _HYDROPONICS_ADVISOR_ROSTER_ENTRY.output_schema_version
    )

    def __post_init__(self) -> None:
        if (
            self.agent_id != _HYDROPONICS_ADVISOR_ROSTER_ENTRY.agent_id
            or self.competence
            != _HYDROPONICS_ADVISOR_ROSTER_ENTRY.competence_summary
            or not isinstance(self.instructions, str)
            or self.instructions != self.instructions.strip()
            or not 1 <= len(self.instructions) <= 10_000
            or self.allowed_decisions != ("speak", "clarify", "silent")
            or self.output_schema_version
            != _HYDROPONICS_ADVISOR_ROSTER_ENTRY.output_schema_version
        ):
            raise HydroponicsAdvisorValidationError()

    def as_provider_value(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "competence": self.competence,
            "instructions": self.instructions,
            "allowed_decisions": list(self.allowed_decisions),
            "output_schema": {
                "name": "HydroponicsAdvisorModelResultV1",
                "schema_version": self.output_schema_version,
                "strict": True,
            },
        }


HYDROPONICS_ADVISOR_DEFINITION_V1 = HydroponicsAdvisorDefinitionV1()


@dataclass(frozen=True, slots=True)
class HydroponicsAdvisorInputRecordV1:
    record_type: str
    source_ref: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.payload, Mapping):
            raise HydroponicsAdvisorValidationError()
        payload = dict(self.payload)
        if self.record_type in {"plant", "daily_checkin", "manual_measurement"}:
            try:
                validated = AgentInputRecordV1(
                    record_type=self.record_type,
                    source_ref=self.source_ref,
                    payload=payload,
                )
            except (AgentRuntimeValidationError, TypeError, ValueError):
                raise HydroponicsAdvisorValidationError() from None
            payload = dict(validated.payload)
        elif self.record_type == "plant_state_record":
            _validate_plant_state_record(self.source_ref, payload)
        else:
            raise HydroponicsAdvisorValidationError()
        object.__setattr__(self, "payload", MappingProxyType(payload))

    def as_provider_value(self) -> dict[str, object]:
        payload = dict(self.payload)
        if self.record_type == "plant_state_record":
            payload["source_refs"] = list(payload["source_refs"])
        return {
            "record_type": self.record_type,
            "source_ref": self.source_ref,
            "payload": payload,
        }


@dataclass(frozen=True, slots=True)
class MeasurementFreshnessV1:
    status: str
    source_ref: str | None
    measured_at: str | None

    def __post_init__(self) -> None:
        if self.status not in _FRESHNESS_STATUSES:
            raise HydroponicsAdvisorValidationError()
        if self.status == "missing":
            if self.source_ref is not None or self.measured_at is not None:
                raise HydroponicsAdvisorValidationError()
            return
        if not _record_ref(self.source_ref, "manual_measurement") or not _utc_rfc3339(
            self.measured_at
        ):
            raise HydroponicsAdvisorValidationError()

    def as_provider_value(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_ref": self.source_ref,
            "measured_at": self.measured_at,
        }


@dataclass(frozen=True, slots=True)
class AnalysisFreshnessV1:
    computed_at: str
    ph: MeasurementFreshnessV1
    ec: MeasurementFreshnessV1
    missing_or_stale: tuple[str, ...]
    window_hours: int = 24

    def __post_init__(self) -> None:
        if not isinstance(self.ph, MeasurementFreshnessV1) or not isinstance(
            self.ec, MeasurementFreshnessV1
        ):
            raise HydroponicsAdvisorValidationError()
        expected = tuple(
            name
            for name, value in (("ph", self.ph), ("ec", self.ec))
            if value.status != "fresh"
        )
        if (
            self.window_hours != 24
            or not _utc_rfc3339(self.computed_at)
            or tuple(self.missing_or_stale) != expected
        ):
            raise HydroponicsAdvisorValidationError()
        object.__setattr__(self, "missing_or_stale", expected)

    def as_provider_value(self) -> dict[str, object]:
        return {
            "window_hours": 24,
            "computed_at": self.computed_at,
            "ph": self.ph.as_provider_value(),
            "ec": self.ec.as_provider_value(),
            "missing_or_stale": list(self.missing_or_stale),
        }


@dataclass(frozen=True, slots=True)
class HydroponicsAdvisorProviderRequestV1:
    request_reason: str
    analysis_goal: str
    computed_at: str
    analysis_freshness: AnalysisFreshnessV1
    records: tuple[HydroponicsAdvisorInputRecordV1, ...]
    source_refs: tuple[str, ...]
    agent_definition: HydroponicsAdvisorDefinitionV1 = (
        HYDROPONICS_ADVISOR_DEFINITION_V1
    )
    schema_version: int = 1

    def __post_init__(self) -> None:
        records = tuple(self.records)
        refs = tuple(self.source_refs)
        if (
            self.schema_version != 1
            or self.agent_definition != HYDROPONICS_ADVISOR_DEFINITION_V1
            or self.request_reason not in REQUEST_REASONS
            or self.analysis_goal not in ANALYSIS_GOALS
            or not _utc_rfc3339(self.computed_at)
            or not isinstance(self.analysis_freshness, AnalysisFreshnessV1)
            or self.analysis_freshness.computed_at != self.computed_at
            or not 1 <= len(records) <= 4
            or any(
                not isinstance(record, HydroponicsAdvisorInputRecordV1)
                for record in records
            )
            or refs != tuple(record.source_ref for record in records)
            or len(refs) != len(set(refs))
            or records[0].record_type != "plant"
        ):
            raise HydroponicsAdvisorValidationError()
        _validate_record_order(records)
        _validate_freshness_sources(records, self.analysis_freshness)
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "source_refs", refs)

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "agent_definition": self.agent_definition.as_provider_value(),
            "request_reason": self.request_reason,
            "analysis_goal": self.analysis_goal,
            "computed_at": self.computed_at,
            "analysis_freshness": self.analysis_freshness.as_provider_value(),
            "records": [record.as_provider_value() for record in self.records],
            "source_refs": list(self.source_refs),
        }

    def policy_source_refs(self) -> tuple[str, ...]:
        refs = [self.records[0].source_ref]
        for value in (self.analysis_freshness.ph, self.analysis_freshness.ec):
            if value.status == "stale" and value.source_ref not in refs:
                assert value.source_ref is not None
                refs.append(value.source_ref)
        return tuple(refs)

    def fresh_measurement_refs(self) -> tuple[str, ...]:
        refs: list[str] = []
        for value in (self.analysis_freshness.ph, self.analysis_freshness.ec):
            if value.status == "fresh" and value.source_ref not in refs:
                assert value.source_ref is not None
                refs.append(value.source_ref)
        return tuple(refs)


@dataclass(frozen=True, slots=True)
class HydroponicsAdvisorModelResultV1:
    runtime_decision: str
    advice_kind: str | None
    candidate_output: str | None
    confidence: float | None
    requested_measurements: tuple[str, ...]
    source_refs: tuple[str, ...]
    reason_code: str | None
    schema_version: int = 1

    @classmethod
    def from_untrusted(
        cls,
        value: object,
        *,
        request: HydroponicsAdvisorProviderRequestV1,
    ) -> "HydroponicsAdvisorModelResultV1":
        fields = _exact_mapping(
            value,
            {
                "schema_version",
                "runtime_decision",
                "advice_kind",
                "candidate_output",
                "confidence",
                "requested_measurements",
                "source_refs",
                "reason_code",
            },
        )
        if fields["schema_version"] != 1:
            raise HydroponicsAdvisorValidationError()
        decision = fields["runtime_decision"]
        kind = fields["advice_kind"]
        output = fields["candidate_output"]
        confidence = fields["confidence"]
        measurements = _measurement_names(fields["requested_measurements"])
        refs = _ordered_subset(fields["source_refs"], request.source_refs)
        reason = fields["reason_code"]
        missing = request.analysis_freshness.missing_or_stale

        if missing:
            if (
                decision != "speak"
                or kind != "measurement_request"
                or output is not None
                or confidence is not None
                or measurements != missing
                or refs != request.policy_source_refs()
                or reason != "critical_measurements_required"
            ):
                raise HydroponicsAdvisorValidationError()
            normalized_confidence = None
        elif decision == "silent":
            if (
                kind is not None
                or output is not None
                or confidence is not None
                or measurements
                or refs
                or reason not in _SILENCE_REASONS
            ):
                raise HydroponicsAdvisorValidationError()
            normalized_confidence = None
        elif decision == "speak" and kind in {"recommendation", "hypothesis"}:
            normalized_confidence = _required_confidence(confidence)
            if (
                not _normalized_text(output, minimum=1, maximum=1000)
                or measurements
                or not refs
                or not _contains_all(refs, request.fresh_measurement_refs())
                or reason is not None
            ):
                raise HydroponicsAdvisorValidationError()
        elif decision == "clarify" and kind == "clarification":
            normalized_confidence = None
            if (
                not _normalized_text(output, minimum=1, maximum=1000)
                or confidence is not None
                or measurements
                or not refs
                or not _contains_all(refs, request.fresh_measurement_refs())
                or reason is not None
            ):
                raise HydroponicsAdvisorValidationError()
        else:
            raise HydroponicsAdvisorValidationError()
        if kind is not None and kind not in _ADVICE_KINDS:
            raise HydroponicsAdvisorValidationError()
        return cls(
            runtime_decision=str(decision),
            advice_kind=kind if isinstance(kind, str) else None,
            candidate_output=output if isinstance(output, str) else None,
            confidence=normalized_confidence,
            requested_measurements=measurements,
            source_refs=refs,
            reason_code=reason if isinstance(reason, str) else None,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "runtime_decision": self.runtime_decision,
            "advice_kind": self.advice_kind,
            "candidate_output": self.candidate_output,
            "confidence": self.confidence,
            "requested_measurements": list(self.requested_measurements),
            "source_refs": list(self.source_refs),
            "reason_code": self.reason_code,
        }


def measurement_request_text(measurements: tuple[str, ...]) -> str:
    if measurements == ("ph",):
        return "Нужно свежее измерение pH перед рекомендацией."
    if measurements == ("ec",):
        return "Нужно свежее измерение EC перед рекомендацией."
    if measurements == ("ph", "ec"):
        return "Нужны свежие измерения pH и EC перед рекомендацией."
    raise HydroponicsAdvisorValidationError()


def _validate_plant_state_record(
    source_ref: str,
    payload: dict[str, object],
) -> None:
    _expect_keys(
        payload,
        {
            "state_record_id",
            "record_kind",
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
    state_id = _canonical_uuid(payload["state_record_id"])
    if (
        source_ref != f"plant_state_record:{state_id}"
        or payload["record_kind"]
        not in {"vision_observation", "plant_state_assessment"}
        or not _normalized_text(payload["observation_key"], minimum=1, maximum=64)
        or payload["polarity"] not in _POLARITIES | {None}
        or payload["severity"] not in _SEVERITIES | {None}
        or payload["assessment_kind"] not in _ASSESSMENT_KINDS | {None}
        or payload["direction"] not in _DIRECTIONS | {None}
        or payload["trust_status"] not in _TRUST_STATUSES
        or not _utc_rfc3339(payload["observed_at"])
        or not _utc_rfc3339(payload["recorded_at"])
    ):
        raise HydroponicsAdvisorValidationError()
    confidence = _required_confidence(payload["confidence"])
    refs = _safe_refs(payload["source_refs"], minimum=1, maximum=4)
    if payload["record_kind"] == "vision_observation":
        if (
            payload["polarity"] is None
            or payload["severity"] is None
            or payload["assessment_kind"] is not None
            or payload["direction"] is not None
            or (
                payload["polarity"] == "absent"
                and payload["severity"] != "none"
            )
            or (
                payload["polarity"] == "present"
                and payload["severity"] not in {"mild", "moderate", "strong"}
            )
            or (
                payload["polarity"] in {"uncertain", "not_assessable"}
                and payload["severity"] != "unknown"
            )
        ):
            raise HydroponicsAdvisorValidationError()
    elif (
        payload["polarity"] is not None
        or payload["severity"] is not None
        or payload["assessment_kind"] is None
        or payload["direction"] is None
        or (
            payload["assessment_kind"] == "trend"
            and payload["direction"] == "not_applicable"
        )
        or (
            payload["assessment_kind"] in {"conflict", "unknown"}
            and payload["direction"] != "not_applicable"
        )
    ):
        raise HydroponicsAdvisorValidationError()
    payload["confidence"] = confidence
    payload["source_refs"] = refs


def _validate_record_order(
    records: tuple[HydroponicsAdvisorInputRecordV1, ...],
) -> None:
    phase = "measurement"
    measurement_count = 0
    context_types: set[str] = set()
    for record in records[1:]:
        if record.record_type == "manual_measurement" and phase == "measurement":
            measurement_count += 1
            if measurement_count > 2:
                raise HydroponicsAdvisorValidationError()
            continue
        phase = "context"
        if record.record_type not in {"daily_checkin", "plant_state_record"}:
            raise HydroponicsAdvisorValidationError()
        if record.record_type in context_types:
            raise HydroponicsAdvisorValidationError()
        context_types.add(record.record_type)
    context = [
        record
        for record in records
        if record.record_type in {"daily_checkin", "plant_state_record"}
    ]
    context_times = [_parse_rfc3339(record.payload["recorded_at"]) for record in context]
    if context_times != sorted(context_times):
        raise HydroponicsAdvisorValidationError()


def _validate_freshness_sources(
    records: tuple[HydroponicsAdvisorInputRecordV1, ...],
    freshness: AnalysisFreshnessV1,
) -> None:
    by_ref = {record.source_ref: record for record in records}
    computed_at = _parse_rfc3339(freshness.computed_at)
    expected_measurement_refs: list[str] = []
    for name, value in (("ph", freshness.ph), ("ec_ms_cm", freshness.ec)):
        if value.status == "missing":
            if any(
                record.record_type == "manual_measurement"
                and record.payload[name] is not None
                for record in records
            ):
                raise HydroponicsAdvisorValidationError()
            continue
        record = by_ref.get(value.source_ref or "")
        if (
            record is None
            or record.record_type != "manual_measurement"
            or record.payload[name] is None
            or record.payload["measured_at"] != value.measured_at
        ):
            raise HydroponicsAdvisorValidationError()
        measured_at = _parse_rfc3339(value.measured_at)
        expected_status = (
            "fresh"
            if computed_at - timedelta(hours=24) <= measured_at <= computed_at
            else "stale"
        )
        if value.status != expected_status:
            raise HydroponicsAdvisorValidationError()
        assert value.source_ref is not None
        if value.source_ref not in expected_measurement_refs:
            expected_measurement_refs.append(value.source_ref)
    actual_measurement_refs = [
        record.source_ref
        for record in records
        if record.record_type == "manual_measurement"
    ]
    if actual_measurement_refs != expected_measurement_refs:
        raise HydroponicsAdvisorValidationError()


def _measurement_names(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise HydroponicsAdvisorValidationError()
    names = tuple(value)
    if (
        len(names) != len(set(names))
        or any(name not in MEASUREMENT_NAMES for name in names)
        or names != tuple(name for name in MEASUREMENT_NAMES if name in names)
    ):
        raise HydroponicsAdvisorValidationError()
    return names


def _ordered_subset(value: object, request_refs: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise HydroponicsAdvisorValidationError()
    refs = tuple(value)
    if (
        len(refs) > 4
        or len(refs) != len(set(refs))
        or refs != tuple(ref for ref in request_refs if ref in refs)
    ):
        raise HydroponicsAdvisorValidationError()
    return refs


def _contains_all(values: tuple[str, ...], required: tuple[str, ...]) -> bool:
    return all(value in values for value in required)


def _safe_refs(value: object, *, minimum: int, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise HydroponicsAdvisorValidationError()
    refs = tuple(value)
    if (
        not minimum <= len(refs) <= maximum
        or len(refs) != len(set(refs))
        or any(not _safe_ref(ref) for ref in refs)
    ):
        raise HydroponicsAdvisorValidationError()
    return refs


def _safe_ref(value: object) -> bool:
    if not isinstance(value, str) or _SOURCE_REF_RE.fullmatch(value) is None:
        return False
    try:
        return str(uuid.UUID(value.split(":", 1)[1])) == value.split(":", 1)[1]
    except (TypeError, ValueError, AttributeError):
        return False


def _record_ref(value: object, kind: str) -> bool:
    return _safe_ref(value) and isinstance(value, str) and value.startswith(f"{kind}:")


def _exact_mapping(value: object, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydroponicsAdvisorValidationError()
    result = dict(value)
    _expect_keys(result, expected)
    return result


def _expect_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise HydroponicsAdvisorValidationError()


def _canonical_uuid(value: object) -> uuid.UUID:
    if not isinstance(value, str):
        raise HydroponicsAdvisorValidationError()
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise HydroponicsAdvisorValidationError() from None
    if str(parsed) != value:
        raise HydroponicsAdvisorValidationError()
    return parsed


def _required_confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise HydroponicsAdvisorValidationError()
    normalized = float(value)
    if not math.isfinite(normalized) or not 0 <= normalized <= 1:
        raise HydroponicsAdvisorValidationError()
    return normalized


def _normalized_text(value: object, *, minimum: int, maximum: int) -> bool:
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


def _parse_rfc3339(value: object) -> datetime:
    if not isinstance(value, str):
        raise HydroponicsAdvisorValidationError()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HydroponicsAdvisorValidationError() from None
    if not _utc_datetime(parsed):
        raise HydroponicsAdvisorValidationError()
    return parsed


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def fixed_decimal(value: Decimal | object, *, places: int) -> str:
    """Serialize an already canonical PostgreSQL numeric without re-rounding."""

    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HydroponicsAdvisorValidationError() from None
    if not parsed.is_finite():
        raise HydroponicsAdvisorValidationError()
    rendered = format(parsed, f".{places}f")
    if Decimal(rendered) != parsed:
        raise HydroponicsAdvisorValidationError()
    return rendered


__all__ = [
    "ANALYSIS_GOALS",
    "HYDROPONICS_ADVISOR_DEFINITION_V1",
    "MEASUREMENT_NAMES",
    "REQUEST_REASONS",
    "AnalysisFreshnessV1",
    "HydroponicsAdvisorCommandV1",
    "HydroponicsAdvisorDefinitionV1",
    "HydroponicsAdvisorInputRecordV1",
    "HydroponicsAdvisorModelResultV1",
    "HydroponicsAdvisorProviderRequestV1",
    "HydroponicsAdvisorValidationError",
    "MeasurementFreshnessV1",
    "fixed_decimal",
    "measurement_request_text",
]
