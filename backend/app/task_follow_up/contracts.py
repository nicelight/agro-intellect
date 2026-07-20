"""Strict internal contracts for the authoritative FT-012 task loop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable
import unicodedata
import uuid

from ..access_admin.actor_context import ActorContext
from ..agent_runtime.contracts import MessageEnvelopeV1, SafetyClassificationResultV1


SAFE_REF_RE = re.compile(
    r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z"
)


class TaskKind(StrEnum):
    CHECK = "check"
    MEASUREMENT = "measurement"
    ACTION = "action"
    FOLLOW_UP = "follow_up"


class TaskStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OutcomeValue(StrEnum):
    IMPROVED = "improved"
    WORSENED = "worsened"
    UNCHANGED = "unchanged"
    NO_DATA = "no_data"


class TaskFollowUpErrorCode(StrEnum):
    TASK_REQUEST_INVALID = "TASK_REQUEST_INVALID"
    TASK_SCOPE_NOT_FOUND = "TASK_SCOPE_NOT_FOUND"
    TASK_COMMAND_FORBIDDEN = "TASK_COMMAND_FORBIDDEN"
    TASK_PLANT_NOT_ACTIVE = "TASK_PLANT_NOT_ACTIVE"
    TASK_SOURCE_INVALID = "TASK_SOURCE_INVALID"
    APPROVAL_NOT_CURRENT = "APPROVAL_NOT_CURRENT"
    TASK_VERSION_CONFLICT = "TASK_VERSION_CONFLICT"
    TASK_INVALID_TRANSITION = "TASK_INVALID_TRANSITION"
    TASK_EVIDENCE_REQUIRED = "TASK_EVIDENCE_REQUIRED"
    TASK_AUDIT_FAILED = "TASK_AUDIT_FAILED"
    TASK_PERSISTENCE_FAILED = "TASK_PERSISTENCE_FAILED"


class TaskFollowUpError(RuntimeError):
    def __init__(self, code: TaskFollowUpErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class ClassifiedMessageTaskCommandV1:
    actor_context: ActorContext
    message_envelope: MessageEnvelopeV1
    classification: SafetyClassificationResultV1
    task_kind: TaskKind
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.message_envelope, MessageEnvelopeV1)
            or not isinstance(self.classification, SafetyClassificationResultV1)
            or not isinstance(self.task_kind, TaskKind)
            or self.task_kind is TaskKind.ACTION
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)


@dataclass(frozen=True, slots=True)
class ApprovalDecisionCommandV1:
    actor_context: ActorContext
    plant_id: uuid.UUID
    safety_decision_id: uuid.UUID
    request_id: uuid.UUID
    expected_version: int
    decision: ApprovalStatus
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not all(
                isinstance(item, uuid.UUID)
                for item in (self.plant_id, self.safety_decision_id, self.request_id)
            )
            or self.request_id.version != 4
            or self.expected_version < 1
            or self.decision not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)


@dataclass(frozen=True, slots=True)
class CompleteTaskCommandV1:
    actor_context: ActorContext
    plant_id: uuid.UUID
    task_id: uuid.UUID
    request_id: uuid.UUID
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not all(
                isinstance(item, uuid.UUID)
                for item in (self.plant_id, self.task_id, self.request_id)
            )
            or self.request_id.version != 4
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)


@dataclass(frozen=True, slots=True)
class RecordOutcomeCommandV1:
    actor_context: ActorContext
    plant_id: uuid.UUID
    follow_up_task_id: uuid.UUID
    request_id: uuid.UUID
    value: OutcomeValue
    evidence_refs: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not all(
                isinstance(item, uuid.UUID)
                for item in (self.plant_id, self.follow_up_task_id, self.request_id)
            )
            or self.request_id.version != 4
            or not isinstance(self.value, OutcomeValue)
            or not isinstance(self.evidence_refs, tuple)
            or not 0 <= len(self.evidence_refs) <= 4
            or len(set(self.evidence_refs)) != len(self.evidence_refs)
            or any(not safe_ref(item) for item in self.evidence_refs)
        ):
            raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)


@dataclass(frozen=True, slots=True)
class OrdinaryTaskCreateResultV1:
    result: str
    task: object
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.result not in {"created", "duplicate"}:
            raise ValueError("Invalid ordinary Task result.")


@dataclass(frozen=True, slots=True)
class ApprovalDecisionResultV1:
    result: str
    approval: object
    action_task: object | None
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class CompleteTaskResultV1:
    result: str
    task: object
    follow_up_task: object | None
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class RecordOutcomeResultV1:
    result: str
    task: object
    outcome: object
    schema_version: int = 1


def canonical_fingerprint(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def canonical_uuid(value: uuid.UUID) -> str:
    return str(value)


def timestamp_text(value: datetime) -> str:
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if normalized.utcoffset() is None:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_REQUEST_INVALID)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_display_text(value: object) -> str:
    if not isinstance(value, str):
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
    normalized = unicodedata.normalize("NFC", value).strip()
    if not 1 <= len(normalized) <= 2000:
        raise TaskFollowUpError(TaskFollowUpErrorCode.TASK_SOURCE_INVALID)
    return normalized


def safe_ref(value: object) -> bool:
    if not isinstance(value, str) or SAFE_REF_RE.fullmatch(value) is None:
        return False
    _kind, identifier = value.split(":", maxsplit=1)
    try:
        return str(uuid.UUID(identifier)) == identifier
    except (ValueError, TypeError, AttributeError):
        return False


def ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


__all__ = [
    "ApprovalDecisionCommandV1",
    "ApprovalDecisionResultV1",
    "ApprovalStatus",
    "ClassifiedMessageTaskCommandV1",
    "CompleteTaskCommandV1",
    "CompleteTaskResultV1",
    "OrdinaryTaskCreateResultV1",
    "OutcomeValue",
    "RecordOutcomeCommandV1",
    "RecordOutcomeResultV1",
    "TaskFollowUpError",
    "TaskFollowUpErrorCode",
    "TaskKind",
    "TaskStatus",
    "canonical_fingerprint",
    "normalized_display_text",
    "ordered_unique",
    "safe_ref",
    "timestamp_text",
]
