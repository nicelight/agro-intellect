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
    selected_proposal: CompanionProposal | None
    active_attention: CompanionHumanAttention | None
    current_proposal: CompanionProposal | None


def validate_issue_graph(
    issue: CompanionIssue,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    attentions: list[CompanionHumanAttention],
    proposals: list[CompanionProposal],
    decisions: list[DecisionRecord],
) -> ValidatedW1IssueGraph:
    """Validate the complete retained W1/W2 authority graph."""

    if issue.farm_id != farm_id or issue.plant_id != plant_id:
        _read_inconsistent()
    attention_by_id = {row.attention_id: row for row in attentions}
    proposal_by_id = {row.proposal_id: row for row in proposals}
    decision_by_id = {row.decision_record_id: row for row in decisions}
    if (
        len(attention_by_id) != len(attentions)
        or len(proposal_by_id) != len(proposals)
        or len(decision_by_id) != len(decisions)
    ):
        _read_inconsistent()
    scope = (farm_id, plant_id, issue.issue_id)
    for attention in attentions:
        if (attention.farm_id, attention.plant_id, attention.issue_id) != scope:
            _read_inconsistent()
        satisfying = (
            decision_by_id.get(attention.satisfied_by_decision_record_id)
            if attention.satisfied_by_decision_record_id is not None
            else None
        )
        if (attention.status == "active") != (satisfying is None):
            _read_inconsistent()
        if satisfying is not None and satisfying.attention_id != attention.attention_id:
            _read_inconsistent()
    for proposal in proposals:
        attention = attention_by_id.get(proposal.attention_id)
        if (
            attention is None
            or (proposal.farm_id, proposal.plant_id, proposal.issue_id) != scope
            or not _proposal_source_refs_are_canonical(issue, proposal)
        ):
            _read_inconsistent()
        linked = (
            decision_by_id.get(proposal.decision_record_id)
            if proposal.decision_record_id is not None
            else None
        )
        if proposal.state == "pending":
            if proposal.record_version != 1 or linked is not None:
                _read_inconsistent()
        elif proposal.state in {"approved", "rejected"}:
            if (
                proposal.record_version != 2
                or linked is None
                or linked.proposal_id != proposal.proposal_id
                or linked.attention_id != proposal.attention_id
                or linked.decision != proposal.state
            ):
                _read_inconsistent()
        elif proposal.state == "superseded":
            if proposal.record_version != 2 or linked is not None:
                _read_inconsistent()
        else:
            _read_inconsistent()
    for decision in decisions:
        proposal = proposal_by_id.get(decision.proposal_id)
        attention = attention_by_id.get(decision.attention_id)
        expected_refs = _decision_source_refs(issue, proposal) if proposal else None
        if (
            proposal is None
            or attention is None
            or (decision.farm_id, decision.plant_id, decision.issue_id) != scope
            or proposal.decision_record_id != decision.decision_record_id
            or attention.satisfied_by_decision_record_id
            != decision.decision_record_id
            or decision.source_refs != expected_refs
            or decision.safety_gate_authority != "not_granted"
        ):
            _read_inconsistent()

    active = [row for row in attentions if row.status == "active"]
    if len(active) > 1:
        _read_inconsistent()
    active_attention = active[0] if active else None
    selected_attention = active_attention or (attentions[-1] if attentions else None)
    current_proposal = None
    selected_proposal = None
    if active_attention is not None:
        matches = [
            row
            for row in proposals
            if row.attention_id == active_attention.attention_id
            and row.state == "pending"
        ]
        if len(matches) != 1:
            _read_inconsistent()
        current_proposal = matches[0]
        selected_proposal = current_proposal
    elif selected_attention is not None:
        satisfying = decision_by_id.get(
            selected_attention.satisfied_by_decision_record_id
        )
        if satisfying is None:
            _read_inconsistent()
        selected_proposal = proposal_by_id.get(satisfying.proposal_id)
        if (
            selected_proposal is None
            or selected_proposal.attention_id != selected_attention.attention_id
        ):
            _read_inconsistent()
    return ValidatedW1IssueGraph(
        selected_attention=selected_attention,
        selected_proposal=selected_proposal,
        active_attention=active_attention,
        current_proposal=current_proposal,
    )


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

    active_attention = next(
        (attention for attention in attentions if attention.status == "active"),
        None,
    )
    selected_attention = (
        active_attention
        if active_attention is not None
        else (attentions[-1] if attentions else None)
    )
    current_proposal = None
    if active_attention is not None:
        matches = [
            proposal
            for proposal in proposals
            if proposal.state == "pending"
            if proposal.attention_id == active_attention.attention_id
        ]
        if len(matches) != 1:
            _read_inconsistent()
        current_proposal = matches[0]
    return ValidatedW1IssueGraph(
        selected_attention=selected_attention,
        selected_proposal=current_proposal,
        active_attention=active_attention,
        current_proposal=current_proposal,
    )


def _decision_source_refs(
    issue: CompanionIssue,
    proposal: CompanionProposal,
) -> list[str]:
    upstream = [
        ref
        for ref in proposal.source_refs[:-2]
        if ref != f"companion_issue:{issue.issue_id}"
    ]
    return [
        f"companion_issue:{issue.issue_id}",
        f"companion_attention:{proposal.attention_id}",
        f"companion_proposal:{proposal.proposal_id}",
        f"safety_classification:{proposal.source_classification_message_id}",
        *upstream,
    ]


def validate_w1_current_pair(
    issue: CompanionIssue,
    attention: CompanionHumanAttention,
    proposal: CompanionProposal,
) -> None:
    """Validate the locked current pair without loading retained history."""

    validate_w1_proposal_edge(issue, attention, proposal)
    if (
        attention.status != "active"
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
    "validate_issue_graph",
    "validate_w1_current_pair",
    "validate_w1_issue_graph",
    "validate_w1_proposal_edge",
]
