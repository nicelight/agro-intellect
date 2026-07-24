"""Strict W1 contracts for Plant-scoped Companion governance authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import re
import unicodedata
import uuid

from ..access_admin.actor_context import ActorContext


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REF_RE = re.compile(
    r"^(plant|daily_checkin|manual_measurement|companion_issue):"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
)


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AttentionStatus(StrEnum):
    ACTIVE = "active"
    SATISFIED = "satisfied"


class ProposalState(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProposalEffect(StrEnum):
    DISCUSSION_ONLY = "discussion_only"
    CHECK = "check"
    MEASUREMENT = "measurement"
    FOLLOW_UP = "follow_up"
    NONE = "none"


class SuggestedResolution(StrEnum):
    KEEP_OPEN = "keep_open"
    RESOLVED = "resolved"


class CompanionGovernanceErrorCode(StrEnum):
    COMMAND_FORBIDDEN = "COMPANION_COMMAND_FORBIDDEN"
    PLANT_NOT_ACTIVE = "COMPANION_PLANT_NOT_ACTIVE"
    ISSUE_NOT_OPEN = "COMPANION_ISSUE_NOT_OPEN"
    PROPOSAL_NOT_CURRENT = "COMPANION_PROPOSAL_NOT_CURRENT"
    VERSION_CONFLICT = "COMPANION_VERSION_CONFLICT"
    EFFECT_INVALID = "COMPANION_EFFECT_INVALID"
    READ_INCONSISTENT = "COMPANION_READ_INCONSISTENT"
    AUDIT_FAILED = "COMPANION_AUDIT_FAILED"
    PERSISTENCE_FAILED = "COMPANION_PERSISTENCE_FAILED"


class CompanionGovernanceError(RuntimeError):
    """Safe closed failure from the Companion governance boundary."""

    def __init__(self, code: CompanionGovernanceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class CompanionGovernanceValidationError(ValueError):
    """An internal strict W1 handoff or view was malformed."""

    def __init__(self) -> None:
        super().__init__("Companion governance contract validation failed.")


@dataclass(frozen=True, slots=True)
class PersistCompanionProposalCommandV1:
    """Validated runtime/classification handoff accepted by the W1 writer.

    The caller supplies no authorization, projection, Timeline, or effect
    routing fields. Current authority and persisted classification are reloaded
    by the service inside the write transaction.
    """

    actor_context: ActorContext
    run_id: uuid.UUID
    message_id: uuid.UUID
    plant_id: uuid.UUID
    target_issue_id: uuid.UUID | None
    expected_issue_version: int | None
    issue_summary_text: str | None
    attention_summary_text: str
    proposal_summary: str
    proposal_text: str
    rationale_text: str | None
    proposed_effect: ProposalEffect | str
    task_display_text: str | None
    suggested_resolution: SuggestedResolution | str
    provider_input_refs: tuple[str, ...]
    run_request_fingerprint: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        try:
            effect = ProposalEffect(self.proposed_effect)
            resolution = SuggestedResolution(self.suggested_resolution)
        except (TypeError, ValueError):
            raise CompanionGovernanceValidationError() from None
        object.__setattr__(self, "proposed_effect", effect)
        object.__setattr__(self, "suggested_resolution", resolution)

        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not _uuid4(self.run_id)
            or not _uuid4(self.message_id)
            or not isinstance(self.plant_id, uuid.UUID)
            or not _SHA256_RE.fullmatch(self.run_request_fingerprint)
        ):
            raise CompanionGovernanceValidationError()

        if self.target_issue_id is None:
            if self.expected_issue_version is not None:
                raise CompanionGovernanceValidationError()
            normalized_issue = normalize_text(self.issue_summary_text, maximum=500)
        else:
            if (
                not isinstance(self.target_issue_id, uuid.UUID)
                or not _positive_int(self.expected_issue_version)
                or self.issue_summary_text is not None
            ):
                raise CompanionGovernanceValidationError()
            normalized_issue = None

        attention = normalize_text(self.attention_summary_text, maximum=500)
        proposal_summary = normalize_text(self.proposal_summary, maximum=500)
        proposal_text = normalize_text(self.proposal_text, maximum=2000)
        rationale = (
            normalize_text(self.rationale_text, maximum=2000)
            if self.rationale_text is not None
            else None
        )
        task_text = (
            normalize_text(self.task_display_text, maximum=2000)
            if self.task_display_text is not None
            else None
        )
        if (effect in _TASK_EFFECTS) is not (task_text is not None):
            raise CompanionGovernanceValidationError()

        refs = validate_provider_input_refs(
            self.provider_input_refs,
            plant_id=self.plant_id,
            target_issue_id=self.target_issue_id,
        )
        object.__setattr__(self, "issue_summary_text", normalized_issue)
        object.__setattr__(self, "attention_summary_text", attention)
        object.__setattr__(self, "proposal_summary", proposal_summary)
        object.__setattr__(self, "proposal_text", proposal_text)
        object.__setattr__(self, "rationale_text", rationale)
        object.__setattr__(self, "task_display_text", task_text)
        object.__setattr__(self, "provider_input_refs", refs)

    @property
    def proposal_source_refs(self) -> tuple[str, ...]:
        return (
            *self.provider_input_refs,
            f"message_envelope:{self.message_id}",
            f"safety_classification:{self.message_id}",
        )


@dataclass(frozen=True, slots=True)
class ProposalPersistenceResultV1:
    result: str
    issue_id: uuid.UUID
    attention_id: uuid.UUID
    proposal_id: uuid.UUID
    classification_message_id: uuid.UUID
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.result not in {"created", "duplicate"}
            or any(
                not isinstance(item, uuid.UUID)
                for item in (
                    self.issue_id,
                    self.attention_id,
                    self.proposal_id,
                    self.classification_message_id,
                )
            )
        ):
            raise CompanionGovernanceValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "result": self.result,
            "issue_ref": f"companion_issue:{self.issue_id}",
            "attention_ref": f"companion_attention:{self.attention_id}",
            "proposal_ref": f"companion_proposal:{self.proposal_id}",
            "classification_ref": (
                f"safety_classification:{self.classification_message_id}"
            ),
        }


@dataclass(frozen=True, slots=True)
class IssueStackPageV1:
    plant_id: uuid.UUID
    focused_issue_ref: str | None
    items: tuple[Mapping[str, object], ...]
    next_cursor: str | None
    schema_version: int = 1

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "plant_id": str(self.plant_id),
            "focused_issue_ref": self.focused_issue_ref,
            "items": [dict(item) for item in self.items],
            "next_cursor": self.next_cursor,
        }


@dataclass(frozen=True, slots=True)
class CompanionIssueDetailV1:
    issue: Mapping[str, object]
    attention: Mapping[str, object] | None
    proposals: tuple[Mapping[str, object], ...]
    decision_records: tuple[Mapping[str, object], ...]
    conclusion: Mapping[str, object]
    schema_version: int = 1

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "issue": dict(self.issue),
            "attention": dict(self.attention) if self.attention is not None else None,
            "proposals": [dict(item) for item in self.proposals],
            "decision_records": [dict(item) for item in self.decision_records],
            "conclusion": dict(self.conclusion),
        }


def normalize_text(value: object, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise CompanionGovernanceValidationError()
    normalized = value.strip()
    if (
        not 1 <= len(normalized) <= maximum
        or any(unicodedata.category(character).startswith("C") for character in normalized)
    ):
        raise CompanionGovernanceValidationError()
    return normalized


def validate_provider_input_refs(
    value: object,
    *,
    plant_id: uuid.UUID,
    target_issue_id: uuid.UUID | None,
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CompanionGovernanceValidationError()
    refs = tuple(value)
    if not 1 <= len(refs) <= 4 or len(set(refs)) != len(refs):
        raise CompanionGovernanceValidationError()
    kinds: list[str] = []
    for ref in refs:
        if not isinstance(ref, str):
            raise CompanionGovernanceValidationError()
        match = _REF_RE.fullmatch(ref)
        if match is None:
            raise CompanionGovernanceValidationError()
        try:
            parsed = uuid.UUID(match.group(2))
        except ValueError:
            raise CompanionGovernanceValidationError() from None
        if str(parsed) != match.group(2):
            raise CompanionGovernanceValidationError()
        kinds.append(match.group(1))

    required_kinds = (
        ("plant",)
        if target_issue_id is None
        else ("plant", "companion_issue")
    )
    optional_kinds = tuple(kinds[len(required_kinds) :])
    if (
        tuple(kinds[: len(required_kinds)]) != required_kinds
        or optional_kinds
        not in {
            (),
            ("daily_checkin",),
            ("manual_measurement",),
            ("daily_checkin", "manual_measurement"),
        }
    ):
        raise CompanionGovernanceValidationError()
    if refs[0] != f"plant:{plant_id}":
        raise CompanionGovernanceValidationError()
    if (
        target_issue_id is not None
        and refs[1] != f"companion_issue:{target_issue_id}"
    ):
        raise CompanionGovernanceValidationError()
    return refs


def timestamp_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def exact_mapping(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise CompanionGovernanceValidationError()
    return dict(value)


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


_TASK_EFFECTS = frozenset(
    {ProposalEffect.CHECK, ProposalEffect.MEASUREMENT, ProposalEffect.FOLLOW_UP}
)


__all__ = [
    "AttentionStatus",
    "CompanionGovernanceError",
    "CompanionGovernanceErrorCode",
    "CompanionGovernanceValidationError",
    "CompanionIssueDetailV1",
    "IssueStackPageV1",
    "IssueStatus",
    "PersistCompanionProposalCommandV1",
    "ProposalEffect",
    "ProposalPersistenceResultV1",
    "ProposalState",
    "SuggestedResolution",
    "normalize_text",
    "timestamp_text",
]
