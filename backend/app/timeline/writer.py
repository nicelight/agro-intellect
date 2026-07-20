from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
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
}
_SOURCE_REF_RE = re.compile(
    r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z"
)
_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


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
    base_is_valid = (
        isinstance(event, TimelineEvent)
        and isinstance(event.farm_id, uuid.UUID)
        and (event.plant_id is None or isinstance(event.plant_id, uuid.UUID))
        and isinstance(event.source_id, uuid.UUID)
        and _EVENT_SOURCE_TYPES.get(event.event_type) == event.source_type
        and isinstance(event.source_refs, dict)
        and isinstance(event.payload_summary, dict)
    )
    if not base_is_valid:
        return False
    if event.event_type == "agent_runtime_decided":
        return _agent_runtime_event_is_valid(event)
    if event.event_type in {
        "task_created",
        "task_completed",
        "approval_decided",
        "follow_up_outcome_recorded",
    }:
        return _task_loop_event_is_valid(event)
    return True


def _task_loop_event_is_valid(event: TimelineEvent) -> bool:
    if event.plant_id is None or not _actor_ref_is_valid(event.actor_ref):
        return False
    refs = event.source_refs.get("record_refs")
    if (
        set(event.source_refs) != {"record_refs"}
        or not isinstance(refs, list)
        or len(refs) > 12
        or len(refs) != len(set(refs))
        or any(not isinstance(ref, str) or _SOURCE_REF_RE.fullmatch(ref) is None for ref in refs)
    ):
        return False
    payload = event.payload_summary
    if event.event_type == "task_created":
        return (
            set(payload) == {"task_kind", "task_source_type", "due_at", "source_ref_count"}
            and payload["task_kind"] in {"check", "measurement", "action", "follow_up"}
            and payload["task_source_type"] in {
                "safe_task_request", "approved_action", "automatic_follow_up"
            }
            and (payload["due_at"] is None or isinstance(payload["due_at"], str))
            and payload["source_ref_count"] == len(refs)
        )
    if event.event_type == "task_completed":
        return (
            set(payload) == {"task_kind", "completion_kind", "source_ref_count"}
            and payload["task_kind"] in {"check", "measurement", "action", "follow_up"}
            and payload["completion_kind"] in {"ordinary", "action", "outcome"}
            and payload["source_ref_count"] == len(refs)
        )
    if event.event_type == "approval_decided":
        return (
            set(payload) == {"decision", "action_kind", "record_version", "action_task_id"}
            and payload["decision"] in {"approved", "rejected"}
            and payload["action_kind"] in {"ph_adjustment", "ec_adjustment", "solution_change"}
            and payload["record_version"] == 2
            and (
                _canonical_uuid_text(payload["action_task_id"])
                if payload["decision"] == "approved"
                else payload["action_task_id"] is None
            )
        )
    return (
        set(payload) == {"follow_up_task_id", "outcome_value", "evidence_ref_count"}
        and _canonical_uuid_text(payload["follow_up_task_id"])
        and payload["outcome_value"] in {"improved", "worsened", "unchanged", "no_data"}
        and isinstance(payload["evidence_ref_count"], int)
        and not isinstance(payload["evidence_ref_count"], bool)
        and 0 <= payload["evidence_ref_count"] <= 4
        and payload["evidence_ref_count"] == len(refs)
    )


