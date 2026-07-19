from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

import pytest

from backend.app.plant_state import (
    PlantStateInputRecordV1,
    PlantStateModelResultV1,
    PlantStateProviderRequestV1,
    PlantStateValidationError,
    validate_structural_assessment,
)


def _record(*, trust="observed", polarity="present", severity="mild"):
    record_id = uuid.uuid4()
    return PlantStateInputRecordV1(
        source_ref=f"plant_state_record:{record_id}",
        payload={
            "state_record_id": str(record_id),
            "observation_key": "leaf_color_change",
            "polarity": polarity,
            "severity": severity,
            "assessment_kind": None,
            "direction": None,
            "trust_status": trust,
            "observed_at": "2026-07-19T08:00:00Z",
            "recorded_at": "2026-07-19T08:01:00Z",
            "confidence": 0.75,
            "source_refs": [f"photo:{uuid.uuid4()}"],
        },
    )


def test_provider_request_is_exact_and_excludes_internal_authority():
    records = (_record(), _record(polarity="absent", severity="none"))
    request = PlantStateProviderRequestV1(
        records=records,
        source_refs=tuple(item.source_ref for item in records),
    )
    payload = request.as_provider_payload()
    assert list(payload) == ["schema_version", "agent_definition", "records", "source_refs"]
    assert payload["source_refs"] == [item["source_ref"] for item in payload["records"]]
    serialized = str(payload)
    for forbidden in (
        "confirmed_by_account_id",
        "membership_id",
        "session_id",
        "authorization_scope",
        "provider",
        "hidden_reasoning",
    ):
        assert forbidden not in serialized


def test_result_schema_rejects_unknown_fields_refs_and_invalid_matrix():
    record = _record()
    # The source-ref equality is itself strict.
    with pytest.raises(PlantStateValidationError):
        PlantStateProviderRequestV1(records=(record,), source_refs=())

    request = PlantStateProviderRequestV1(
        records=(record,),
        source_refs=(record.source_ref,),
    )
    refs = request.source_refs
    base = {
        "schema_version": 1,
        "runtime_decision": "speak",
        "assessment_kind": "unknown",
        "observation_key": "leaf_color_change",
        "direction": "not_applicable",
        "summary": "Evidence remains insufficient.",
        "confidence": 0.4,
        "source_refs": list(refs),
        "reason_code": None,
    }
    parsed = PlantStateModelResultV1.from_untrusted(base, request_source_refs=refs)
    assert parsed.assessment_kind == "unknown"
    for mutation in (
        {**base, "extra": "forbidden"},
        {**base, "source_refs": [f"plant_state_record:{uuid.uuid4()}"]},
        {**base, "assessment_kind": "conflict", "direction": "increasing"},
        {**base, "confidence": float("nan")},
    ):
        with pytest.raises(PlantStateValidationError):
            PlantStateModelResultV1.from_untrusted(mutation, request_source_refs=refs)


@dataclass
class _Evidence:
    observation_key: str
    polarity: str | None
    severity: str | None
    assessment_kind: str | None = None
    trust_status: str = "observed"


def test_structural_trend_conflict_unknown_matrix():
    trend = [
        _Evidence("leaf_spots", "present", "mild"),
        _Evidence("leaf_spots", "present", "moderate"),
    ]
    assert validate_structural_assessment(
        trend,
        assessment_kind="trend",
        observation_key="leaf_spots",
        direction="increasing",
    )
    assert not validate_structural_assessment(
        trend,
        assessment_kind="trend",
        observation_key="leaf_spots",
        direction="decreasing",
    )
    opposing = [
        _Evidence("wilting", "present", "mild"),
        _Evidence("wilting", "absent", "none"),
    ]
    assert validate_structural_assessment(
        opposing,
        assessment_kind="conflict",
        observation_key="wilting",
        direction="not_applicable",
    )
    unknown = [_Evidence("image_quality", "not_assessable", "unknown", trust_status="unknown")]
    assert validate_structural_assessment(
        unknown,
        assessment_kind="unknown",
        observation_key="image_quality",
        direction="not_applicable",
    )
