"""Closed W1 integrity validation for retained Companion authority."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from .contracts import (
    CompanionGovernanceError,
    CompanionGovernanceErrorCode,
    CompanionGovernanceValidationError,
    validate_provider_input_refs,
)
from .models import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)


@dataclass(frozen=True, slots=True)
class ValidatedW1IssueGraph:
    selected_attention: CompanionHumanAttention | None
    active_attention: CompanionHumanAttention | None
    current_proposal: CompanionProposal | None


def validate_w1_issue_graph(
    issue: CompanionIssue,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    attentions: list[CompanionHumanAttention],
    proposals: list[CompanionProposal],
    decisions: list[DecisionRecord],
) -> ValidatedW1IssueGraph:
    """Validate semantic relations not expressible by the existing simple FKs."""

    if decisions or issue.farm_id != farm_id or issue.plant_id != plant_id:
        _read_inconsistent()

    scope = (farm_id, plant_id, issue.issue_id)
    attention_by_id: dict[uuid.UUID, CompanionHumanAttention] = {}
    for attention in attentions:
        if (
            (attention.farm_id, attention.plant_id, attention.issue_id) != scope
            or attention.satisfied_by_decision_record_id is not None
        ):
            _read_inconsistent()
        attention_by_id[attention.attention_id] = attention

    proposal_by_id: dict[uuid.UUID, CompanionProposal] = {}
    for proposal in proposals:
        attention = attention_by_id.get(proposal.attention_id)
        if attention is None:
            _read_inconsistent()
        validate_w1_proposal_edge(issue, attention, proposal)
        proposal_by_id[proposal.proposal_id] = proposal

    for attention in attentions:
        current = proposal_by_id.get(attention.current_proposal_id)
        if current is None or current.attention_id != attention.attention_id:
            _read_inconsistent()
        if attention.status == "active" and current.state != "pending":
            _read_inconsistent()

    for proposal in proposals:
        attention = attention_by_id[proposal.attention_id]
        if proposal.state == "pending" and (
            attention.status != "active"
            or attention.current_proposal_id != proposal.proposal_id
        ):
            _read_inconsistent()

    active_attention = next(
        (attention for attention in attentions if attention.status == "active"),
        None,
    )
    selected_attention = (
        active_attention
        if active_attention is not None
        else (attentions[-1] if attentions else None)
    )
    current_proposal = (
        proposal_by_id.get(active_attention.current_proposal_id)
        if active_attention is not None
        else None
    )
    return ValidatedW1IssueGraph(
        selected_attention=selected_attention,
        active_attention=active_attention,
        current_proposal=current_proposal,
    )


def validate_w1_current_pair(
    issue: CompanionIssue,
    attention: CompanionHumanAttention,
    proposal: CompanionProposal,
) -> None:
    """Validate the locked current pair without loading retained history."""

    validate_w1_proposal_edge(issue, attention, proposal)
    if (
        attention.current_proposal_id != proposal.proposal_id
        or attention.status != "active"
        or proposal.state != "pending"
        or proposal.record_version != 1
    ):
        _read_inconsistent()


def validate_w1_proposal_edge(
    issue: CompanionIssue,
    attention: CompanionHumanAttention,
    proposal: CompanionProposal,
) -> None:
    """Validate one retained proposal edge and its derivable W1 refs."""

    scope = (issue.farm_id, issue.plant_id, issue.issue_id)
    if (
        (attention.farm_id, attention.plant_id, attention.issue_id) != scope
        or (proposal.farm_id, proposal.plant_id, proposal.issue_id) != scope
        or proposal.attention_id != attention.attention_id
        or proposal.decision_record_id is not None
        or attention.satisfied_by_decision_record_id is not None
        or not _proposal_source_refs_are_canonical(issue, proposal)
    ):
        _read_inconsistent()


def _proposal_source_refs_are_canonical(
    issue: CompanionIssue,
    proposal: CompanionProposal,
) -> bool:
    refs = proposal.source_refs
    if not isinstance(refs, list) or len(refs) < 3:
        return False
    expected_tail = [
        f"message_envelope:{proposal.source_message_id}",
        f"safety_classification:{proposal.source_classification_message_id}",
    ]
    if refs[-2:] != expected_tail:
        return False
    target_issue_id = (
        None
        if issue.created_by_run_id == proposal.source_run_id
        else issue.issue_id
    )
    try:
        provider_refs = validate_provider_input_refs(
            refs[:-2],
            plant_id=issue.plant_id,
            target_issue_id=target_issue_id,
        )
    except CompanionGovernanceValidationError:
        return False
    return list(provider_refs) == refs[:-2]


def _read_inconsistent() -> None:
    raise CompanionGovernanceError(CompanionGovernanceErrorCode.READ_INCONSISTENT)


__all__ = [
    "ValidatedW1IssueGraph",
    "validate_w1_current_pair",
    "validate_w1_issue_graph",
    "validate_w1_proposal_edge",
]
