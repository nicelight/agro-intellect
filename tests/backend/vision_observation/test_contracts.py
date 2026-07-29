from __future__ import annotations

from dataclasses import fields as dataclass_fields
from datetime import datetime, timezone
import hashlib
import json
import uuid

import pytest

from backend.app.vision_observation import (
    VISION_OBSERVATION_DEFINITION_V1,
    VisionInputRecordV1,
    VisionMediaV1,
    VisionObservationModelResultV1,
    VisionObservationValidationError,
    VisionProviderRequestV1,
    VisionStateCandidateV1,
)


def _request():
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    plant = VisionInputRecordV1(
        record_type="plant",
        source_ref=f"plant:{plant_id}",
        payload={"plant_id": str(plant_id), "status": "active"},
    )
    photo = VisionInputRecordV1(
        record_type="photo",
        source_ref=f"photo:{photo_id}",
        payload={
            "photo_id": str(photo_id),
            "plant_id": str(plant_id),
            "photo_type": "leaf_closeup",
            "captured_at": "2026-07-18T08:00:00Z",
            "content_type": "image/jpeg",
            "size_bytes": 4,
            "sha256": hashlib.sha256(b"jpeg").hexdigest(),
            "local_only": True,
        },
    )
    return VisionProviderRequestV1(records=(plant, photo))


def test_request_and_media_are_exact_ordered_and_bytes_are_not_json():
    request = _request()
    payload = request.as_provider_payload()
    assert list(payload) == ["schema_version", "agent_definition", "records", "source_refs"]
    assert [item["record_type"] for item in payload["records"]] == ["plant", "photo"]
    assert payload["source_refs"] == [item["source_ref"] for item in payload["records"]]
    assert "source_refs" not in {field.name for field in dataclass_fields(request)}
    assert payload["agent_definition"] == {
        "agent_id": "vision_observation",
        "competence": VISION_OBSERVATION_DEFINITION_V1.competence,
        "instructions": VISION_OBSERVATION_DEFINITION_V1.instructions,
        "allowed_decisions": ["speak", "clarify", "silent"],
        "output_schema": {
            "name": "VisionObservationModelResultV1",
            "schema_version": 1,
            "strict": True,
        },
    }
    content = b"BINARY_SENTINEL_NOT_JSON"
    media = VisionMediaV1(
        source_ref=request.source_refs[1],
        content_type="image/jpeg",
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )
    assert media.content == content
    assert content not in json.dumps(payload).encode()


@pytest.mark.parametrize(
    ("decision", "fields"),
    [
        (
            "speak",
            {
                "observation_key": "leaf_spots",
                "polarity": "present",
                "severity": "mild",
                "summary": "Visible small brown spots are present.",
                "confidence": 0.72,
                "reason_code": None,
            },
        ),
        (
            "clarify",
            {
                "observation_key": "image_quality",
                "polarity": "not_assessable",
                "severity": "unknown",
                "summary": "The leaf is not visible clearly enough.",
                "confidence": None,
                "reason_code": None,
            },
        ),
        (
            "silent",
            {
                "observation_key": None,
                "polarity": None,
                "severity": None,
                "summary": None,
                "confidence": None,
                "reason_code": "no_material_output",
            },
        ),
    ],
)
def test_result_matrix_accepts_only_closed_decisions(decision, fields):
    result = VisionObservationModelResultV1.from_untrusted(
        {
            "schema_version": 1,
            "runtime_decision": decision,
            **fields,
        },
    )
    assert result.runtime_decision == decision
    assert "source_refs" not in result.as_value()


@pytest.mark.parametrize(
    "mutation",
    [
        {"diagnosis": "disease"},
        {"recommendation": "spray leaves"},
        {"polarity": "absent", "severity": "strong"},
        {"source_refs": [f"photo:{uuid.uuid4()}"]},
    ],
)
def test_result_rejects_unknown_action_fields_and_incompatible_values(mutation):
    value = {
        "schema_version": 1,
        "runtime_decision": "speak",
        "observation_key": "leaf_spots",
        "polarity": "present",
        "severity": "mild",
        "summary": "Small spots are visible.",
        "confidence": 0.8,
        "reason_code": None,
    }
    value.update(mutation)
    with pytest.raises(VisionObservationValidationError):
        VisionObservationModelResultV1.from_untrusted(value)


def test_state_candidate_is_non_authoritative_closed_value():
    candidate = VisionStateCandidateV1(
        run_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
        observation_key="leaf_color_change",
        polarity="uncertain",
        severity="unknown",
        summary="Pale areas may be visible.",
        confidence=0.49,
        source_refs=(f"photo:{uuid.uuid4()}",),
        observed_at=datetime.now(timezone.utc),
    )
    assert set(candidate.as_value()) == {
        "schema_version",
        "run_id",
        "message_id",
        "observation_key",
        "polarity",
        "severity",
        "summary",
        "confidence",
        "source_refs",
        "observed_at",
    }
    assert "trust" not in str(candidate.as_value())
    assert "confirmed" not in str(candidate.as_value())
