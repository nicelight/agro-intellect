from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from backend.app import AppSettings
from backend.app.timeline import TimelineEvent, append_timeline_event


def test_timeline_writer_appends_registered_event_ref_and_redacts_payload(tmp_path):
    farm_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    ref = append_timeline_event(
        TimelineEvent(
            farm_id=farm_id,
            plant_id=plant_id,
            actor_ref={"account_id": str(uuid.uuid4()), "role_preset": "engineer"},
            event_type="manual_measurement_recorded",
            source_type="manual_measurement",
            source_id=source_id,
            source_refs={"farm_id": str(farm_id), "plant_id": str(plant_id)},
            payload_summary={
                "measured_at": datetime.now(timezone.utc),
                "ph": 6.4,
                "provenance_note": "device note password=plain-secret",
                "api_token": "plain-secret",
            },
        ),
        settings=AppSettings(local_timeline_root=tmp_path),
    )

    assert ref["event_type"] == "manual_measurement_recorded"
    assert ref["timeline_ref"] == f"timeline.jsonl#{ref['timeline_event_id']}"

    lines = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["farm_id"] == str(farm_id)
    assert record["plant_id"] == str(plant_id)
    assert record["source_id"] == str(source_id)
    assert record["redaction_status"] == "redacted"
    assert "plain-secret" not in lines[0]
    assert record["payload_summary"]["api_token"] == "***"
