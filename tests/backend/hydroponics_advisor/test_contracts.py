from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import datetime, timezone
import uuid

import pytest

from backend.app.agent_runtime.roster import CANONICAL_ROSTER_V1
from backend.app.hydroponics_advisor import (
    HYDROPONICS_ADVISOR_DEFINITION_V1,
    AnalysisFreshnessV1,
    HydroponicsAdvisorInputRecordV1,
    HydroponicsAdvisorModelResultV1,
    HydroponicsAdvisorProviderRequestV1,
    HydroponicsAdvisorValidationError,
    MeasurementFreshnessV1,
)


NOW = "2026-07-20T00:00:00Z"
STALE = "2026-07-18T23:59:59Z"


def _plant(plant_id: uuid.UUID) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="plant",
        source_ref=f"plant:{plant_id}",
        payload={"plant_id": str(plant_id), "status": "active"},
    )


def _measurement(
    measurement_id: uuid.UUID,
    *,
    ph: str | None,
    ec: str | None,
    measured_at: str = NOW,
) -> HydroponicsAdvisorInputRecordV1:
    return HydroponicsAdvisorInputRecordV1(
        record_type="manual_measurement",
        source_ref=f"manual_measurement:{measurement_id}",
        payload={
            "measurement_id": str(measurement_id),
            "measured_at": measured_at,
            "recorded_at": NOW,
            "ph": ph,
            "ec_ms_cm": ec,
            "source_type": "manual_user",
            "trust_status": "confirmed",
        },
    )


def _request(*, missing_ph: bool = False) -> HydroponicsAdvisorProviderRequestV1:
    plant_id = uuid.uuid4()
    ph_id = uuid.uuid4()
    ec_id = uuid.uuid4()
    plant = _plant(plant_id)
    records = [plant]
    ph_ref = None
    if not missing_ph:
        ph = _measurement(ph_id, ph="6.50", ec=None)
        records.append(ph)
        ph_ref = ph.source_ref
    ec = _measurement(
        ec_id,
        ph=None,
        ec="1.250",
        measured_at=STALE if missing_ph else NOW,
    )
    records.append(ec)
    ph_freshness = MeasurementFreshnessV1(
        status="missing" if missing_ph else "fresh",
        source_ref=ph_ref,
        measured_at=None if missing_ph else NOW,
    )
    ec_freshness = MeasurementFreshnessV1(
        status="stale" if missing_ph else "fresh",
        source_ref=ec.source_ref,
        measured_at=STALE if missing_ph else NOW,
    )
    return HydroponicsAdvisorProviderRequestV1(
        request_reason="manual_review",
        analysis_goal="missing_data_review" if missing_ph else "general_hydroponics_review",
        computed_at=NOW,
        analysis_freshness=AnalysisFreshnessV1(
            computed_at=NOW,
            ph=ph_freshness,
            ec=ec_freshness,
            missing_or_stale=("ph", "ec") if missing_ph else (),
        ),
        records=tuple(records),
    )


def test_provider_definition_composes_exact_canonical_roster_metadata():
    request = _request()
    payload = request.as_provider_payload()
    roster_entry = next(
        item
        for item in CANONICAL_ROSTER_V1
        if item.agent_id == "hydroponics_advisor"
    )
    assert (
        HYDROPONICS_ADVISOR_DEFINITION_V1.agent_id,
        HYDROPONICS_ADVISOR_DEFINITION_V1.competence,
        HYDROPONICS_ADVISOR_DEFINITION_V1.output_schema_version,
    ) == (
        roster_entry.agent_id,
        roster_entry.competence_summary,
        roster_entry.output_schema_version,
    )
    assert payload["agent_definition"] == {
        "agent_id": roster_entry.agent_id,
        "competence": roster_entry.competence_summary,
        "instructions": HYDROPONICS_ADVISOR_DEFINITION_V1.instructions,
        "allowed_decisions": list(
            HYDROPONICS_ADVISOR_DEFINITION_V1.allowed_decisions
        ),
        "output_schema": {
            "name": "HydroponicsAdvisorModelResultV1",
            "schema_version": roster_entry.output_schema_version,
            "strict": True,
        },
    }


