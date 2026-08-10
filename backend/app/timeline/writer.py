from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any
import uuid

from ..config import AppSettings
from ..core.redaction import is_sensitive_key, redact_text


_EVENT_SOURCE_TYPES = {
    "daily_checkin_recorded": "daily_checkin",
    "manual_measurement_recorded": "manual_measurement",
    "photo_accepted": "photo_catalog_item",
    "agent_runtime_decided": "agent_runtime_attempt",
    "task_created": "task",
    "task_completed": "task",
    "approval_decided": "approval",
    "follow_up_outcome_recorded": "outcome",
    "companion_issue_opened": "companion_issue",
    "companion_proposal_created": "companion_proposal",
    "companion_proposal_superseded": "companion_proposal",
    "companion_decision_recorded": "decision_record",
    "companion_issue_resolved": "companion_issue",
    "companion_issue_closed": "companion_issue",
    "dataset_candidate_created": "dataset_candidate",
}


class TimelineAppendError(RuntimeError):
    """Safe timeline append failure."""

    def __init__(self) -> None:
        super().__init__("Timeline append failed.")


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    farm_id: uuid.UUID
    plant_id: uuid.UUID | None
    actor_ref: dict[str, object] | None
    event_type: str
    source_type: str
    source_id: uuid.UUID
    source_refs: dict[str, object]
    payload_summary: dict[str, object]


class TimelineJsonlAppender:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.from_env()

    def __call__(self, event: TimelineEvent) -> dict[str, object]:
        return append_timeline_event(event, settings=self._settings)


def append_timeline_event(
    event: TimelineEvent,
    *,
    settings: AppSettings | None = None,
) -> dict[str, object]:
    if not _event_shape_is_valid(event):
        raise TimelineAppendError

    timeline_event_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)
    source_refs, source_redacted = _sanitize_json(event.source_refs)
    payload_summary, payload_redacted = _sanitize_json(event.payload_summary)
    actor_ref, actor_redacted = _sanitize_json(event.actor_ref or {})
    record = {
        "timeline_event_id": str(timeline_event_id),
        "created_at": created_at.isoformat(),
        "farm_id": str(event.farm_id),
        "plant_id": str(event.plant_id) if event.plant_id is not None else None,
        "actor_ref": actor_ref,
        "event_type": event.event_type,
        "source_type": event.source_type,
        "source_id": str(event.source_id),
        "source_refs": source_refs,
        "payload_summary": payload_summary,
        "redaction_status": (
            "redacted" if source_redacted or payload_redacted or actor_redacted else "clean"
        ),
    }
    resolved_settings = settings or AppSettings.from_env()
    path = Path(resolved_settings.local_timeline_root) / "timeline.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            stream.write("\n")
    except OSError:
        raise TimelineAppendError from None
    return {
        "timeline_event_id": str(timeline_event_id),
        "timeline_ref": f"timeline.jsonl#{timeline_event_id}",
        "event_type": event.event_type,
        "created_at": created_at.isoformat(),
    }


def _event_shape_is_valid(event: object) -> bool:
    return (
        isinstance(event, TimelineEvent)
        and isinstance(event.farm_id, uuid.UUID)
        and (event.plant_id is None or isinstance(event.plant_id, uuid.UUID))
        and (event.actor_ref is None or isinstance(event.actor_ref, dict))
        and isinstance(event.source_id, uuid.UUID)
        and _EVENT_SOURCE_TYPES.get(event.event_type) == event.source_type
        and isinstance(event.source_refs, dict)
        and isinstance(event.payload_summary, dict)
    )


def _sanitize_json(value: Any) -> tuple[Any, bool]:
    if isinstance(value, dict):
        redacted = False
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            string_key = str(key)
            if is_sensitive_key(string_key):
                sanitized[string_key] = "***"
                redacted = True
                continue
            sanitized_value, item_redacted = _sanitize_json(item)
            sanitized[string_key] = sanitized_value
            redacted = redacted or item_redacted
        return sanitized, redacted
    if isinstance(value, list | tuple):
        redacted = False
        sanitized_items = []
        for item in value:
            sanitized_item, item_redacted = _sanitize_json(item)
            sanitized_items.append(sanitized_item)
            redacted = redacted or item_redacted
        return sanitized_items, redacted
    if isinstance(value, uuid.UUID):
        return str(value), False
    if isinstance(value, datetime):
        return value.isoformat(), False
    if isinstance(value, Decimal):
        return float(value), False
    if isinstance(value, str):
        redacted = redact_text(value)
        return redacted, redacted != value
    if value is None or isinstance(value, bool | int | float):
        return value, False
    return redact_text(str(value)), True
