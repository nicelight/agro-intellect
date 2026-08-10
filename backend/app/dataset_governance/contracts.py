"""Strict W1 contracts for the Dataset Candidate creation seam."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
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


__all__ = [
    "CandidateOrigin",
    "CandidateStatus",
    "ConfirmationSource",
    "CuratorDecision",
    "DatasetGovernanceError",
    "DatasetGovernanceErrorCode",
    "DatasetGovernanceValidationError",
    "QualityTier",
    "RecordDatasetEvidenceCommandV1",
    "RecordDatasetEvidenceResultV1",
    "SourceKind",
    "Split",
]
