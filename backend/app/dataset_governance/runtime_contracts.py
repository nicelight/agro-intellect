"""Strict provider-neutral contracts for the registered Dataset Governance
advisory-only runtime route (AD-011).

This module defines the competence-local command, request, result, and outcome
for the Dataset Governance Agent. The Dataset Governance Agent assesses one
authorized candidate without persisting any Dataset field and without entering
generic ``AgentRuntimeOutcomeV1`` or MessageEnvelope flow.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import uuid

from ..access_admin.actor_context import ActorContext
from .contracts import (
    CandidateOrigin,
    CandidateStatus,
    QualityTier,
)

#: Canonical strong-evidence policy identifier carried in the closed policy context.
STRONG_EVIDENCE_POLICY_V1 = "ft014_strong_evidence_v1"

#: Closed assessment values for the Dataset Governance Agent result.
GOVERNANCE_ASSESSMENTS = frozenset(
    {"eligible_for_curator_review", "needs_human_review", "policy_violation"}
)

#: Closed violation-code catalog the model may use for a ``policy_violation``
#: assessment. Codes mirror the canonical strong-evidence policy conditions in
#: states/dataset-governance.md and decisions D4/D5.
GOVERNANCE_VIOLATION_CODES = frozenset(
    {
        "agent_labeled",
        "weak_evidence",
        "follow_up_missing",
        "gold_designation",
    }
)

#: Closed Training Data Curator decisions. ``silent`` persists nothing; the
#: curator usually stays silent.
CURATOR_DECISIONS = frozenset({"selected", "deferred", "rejected", "silent"})

DATASET_AGENT_IDS = frozenset({"dataset_governance", "training_data_curator"})
DATASET_TRIGGER_KINDS = frozenset({"dataset_candidate_created", "manual_review"})

OUTCOME_KINDS = frozenset(
    {
        "advisory_ready",
        "model_silent",
        "context_denied",
        "runtime_not_configured",
        "provider_failed",
        "output_invalid",
        "post_io_guard_denied",
        "policy_blocked",
        "audit_failed",
    }
)
OUTCOME_STATUSES = frozenset({"advisory_ready", "silent", "blocked", "failed"})
PROVIDER_CALL_STATUSES = frozenset({"not_attempted", "completed", "failed"})
AUDIT_STATUSES = frozenset({"appended", "failed"})
CURATOR_GATE_RESULTS = frozenset(
    {"not_applicable", "not_requested", "confirmed", "policy_blocked"}
)

DATASET_AGENT_CONTEXT_DENIED = "dataset_agent_context_denied"
DATASET_AGENT_RUNTIME_NOT_CONFIGURED = "dataset_agent_runtime_not_configured"
DATASET_AGENT_PROVIDER_FAILED = "dataset_agent_provider_failed"
DATASET_AGENT_OUTPUT_INVALID = "dataset_agent_output_invalid"
DATASET_AGENT_POST_IO_GUARD_DENIED = "dataset_agent_post_io_guard_denied"
DATASET_CONFIRMATION_POLICY_VIOLATION = "dataset_confirmation_policy_violation"
DATASET_AGENT_AUDIT_FAILED = "dataset_agent_audit_failed"

_AGENT_ID_RE = re.compile(r"[a-z][a-z0-9_]{2,63}\Z")
_MODEL_REF_RE = re.compile(r"[a-z][a-z0-9_]{0,63}:[A-Za-z0-9._-]{1,127}\Z")


class DatasetGovernanceRuntimeValidationError(ValueError):
    """A competence-local Dataset Governance runtime contract is malformed."""

    def __init__(self) -> None:
        super().__init__("Dataset Governance runtime contract validation failed.")


@dataclass(frozen=True, slots=True)
class DatasetAgentCommandV1:
    """Service-side explicit internal invocation over one existing candidate."""

    run_id: uuid.UUID
    requested_at: datetime
    actor_context: ActorContext
    plant_id: uuid.UUID
    candidate_id: uuid.UUID
    agent_id: str
    trigger_kind: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or not _utc_datetime(self.requested_at)
            or not isinstance(self.actor_context, ActorContext)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.candidate_id, uuid.UUID)
            or self.agent_id not in DATASET_AGENT_IDS
            or self.trigger_kind not in DATASET_TRIGGER_KINDS
        ):
            raise DatasetGovernanceRuntimeValidationError()

    @property
    def command_sha256(self) -> str:
        return dataset_agent_command_sha256(self)


@dataclass(frozen=True, slots=True)
class DatasetGovernanceCandidateSnapshotV1:
    """Typed candidate snapshot with evidence kinds and counts only."""

    candidate_status: str
    candidate_origin: str
    quality_tier: str
    follow_up_seen: bool
    corrected: bool
    evidence_ref_count: int
    evidence_kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        kinds = tuple(self.evidence_kinds)
        if (
            self.candidate_status
            not in {status.value for status in CandidateStatus}
            or self.candidate_origin
            not in {origin.value for origin in CandidateOrigin}
            or self.quality_tier not in {tier.value for tier in QualityTier}
            or not isinstance(self.follow_up_seen, bool)
            or not isinstance(self.corrected, bool)
            or not isinstance(self.evidence_ref_count, int)
            or self.evidence_ref_count < 1
            or not kinds
            or len(kinds) != len(set(kinds))
            or any(not isinstance(kind, str) or not kind for kind in kinds)
        ):
            raise DatasetGovernanceRuntimeValidationError()
        object.__setattr__(self, "evidence_kinds", kinds)

    def as_value(self) -> dict[str, object]:
        return {
            "candidate_status": self.candidate_status,
            "candidate_origin": self.candidate_origin,
            "quality_tier": self.quality_tier,
            "follow_up_seen": self.follow_up_seen,
            "corrected": self.corrected,
            "evidence_ref_count": self.evidence_ref_count,
            "evidence_kinds": list(self.evidence_kinds),
        }


@dataclass(frozen=True, slots=True)
class DatasetGovernancePolicyContextV1:
    """Closed server-derived policy context for the assessment."""

    strong_evidence_policy: str
    agent_labeled_guard: bool

    def __post_init__(self) -> None:
        if (
            self.strong_evidence_policy != STRONG_EVIDENCE_POLICY_V1
            or self.agent_labeled_guard is not True
        ):
            raise DatasetGovernanceRuntimeValidationError()

    def as_value(self) -> dict[str, object]:
        return {
            "strong_evidence_policy": self.strong_evidence_policy,
            "agent_labeled_guard": self.agent_labeled_guard,
        }


@dataclass(frozen=True, slots=True)
class DatasetGovernanceProviderRequestV1:
    """Strict provider request constructed server-side for the governance agent."""

    run_id: uuid.UUID
    requested_at: datetime
    plant_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate: DatasetGovernanceCandidateSnapshotV1
    policy_context: DatasetGovernancePolicyContextV1
    agent_id: str = "dataset_governance"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or not _utc_datetime(self.requested_at)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.candidate_id, uuid.UUID)
            or not isinstance(self.candidate, DatasetGovernanceCandidateSnapshotV1)
            or not isinstance(self.policy_context, DatasetGovernancePolicyContextV1)
            or self.agent_id != "dataset_governance"
        ):
            raise DatasetGovernanceRuntimeValidationError()

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "requested_at": _timestamp_text(self.requested_at),
            "agent_id": self.agent_id,
            "plant_id": str(self.plant_id),
            "candidate_id": str(self.candidate_id),
            "candidate": self.candidate.as_value(),
            "policy_context": self.policy_context.as_value(),
        }


@dataclass(frozen=True, slots=True)
class TrainingDataCuratorProviderRequestV1:
    """Strict provider request constructed server-side for the curator agent."""

    run_id: uuid.UUID
    requested_at: datetime
    plant_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate: DatasetGovernanceCandidateSnapshotV1
    policy_context: DatasetGovernancePolicyContextV1
    agent_id: str = "training_data_curator"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or not _utc_datetime(self.requested_at)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.candidate_id, uuid.UUID)
            or not isinstance(self.candidate, DatasetGovernanceCandidateSnapshotV1)
            or not isinstance(self.policy_context, DatasetGovernancePolicyContextV1)
            or self.agent_id != "training_data_curator"
        ):
            raise DatasetGovernanceRuntimeValidationError()

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "requested_at": _timestamp_text(self.requested_at),
            "agent_id": self.agent_id,
            "plant_id": str(self.plant_id),
            "candidate_id": str(self.candidate_id),
            "candidate": self.candidate.as_value(),
            "policy_context": self.policy_context.as_value(),
        }


@dataclass(frozen=True, slots=True)
class TrainingDataCuratorDecisionV1:
    """Validated untrusted Training Data Curator result.

    The decision is advisory only: ``selected`` still requires the server-side
    strong-evidence gate, and the result can never supply lifecycle, quality,
    split, confirmation, evidence, or trainability fields.
    """

    run_id: uuid.UUID
    curator_decision: str
    curator_notes_ref: str | None
    schema_version: int = 1

    @classmethod
    def from_untrusted(
        cls,
        value: object,
        *,
        request: TrainingDataCuratorProviderRequestV1,
    ) -> "TrainingDataCuratorDecisionV1":
        fields = _exact_mapping(
            value,
            {
                "schema_version",
                "run_id",
                "curator_decision",
                "curator_notes_ref",
            },
        )
        if fields["schema_version"] != 1:
            raise DatasetGovernanceRuntimeValidationError()
        run_id = _canonical_uuid(fields["run_id"], version=4)
        decision = fields["curator_decision"]
        notes = fields["curator_notes_ref"]
        if (
            run_id != request.run_id
            or decision not in CURATOR_DECISIONS
            or (
                notes is not None
                and not _bounded_text(notes, maximum=200)
            )
            or (decision == "silent" and notes is not None)
        ):
            raise DatasetGovernanceRuntimeValidationError()
        return cls(
            run_id=run_id,
            curator_decision=decision,
            curator_notes_ref=notes,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "curator_decision": self.curator_decision,
            "curator_notes_ref": self.curator_notes_ref,
        }


@dataclass(frozen=True, slots=True)
class DatasetGovernanceAssessmentV1:
    """Validated untrusted assessment from the governance provider."""

    run_id: uuid.UUID
    assessment: str
    violation_codes: tuple[str, ...]
    assessment_notes: str
    schema_version: int = 1

    @classmethod
    def from_untrusted(
        cls,
        value: object,
        *,
        request: DatasetGovernanceProviderRequestV1,
    ) -> "DatasetGovernanceAssessmentV1":
        fields = _exact_mapping(
            value,
            {
                "schema_version",
                "run_id",
                "assessment",
                "violation_codes",
                "assessment_notes",
            },
        )
        if fields["schema_version"] != 1:
            raise DatasetGovernanceRuntimeValidationError()
        run_id = _canonical_uuid(fields["run_id"], version=4)
        assessment = fields["assessment"]
        codes = _closed_strings(
            fields["violation_codes"],
            allowed=GOVERNANCE_VIOLATION_CODES,
        )
        notes = fields["assessment_notes"]
        if (
            run_id != request.run_id
            or assessment not in GOVERNANCE_ASSESSMENTS
            or not _bounded_text(notes, maximum=500)
        ):
            raise DatasetGovernanceRuntimeValidationError()
        if assessment == "policy_violation":
            if not codes:
                raise DatasetGovernanceRuntimeValidationError()
        elif codes:
            raise DatasetGovernanceRuntimeValidationError()
        return cls(
            run_id=run_id,
            assessment=assessment,
            violation_codes=codes,
            assessment_notes=notes,
        )

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "assessment": self.assessment,
            "violation_codes": list(self.violation_codes),
            "assessment_notes": self.assessment_notes,
        }


@dataclass(frozen=True, slots=True)
class DatasetAgentRuntimeOutcomeV1:
    """Strict competence-local outcome for the registered advisory route."""

    run_id: uuid.UUID
    agent_id: str
    candidate_id: uuid.UUID
    outcome_kind: str
    status: str
    reason_code: str
    error_code: str | None
    validated_result: object | None
    event_ref: Mapping[str, object] | None
    model_ref: str | None
    provider_call_status: str
    audit_status: str
    curator_gate_result: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or not _uuid4(self.run_id)
            or self.agent_id not in DATASET_AGENT_IDS
            or not isinstance(self.candidate_id, uuid.UUID)
            or self.outcome_kind not in OUTCOME_KINDS
            or self.status not in OUTCOME_STATUSES
            or not isinstance(self.reason_code, str)
            or (
                self.error_code is not None
                and not isinstance(self.error_code, str)
            )
            or (
                self.model_ref is not None
                and _MODEL_REF_RE.fullmatch(self.model_ref) is None
            )
            or self.provider_call_status not in PROVIDER_CALL_STATUSES
            or self.audit_status not in AUDIT_STATUSES
            or self.curator_gate_result not in CURATOR_GATE_RESULTS
        ):
            raise DatasetGovernanceRuntimeValidationError()
        _validate_outcome_matrix(self)

    def as_value(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "run_id": str(self.run_id),
            "agent_id": self.agent_id,
            "candidate_id": str(self.candidate_id),
            "outcome_kind": self.outcome_kind,
            "status": self.status,
            "reason_code": self.reason_code,
            "error_code": self.error_code,
            "validated_result": (
                self.validated_result.as_value()
                if self.validated_result is not None
                else None
            ),
            "event_ref": dict(self.event_ref) if self.event_ref is not None else None,
            "model_ref": self.model_ref,
            "provider_call_status": self.provider_call_status,
            "audit_status": self.audit_status,
            "curator_gate_result": self.curator_gate_result,
        }


def dataset_agent_command_sha256(command: DatasetAgentCommandV1) -> str:
    """Fingerprint the command from its canonical immutable identity inputs."""
    if not isinstance(command, DatasetAgentCommandV1):
        raise DatasetGovernanceRuntimeValidationError()
    actor = command.actor_context
    payload = {
        "schema_version": command.schema_version,
        "run_id": str(command.run_id),
        "requested_at": _timestamp_text(command.requested_at),
        "request_id": actor.request_id,
        "session_id": str(actor.session_id),
        "account_id": str(actor.account_id),
        "farm_id": str(actor.farm_id),
        "membership_id": str(actor.membership_id),
        "plant_id": str(command.plant_id),
        "candidate_id": str(command.candidate_id),
        "agent_id": command.agent_id,
        "trigger_kind": command.trigger_kind,
    }
    compact = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def _validate_outcome_matrix(outcome: DatasetAgentRuntimeOutcomeV1) -> None:
    kind = outcome.outcome_kind
    has_result = outcome.validated_result is not None
    has_event = _is_dataset_agent_event_ref(outcome.event_ref)
    model_present = outcome.model_ref is not None

    if kind == "advisory_ready":
        result = outcome.validated_result
        if outcome.agent_id == "dataset_governance":
            result_ok = _matching_governance_result(result, outcome.run_id)
            gate_ok = outcome.curator_gate_result == "not_applicable"
        else:
            result_ok = _matching_curator_result(result, outcome.run_id)
            gate_ok = (
                outcome.curator_gate_result == "not_requested"
                and result_ok
                and result.curator_decision in {"deferred", "rejected"}
            ) or (
                outcome.curator_gate_result == "confirmed"
                and result_ok
                and result.curator_decision == "selected"
            )
        valid = (
            outcome.status == "advisory_ready"
            and result_ok
            and gate_ok
            and has_event
            and model_present
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
            and outcome.reason_code == "advisory_ready"
            and outcome.error_code is None
        )
    elif kind == "model_silent":
        result = outcome.validated_result
        valid = (
            outcome.status == "silent"
            and isinstance(result, TrainingDataCuratorDecisionV1)
            and result.schema_version == 1
            and result.run_id == outcome.run_id
            and result.curator_decision == "silent"
            and has_event
            and model_present
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_requested"
            and outcome.reason_code == "model_silent"
            and outcome.error_code is None
        )
    elif kind == "context_denied":
        valid = (
            outcome.status == "blocked"
            and not has_result
            and has_event
            and not model_present
            and outcome.provider_call_status == "not_attempted"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_applicable"
            and outcome.reason_code == "context_denied"
            and outcome.error_code == DATASET_AGENT_CONTEXT_DENIED
        )
    elif kind == "runtime_not_configured":
        valid = (
            outcome.status == "failed"
            and not has_result
            and has_event
            and not model_present
            and outcome.provider_call_status == "not_attempted"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_applicable"
            and outcome.reason_code == "runtime_not_configured"
            and outcome.error_code == DATASET_AGENT_RUNTIME_NOT_CONFIGURED
        )
    elif kind == "provider_failed":
        valid = (
            outcome.status == "failed"
            and not has_result
            and has_event
            and model_present
            and outcome.provider_call_status == "failed"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_applicable"
            and outcome.reason_code == "provider_failed"
            and outcome.error_code == DATASET_AGENT_PROVIDER_FAILED
        )
    elif kind == "output_invalid":
        valid = (
            outcome.status == "blocked"
            and not has_result
            and has_event
            and model_present
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_applicable"
            and outcome.reason_code == "output_invalid"
            and outcome.error_code == DATASET_AGENT_OUTPUT_INVALID
        )
    elif kind == "post_io_guard_denied":
        valid = (
            outcome.status == "blocked"
            and not has_result
            and has_event
            and model_present
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "not_applicable"
            and outcome.reason_code == "post_io_guard_denied"
            and outcome.error_code == DATASET_AGENT_POST_IO_GUARD_DENIED
        )
    elif kind == "policy_blocked":
        valid = (
            outcome.status == "blocked"
            and not has_result
            and has_event
            and model_present
            and outcome.provider_call_status == "completed"
            and outcome.audit_status == "appended"
            and outcome.curator_gate_result == "policy_blocked"
            and outcome.reason_code == "policy_blocked"
            and outcome.error_code == DATASET_CONFIRMATION_POLICY_VIOLATION
        )
    else:  # audit_failed
        valid = (
            outcome.status == "failed"
            and not has_result
            and not has_event
            and outcome.audit_status == "failed"
            and outcome.provider_call_status in PROVIDER_CALL_STATUSES
            and outcome.reason_code == "audit_failed"
            and outcome.error_code == DATASET_AGENT_AUDIT_FAILED
        )
    if not valid:
        raise DatasetGovernanceRuntimeValidationError()


def _matching_governance_result(value: object, run_id: uuid.UUID) -> bool:
    return (
        isinstance(value, DatasetGovernanceAssessmentV1)
        and value.schema_version == 1
        and value.run_id == run_id
    )


def _matching_curator_result(value: object, run_id: uuid.UUID) -> bool:
    return (
        isinstance(value, TrainingDataCuratorDecisionV1)
        and value.schema_version == 1
        and value.run_id == run_id
    )


def _is_dataset_agent_event_ref(value: object) -> bool:
    if (
        not isinstance(value, Mapping)
        or value.get("event_type") != "dataset_agent_runtime_decided"
    ):
        return False
    try:
        uuid.UUID(str(value.get("timeline_event_id")))
    except (TypeError, ValueError):
        return False
    return (
        isinstance(value.get("timeline_ref"), str)
        and str(value.get("timeline_ref")).startswith("timeline.jsonl#")
        and isinstance(value.get("created_at"), str)
    )


def _exact_mapping(value: object, keys: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise DatasetGovernanceRuntimeValidationError()
    return dict(value)


def _closed_strings(value: object, *, allowed: frozenset[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise DatasetGovernanceRuntimeValidationError()
    codes = tuple(value)
    if len(codes) != len(set(codes)) or any(code not in allowed for code in codes):
        raise DatasetGovernanceRuntimeValidationError()
    return codes


def _bounded_text(value: object, *, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and 0 <= len(value) <= maximum
    )


def _canonical_uuid(value: object, *, version: int | None = None) -> uuid.UUID:
    if not isinstance(value, str):
        raise DatasetGovernanceRuntimeValidationError()
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        raise DatasetGovernanceRuntimeValidationError() from None
    if str(parsed) != value or (version is not None and parsed.version != version):
        raise DatasetGovernanceRuntimeValidationError()
    return parsed


def _uuid4(value: object) -> bool:
    return isinstance(value, uuid.UUID) and value.version == 4


def _utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timezone.utc.utcoffset(value)
    )


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "CURATOR_DECISIONS",
    "DATASET_AGENT_AUDIT_FAILED",
    "DATASET_AGENT_CONTEXT_DENIED",
    "DATASET_AGENT_IDS",
    "DATASET_AGENT_OUTPUT_INVALID",
    "DATASET_AGENT_POST_IO_GUARD_DENIED",
    "DATASET_AGENT_PROVIDER_FAILED",
    "DATASET_AGENT_RUNTIME_NOT_CONFIGURED",
    "DATASET_TRIGGER_KINDS",
    "DATASET_CONFIRMATION_POLICY_VIOLATION",
    "DatasetAgentCommandV1",
    "DatasetAgentRuntimeOutcomeV1",
    "DatasetGovernanceAssessmentV1",
    "DatasetGovernanceCandidateSnapshotV1",
    "DatasetGovernancePolicyContextV1",
    "DatasetGovernanceProviderRequestV1",
    "DatasetGovernanceRuntimeValidationError",
    "GOVERNANCE_ASSESSMENTS",
    "GOVERNANCE_VIOLATION_CODES",
    "OUTCOME_KINDS",
    "STRONG_EVIDENCE_POLICY_V1",
    "TrainingDataCuratorDecisionV1",
    "TrainingDataCuratorProviderRequestV1",
    "dataset_agent_command_sha256",
]
