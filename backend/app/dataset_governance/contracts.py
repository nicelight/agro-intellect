"""Strict W1 contracts for the Dataset Candidate creation seam."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import re
import uuid

from ..access_admin.actor_context import ActorContext


class CandidateStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_REVIEW = "needs_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXCLUDED = "excluded"


class CandidateOrigin(StrEnum):
    RAW = "raw"
    AGENT_LABELED = "agent_labeled"


class QualityTier(StrEnum):
    STANDARD = "standard"
    GOLD = "gold"


class Split(StrEnum):
    TRAIN = "train"
    EVAL = "eval"
    HOLDOUT = "holdout"


class ConfirmationSource(StrEnum):
    CURATOR_AUTO = "curator_auto"
    HUMAN_REVIEW = "human_review"
    EXPERT_REVIEW = "expert_review"
    BATCH_REVIEW = "batch_review"


class CandidateTransition(StrEnum):
    REQUEST_REVIEW = "request_review"
    CONFIRM = "confirm"
    REJECT = "reject"
    EXCLUDE = "exclude"


class SourceKind(StrEnum):
    PHOTO_CATALOG_ITEM = "photo_catalog_item"
    DAILY_CHECK_IN = "daily_check_in"
    MANUAL_MEASUREMENT = "manual_measurement"
    FOLLOW_UP_OUTCOME = "follow_up_outcome"


class CuratorDecision(StrEnum):
    SELECTED = "selected"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class DatasetGovernanceErrorCode(StrEnum):
    CANDIDATE_NOT_FOUND = "dataset_candidate_not_found"
    CANDIDATE_CONFLICT = "dataset_candidate_conflict"
    TRANSITION_FORBIDDEN = "dataset_transition_forbidden"
    EVIDENCE_INVALID = "dataset_evidence_invalid"
    CONFIRMATION_POLICY_VIOLATION = "dataset_confirmation_policy_violation"
    EVIDENCE_ASSOCIATION_CONFLICT = "dataset_evidence_association_conflict"
    TRAINABILITY_ASSIGN_FORBIDDEN = "dataset_trainability_assign_forbidden"
    CONTEXT_FORBIDDEN = "dataset_context_forbidden"
    AUDIT_FAILED = "dataset_audit_failed"
    PERSISTENCE_FAILED = "dataset_persistence_failed"
    INTERNAL_ERROR = "dataset_internal_error"


#: Outcome source ref shape (`kind:uuid`) validated by Task & Follow-Up.
SAFE_OUTCOME_REF_RE = re.compile(
    r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z"
)


class DatasetGovernanceError(RuntimeError):
    """Safe closed failure from the Dataset Governance boundary."""

    def __init__(self, code: DatasetGovernanceErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class DatasetGovernanceValidationError(ValueError):
    """An internal strict W1 handoff was malformed."""

    def __init__(self) -> None:
        super().__init__("Dataset Governance contract validation failed.")


@dataclass(frozen=True, slots=True)
class RecordDatasetEvidenceCommandV1:
    """Service-side creation seam input.

    The caller supplies only service-side identities (ActorContext, Plant,
    and the originating source row). No caller may pass ``candidate_status``,
    ``quality_tier``, ``confirmation_source``, ``can_train_on``, ``split``, or
    curator fields: those fields are structurally absent from this command and
    any attempt to supply them is rejected.
    """

    actor_context: ActorContext
    plant_id: uuid.UUID
    source_kind: SourceKind | str
    source_ref: uuid.UUID
    schema_version: int = 1

    def __post_init__(self) -> None:
        try:
            kind = SourceKind(self.source_kind)
        except (TypeError, ValueError):
            raise DatasetGovernanceValidationError() from None
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.source_ref, uuid.UUID)
        ):
            raise DatasetGovernanceValidationError()
        object.__setattr__(self, "source_kind", kind)


@dataclass(frozen=True, slots=True)
class RecordDatasetEvidenceResultV1:
    result: str
    candidate_id: uuid.UUID
    candidate_ref: str
    event_ref: Mapping[str, object]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.result not in {"created", "duplicate"}
            or not isinstance(self.candidate_id, uuid.UUID)
            or not isinstance(self.candidate_ref, str)
            or not isinstance(self.event_ref, Mapping)
        ):
            raise DatasetGovernanceValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "result": self.result,
            "candidate_id": str(self.candidate_id),
            "candidate_ref": self.candidate_ref,
            "event_ref": dict(self.event_ref),
        }


@dataclass(frozen=True, slots=True)
class TransitionDatasetCandidateCommandV1:
    """Service-side transition authority input.

    The caller supplies only service-side identities and the requested target
    transition with its expected current status/version. ``candidate_status``,
    ``can_train_on``, ``split``, and arbitrary confirmation/quality assignment
    are structurally absent: the target state is derived inside the authority.
    """

    actor_context: ActorContext
    candidate_id: uuid.UUID
    transition: CandidateTransition | str
    expected_status: CandidateStatus | str
    expected_record_version: int
    confirmation_source: ConfirmationSource | str | None = None
    quality_tier: QualityTier | str | None = None
    curator_run_id: uuid.UUID | None = None
    curator_command_sha256: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        try:
            transition = CandidateTransition(self.transition)
            expected_status = CandidateStatus(self.expected_status)
            confirmation_source = (
                ConfirmationSource(self.confirmation_source)
                if self.confirmation_source is not None
                else None
            )
            quality_tier = (
                QualityTier(self.quality_tier)
                if self.quality_tier is not None
                else None
            )
        except (TypeError, ValueError):
            raise DatasetGovernanceValidationError() from None
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.candidate_id, uuid.UUID)
            or not isinstance(self.expected_record_version, int)
            or self.expected_record_version <= 0
        ):
            raise DatasetGovernanceValidationError()
        if transition is CandidateTransition.CONFIRM:
            if confirmation_source is None:
                raise DatasetGovernanceValidationError()
            if confirmation_source is ConfirmationSource.CURATOR_AUTO:
                if (
                    not isinstance(self.curator_run_id, uuid.UUID)
                    or not isinstance(self.curator_command_sha256, str)
                    or len(self.curator_command_sha256) != 64
                ):
                    raise DatasetGovernanceValidationError()
        elif (
            confirmation_source is not None
            or quality_tier is not None
            or self.curator_run_id is not None
            or self.curator_command_sha256 is not None
        ):
            raise DatasetGovernanceValidationError()
        if (
            transition is not CandidateTransition.CONFIRM
            and quality_tier is not None
        ):
            raise DatasetGovernanceValidationError()
        object.__setattr__(self, "transition", transition)
        object.__setattr__(self, "expected_status", expected_status)
        if confirmation_source is not None:
            object.__setattr__(self, "confirmation_source", confirmation_source)
        if quality_tier is not None:
            object.__setattr__(self, "quality_tier", quality_tier)


@dataclass(frozen=True, slots=True)
class TransitionDatasetCandidateResultV1:
    result: str
    candidate_id: uuid.UUID
    candidate_ref: str
    from_status: str
    to_status: str
    can_train_on: bool
    event_ref: Mapping[str, object]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.result != "transitioned"
            or not isinstance(self.candidate_id, uuid.UUID)
            or not isinstance(self.candidate_ref, str)
            or not isinstance(self.from_status, str)
            or not isinstance(self.to_status, str)
            or not isinstance(self.can_train_on, bool)
            or not isinstance(self.event_ref, Mapping)
        ):
            raise DatasetGovernanceValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "result": self.result,
            "candidate_id": str(self.candidate_id),
            "candidate_ref": self.candidate_ref,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "can_train_on": self.can_train_on,
            "event_ref": dict(self.event_ref),
        }


@dataclass(frozen=True, slots=True)
class AssociateFollowUpEvidenceCommandV1:
    """Internal follow-up evidence association input.

    The caller supplies only service-side current ``ActorContext``, the active
    Plant identity, the already-locked Outcome row identity, and that Outcome's
    canonical ordered source refs. ``candidate_id`` selection, arbitrary
    evidence bodies, and every lifecycle/quality/split/confirmation/
    trainability field are structurally absent: targets are derived inside the
    authority from the supplied refs only.
    """

    actor_context: ActorContext
    plant_id: uuid.UUID
    outcome_id: uuid.UUID
    evidence_refs: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.outcome_id, uuid.UUID)
            or not isinstance(self.evidence_refs, tuple)
            or not 0 <= len(self.evidence_refs) <= 4
            or len(set(self.evidence_refs)) != len(self.evidence_refs)
            or any(
                not isinstance(item, str) or SAFE_OUTCOME_REF_RE.fullmatch(item) is None
                for item in self.evidence_refs
            )
        ):
            raise DatasetGovernanceValidationError()


@dataclass(frozen=True, slots=True)
class AssociateFollowUpEvidenceResultV1:
    """Ordered changed candidate ids plus the unchanged-match count."""

    result: str
    changed_candidate_ids: tuple[uuid.UUID, ...]
    unchanged_match_count: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.result not in {"associated", "noop"}
            or not isinstance(self.changed_candidate_ids, tuple)
            or not all(
                isinstance(item, uuid.UUID) for item in self.changed_candidate_ids
            )
            or not isinstance(self.unchanged_match_count, int)
            or self.unchanged_match_count < 0
        ):
            raise DatasetGovernanceValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "result": self.result,
            "changed_candidate_ids": [
                str(item) for item in self.changed_candidate_ids
            ],
            "unchanged_match_count": self.unchanged_match_count,
        }


__all__ = [
    "AssociateFollowUpEvidenceCommandV1",
    "AssociateFollowUpEvidenceResultV1",
    "CandidateOrigin",
    "CandidateStatus",
    "CandidateTransition",
    "ConfirmationSource",
    "CuratorDecision",
    "DatasetGovernanceError",
    "DatasetGovernanceErrorCode",
    "DatasetGovernanceValidationError",
    "QualityTier",
    "RecordDatasetEvidenceCommandV1",
    "RecordDatasetEvidenceResultV1",
    "SAFE_OUTCOME_REF_RE",
    "SourceKind",
    "Split",
    "TransitionDatasetCandidateCommandV1",
    "TransitionDatasetCandidateResultV1",
]