def test_definition_and_request_are_exact_and_exclude_caller_runtime_fields():
    request = _request()
    payload = request.as_provider_payload()
    assert "source_refs" not in {field.name for field in dataclass_fields(request)}
    assert list(payload) == [
        "schema_version",
        "agent_definition",
        "request_reason",
        "analysis_goal",
        "computed_at",
        "analysis_freshness",
        "records",
        "source_refs",
    ]
    serialized = str(payload)
    for forbidden in (
        "actor_context",
        "session_id",
        "membership_id",
        "grant_id",
        "provider_profile",
        "model_id",
        "base_url",
        "prompt",
        "authorization_scope",
    ):
        assert forbidden not in serialized


def test_missing_policy_accepts_only_exact_project_computed_result():
    request = _request(missing_ph=True)
    accepted = HydroponicsAdvisorModelResultV1.from_untrusted(
        {
            "schema_version": 1,
            "runtime_decision": "speak",
            "advice_kind": "measurement_request",
            "candidate_output": None,
            "confidence": None,
            "requested_measurements": ["ph", "ec"],
            "source_refs": list(request.policy_source_refs()),
            "reason_code": "critical_measurements_required",
        },
        request=request,
    )
    assert accepted.requested_measurements == ("ph", "ec")
    assert accepted.source_refs == request.policy_source_refs()

    invalid_values = [
        {
            "schema_version": 1,
            "runtime_decision": "silent",
            "advice_kind": None,
            "candidate_output": None,
            "confidence": None,
            "requested_measurements": [],
            "source_refs": [],
            "reason_code": "insufficient_evidence",
        },
        {
            "schema_version": 1,
            "runtime_decision": "speak",
            "advice_kind": "recommendation",
            "candidate_output": "Add nutrient.",
            "confidence": 0.9,
            "requested_measurements": [],
            "source_refs": list(request.source_refs),
            "reason_code": None,
        },
        {
            "schema_version": 1,
            "runtime_decision": "speak",
            "advice_kind": "measurement_request",
            "candidate_output": None,
            "confidence": None,
            "requested_measurements": ["ec", "ph"],
            "source_refs": list(request.policy_source_refs()),
            "reason_code": "critical_measurements_required",
        },
    ]
    for value in invalid_values:
        with pytest.raises(HydroponicsAdvisorValidationError):
            HydroponicsAdvisorModelResultV1.from_untrusted(value, request=request)


def test_fresh_policy_requires_both_measurement_refs_and_rejects_unknown_fields():
    request = _request()
    result = {
        "schema_version": 1,
        "runtime_decision": "speak",
        "advice_kind": "recommendation",
        "candidate_output": "<script>literal pending text</script>",
        "confidence": 0.7,
        "requested_measurements": [],
        "source_refs": list(request.source_refs),
        "reason_code": None,
    }
    accepted = HydroponicsAdvisorModelResultV1.from_untrusted(result, request=request)
    assert accepted.candidate_output == "<script>literal pending text</script>"

    missing_ref = {**result, "source_refs": [request.source_refs[0], request.source_refs[1]]}
    with pytest.raises(HydroponicsAdvisorValidationError):
        HydroponicsAdvisorModelResultV1.from_untrusted(missing_ref, request=request)
    with pytest.raises(HydroponicsAdvisorValidationError):
        HydroponicsAdvisorModelResultV1.from_untrusted(
            {**result, "provider": "forbidden"},
            request=request,
        )


def test_strict_records_reject_unknown_payload_and_freshness_mismatch():
    plant_id = uuid.uuid4()
    with pytest.raises(HydroponicsAdvisorValidationError):
        HydroponicsAdvisorInputRecordV1(
            record_type="plant",
            source_ref=f"plant:{plant_id}",
            payload={"plant_id": str(plant_id), "status": "active", "prompt": "x"},
        )
    with pytest.raises(HydroponicsAdvisorValidationError):
        AnalysisFreshnessV1(
            computed_at=datetime.now(timezone.utc).isoformat(),
            ph=MeasurementFreshnessV1("missing", None, None),
            ec=MeasurementFreshnessV1("fresh", f"manual_measurement:{uuid.uuid4()}", NOW),
            missing_or_stale=(),
        )