def _agent_runtime_event_is_valid(event: TimelineEvent) -> bool:
    if event.plant_id is None or not _actor_ref_is_valid(event.actor_ref):
        return False
    if event.source_id.version != 4:
        return False
    input_refs = event.source_refs.get("input_refs")
    if (
        set(event.source_refs) != {"input_refs"}
        or not isinstance(input_refs, list)
        or not 1 <= len(input_refs) <= 4
        or len(input_refs) != len(set(input_refs))
        or any(not _agent_input_ref_is_valid(item) for item in input_refs)
    ):
        return False
    payload = event.payload_summary
    expected_keys = {
        "agent_id",
        "model_ref",
        "outcome_kind",
        "candidate_decision",
        "final_decision",
        "outcome_status",
        "reason_code",
        "error_code",
        "message_id",
        "candidate_claim_type",
        "source_ref_count",
    }
    if set(payload) != expected_keys:
        return False
    if (
        not isinstance(payload["agent_id"], str)
        or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", payload["agent_id"])
        or not isinstance(payload["model_ref"], str)
        or _MODEL_REF_RE.fullmatch(payload["model_ref"]) is None
        or isinstance(payload["source_ref_count"], bool)
        or not isinstance(payload["source_ref_count"], int)
        or payload["source_ref_count"] != len(input_refs)
    ):
        return False
    return _agent_runtime_payload_matrix_is_valid(payload)


def _actor_ref_is_valid(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "account_id",
        "membership_id",
        "role_preset",
    }:
        return False
    return (
        _canonical_uuid_text(value["account_id"])
        and _canonical_uuid_text(value["membership_id"])
        and value["role_preset"] in {"boss", "engineer", "consultant"}
    )


def _agent_runtime_payload_matrix_is_valid(payload: dict[str, object]) -> bool:
    kind = payload["outcome_kind"]
    candidate = payload["candidate_decision"]
    final = payload["final_decision"]
    status = payload["outcome_status"]
    reason = payload["reason_code"]
    error = payload["error_code"]
    message_id = payload["message_id"]
    claim = payload["candidate_claim_type"]
    claims = {
        "observation",
        "hypothesis",
        "recommendation",
        "clarification",
        "task_request",
        "safety_block",
        "team_signal",
    }
    if kind == "envelope_ready":
        return (
            candidate in {"speak", "clarify", "escalate"}
            and final == candidate
            and status == "envelope_ready"
            and reason == "envelope_ready"
            and error is None
            and _canonical_uuid_text(message_id)
            and _claim_matches_decision(candidate, claim, claims)
        )
    if kind == "model_silent":
        return (
            candidate == "silent"
            and final == "silent"
            and status == "silent"
            and reason in {"no_material_output", "insufficient_evidence"}
            and error is None
            and message_id is None
            and claim is None
        )
    if kind == "provider_failed":
        return (
            candidate is None
            and final is None
            and status == "failed"
            and reason == "provider_failed"
            and error == "AGENT_PROVIDER_FAILED"
            and message_id is None
            and claim is None
        )
    if kind == "output_invalid":
        return (
            candidate is None
            and final is None
            and status == "blocked"
            and reason == "output_invalid"
            and error == "AGENT_OUTPUT_INVALID"
            and message_id is None
            and claim is None
        )
    if kind == "publication_guard_denied":
        return (
            candidate in {"speak", "silent", "clarify", "escalate"}
            and final is None
            and status == "blocked"
            and reason == "publication_guard_denied"
            and error == "AGENT_PUBLICATION_BLOCKED"
            and message_id is None
            and (claim is None if candidate == "silent" else _claim_matches_decision(candidate, claim, claims))
        )
    return False


def _canonical_uuid_text(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return str(parsed) == value


def _agent_input_ref_is_valid(value: object) -> bool:
    if not isinstance(value, str) or _SOURCE_REF_RE.fullmatch(value) is None:
        return False
    kind, identifier = value.split(":", maxsplit=1)
    return kind in {"plant", "daily_checkin", "manual_measurement"} and _canonical_uuid_text(identifier)


def _claim_matches_decision(
    decision: object,
    claim: object,
    claims: set[str],
) -> bool:
    if claim not in claims:
        return False
    if decision == "speak":
        return claim in {"observation", "hypothesis", "recommendation", "task_request", "team_signal"}
    if decision == "clarify":
        return claim == "clarification"
    if decision == "escalate":
        return claim in {"safety_block", "team_signal"}
    return False


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
