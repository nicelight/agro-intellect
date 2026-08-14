from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

import pytest

from backend.app import AppSettings
from backend.app.timeline import TimelineAppendError, TimelineEvent, append_timeline_event

CORPUS_DB_PASSWORD = "corpus-timeline-db-pw-5q8t"
CORPUS_ENV_SECRET = "corpus-timeline-env-secret-2x9k"
CORPUS_BEARER = "corpus-timeline-bearer-w4m6"
CORPUS_API_KEY = "corpus-timeline-api-key-8n3p"
CORPUS_SESSION_TOKEN = "corpus-timeline-session-token-6d3f"

CORPUS = [
    CORPUS_DB_PASSWORD,
    CORPUS_ENV_SECRET,
    CORPUS_BEARER,
    CORPUS_API_KEY,
    CORPUS_SESSION_TOKEN,
]


class _Unrenderable(str):
    def __str__(self) -> str:
        raise ValueError(f"boom {CORPUS_ENV_SECRET}")


def _timeline_event(farm_id, plant_id, source_id) -> TimelineEvent:
    return TimelineEvent(
        farm_id=farm_id,
        plant_id=plant_id,
        actor_ref={"account_id": str(uuid.uuid4()), "role_preset": "engineer"},
        event_type="manual_measurement_recorded",
        source_type="manual_measurement",
        source_id=source_id,
        source_refs={
            "farm_id": str(farm_id),
            "plant_id": str(plant_id),
            "note": f"Bearer {CORPUS_BEARER} password={CORPUS_DB_PASSWORD}",
        },
        payload_summary={
            "measured_at": datetime.now(timezone.utc),
            "ph": 6.4,
            "provenance_note": (
                f"password={CORPUS_DB_PASSWORD} env={CORPUS_ENV_SECRET} "
                f"key={CORPUS_API_KEY} token={CORPUS_SESSION_TOKEN} "
                f"Authorization: Bearer {CORPUS_BEARER}"
            ),
            "api_token": CORPUS_SESSION_TOKEN,
            "safe_note": "no secrets here",
        },
    )


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


def test_timeline_writer_removes_configured_corpus_before_append(tmp_path, monkeypatch):
    monkeypatch.setenv("AGRO_TIMELINE_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    monkeypatch.setenv("AGRO_TIMELINE_CORPUS_API_KEY", CORPUS_API_KEY)
    monkeypatch.setenv("AGRO_TIMELINE_CORPUS_SESSION", CORPUS_SESSION_TOKEN)
    monkeypatch.setenv("AGRO_TIMELINE_CORPUS_DB_URL", CORPUS_DB_PASSWORD)
    farm_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    source_id = uuid.uuid4()
    event = _timeline_event(farm_id, plant_id, source_id)
    payload_before = dict(event.payload_summary)
    source_refs_before = dict(event.source_refs)

    ref = append_timeline_event(
        event,
        settings=AppSettings(local_timeline_root=tmp_path),
    )

    assert ref["event_type"] == "manual_measurement_recorded"
    assert ref["timeline_ref"] == f"timeline.jsonl#{ref['timeline_event_id']}"
    assert ref["created_at"]

    line = (tmp_path / "timeline.jsonl").read_text(encoding="utf-8")
    for raw in CORPUS:
        assert raw not in line
    assert "***" in line

    record = json.loads(line.splitlines()[0])
    assert record["redaction_status"] == "redacted"
    assert record["event_type"] == "manual_measurement_recorded"
    assert record["source_type"] == "manual_measurement"
    assert record["source_id"] == str(source_id)
    assert record["farm_id"] == str(farm_id)
    assert record["plant_id"] == str(plant_id)
    assert record["timeline_event_id"] == ref["timeline_event_id"]
    assert record["payload_summary"]["api_token"] == "***"
    assert record["payload_summary"]["safe_note"] == "no secrets here"
    assert record["payload_summary"]["ph"] == 6.4
    assert payload_before == event.payload_summary
    assert source_refs_before == event.source_refs


def test_timeline_append_failure_uses_registered_error_without_echo(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGRO_TIMELINE_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    farm_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    source_id = uuid.uuid4()

    blocking_root = tmp_path / "blocked"
    blocking_root.mkdir(parents=True)
    (blocking_root / "timeline.jsonl").mkdir()

    with pytest.raises(TimelineAppendError) as exc_info:
        append_timeline_event(
            _timeline_event(farm_id, plant_id, source_id),
            settings=AppSettings(local_timeline_root=blocking_root),
        )
    message = str(exc_info.value)
    assert message == "Timeline append failed."
    for raw in CORPUS:
        assert raw not in message

    with pytest.raises(TimelineAppendError) as exc_info:
        append_timeline_event(
            TimelineEvent(
                farm_id=farm_id,
                plant_id=None,
                actor_ref=None,
                event_type="not_registered_type",
                source_type="manual_measurement",
                source_id=source_id,
                source_refs={},
                payload_summary={},
            ),
            settings=AppSettings(local_timeline_root=tmp_path / "shaped"),
        )
    message = str(exc_info.value)
    assert message == "Timeline append failed."
    for raw in CORPUS:
        assert raw not in message

    unrenderable_root = tmp_path / "unrenderable"
    event = _timeline_event(farm_id, plant_id, source_id)
    event.payload_summary["note"] = _Unrenderable(CORPUS_ENV_SECRET)
    with pytest.raises(TimelineAppendError) as exc_info:
        append_timeline_event(
            event,
            settings=AppSettings(local_timeline_root=unrenderable_root),
        )
    message = str(exc_info.value)
    assert message == "Timeline append failed."
    for raw in CORPUS:
        assert raw not in message
    assert not (unrenderable_root / "timeline.jsonl").exists()
