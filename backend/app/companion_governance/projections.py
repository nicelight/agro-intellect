"""Canonical W1 UI projections derived from governance authority."""

from __future__ import annotations

from ..agent_chat.contracts import (
    AgentChatContractError,
    UIFeedEventV1,
    timestamp_text,
)
from ..agent_chat.models import UIFeedEvent
from .contracts import CompanionGovernanceError, CompanionGovernanceErrorCode
from .models import CompanionHumanAttention, CompanionIssue, CompanionProposal


_VISIBLE_ROLES = ["boss", "engineer", "consultant"]


def attention_ui_event(
    attention: CompanionHumanAttention,
    *,
    issue: CompanionIssue,
) -> UIFeedEventV1:
    return UIFeedEventV1.from_untrusted(
        {
            "schema_version": 1,
            "ui_event_id": str(attention.attention_id),
            "created_at": timestamp_text(attention.created_at),
            "farm_id": str(attention.farm_id),
            "plant_id": str(attention.plant_id),
            "source_type": "companion_governance",
            "source_id": str(attention.attention_id),
            "source_refs": [
                f"companion_issue:{issue.issue_id}",
                f"companion_attention:{attention.attention_id}",
                f"companion_proposal:{attention.current_proposal_id}",
            ],
            "display_kind": "companion_governance",
            "display_payload": {
                "payload_kind": "companion_attention",
                "attention_ref": f"companion_attention:{attention.attention_id}",
                "issue_ref": f"companion_issue:{issue.issue_id}",
                "summary_text": attention.summary_text,
            },
            "visible_to_roles": _VISIBLE_ROLES,
            "visible_to_agents": False,
            "consumable_by_agents": False,
        }
    )


def proposal_ui_event(proposal: CompanionProposal) -> UIFeedEventV1:
    return UIFeedEventV1.from_untrusted(
        {
            "schema_version": 1,
            "ui_event_id": str(proposal.proposal_id),
            "created_at": timestamp_text(proposal.created_at),
            "farm_id": str(proposal.farm_id),
            "plant_id": str(proposal.plant_id),
            "source_type": "companion_governance",
            "source_id": str(proposal.proposal_id),
            "source_refs": [
                f"companion_issue:{proposal.issue_id}",
                f"companion_attention:{proposal.attention_id}",
                f"companion_proposal:{proposal.proposal_id}",
                (
                    "safety_classification:"
                    f"{proposal.source_classification_message_id}"
                ),
            ],
            "display_kind": "companion_governance",
            "display_payload": {
                "payload_kind": "companion_proposal",
                "proposal_ref": f"companion_proposal:{proposal.proposal_id}",
                "issue_ref": f"companion_issue:{proposal.issue_id}",
                "proposal_state": proposal.state,
                "summary_text": proposal.proposal_summary,
            },
            "visible_to_roles": _VISIBLE_ROLES,
            "visible_to_agents": False,
            "consumable_by_agents": False,
        }
    )


def new_ui_model(event: UIFeedEventV1) -> UIFeedEvent:
    return UIFeedEvent(
        ui_event_id=event.ui_event_id,
        created_at=event.created_at,
        farm_id=event.farm_id,
        plant_id=event.plant_id,
        source_type=event.source_type,
        source_id=event.source_id,
        source_refs=list(event.source_refs),
        display_kind=event.display_kind,
        display_payload=dict(event.display_payload),
        visible_to_roles=list(event.visible_to_roles),
        visible_to_agents=False,
        consumable_by_agents=False,
        agent_id=None,
        roster_version=None,
    )


def require_canonical_pending_proposal_projection(
    projection: UIFeedEvent | None,
    proposal: CompanionProposal,
) -> None:
    """Fail before audit/mutation unless the stored row is the exact projection."""

    if projection is None:
        _persistence_failed()
    try:
        stored = UIFeedEventV1.from_untrusted(_ui_row_value(projection))
        expected = proposal_ui_event(proposal)
    except (AgentChatContractError, TypeError, ValueError):
        _persistence_failed()
    if stored != expected:
        _persistence_failed()


def apply_canonical_proposal_projection(
    projection: UIFeedEvent,
    proposal: CompanionProposal,
) -> None:
    """Apply only the terminal payload after the pending row was verified."""

    try:
        expected = proposal_ui_event(proposal)
        projection.display_payload = dict(expected.display_payload)
        stored = UIFeedEventV1.from_untrusted(_ui_row_value(projection))
    except (AgentChatContractError, TypeError, ValueError):
        _persistence_failed()
    if stored != expected:
        _persistence_failed()


def _ui_row_value(row: UIFeedEvent) -> dict[str, object]:
    return {
        "schema_version": 1,
        "ui_event_id": str(row.ui_event_id),
        "created_at": timestamp_text(row.created_at),
        "farm_id": str(row.farm_id),
        "plant_id": str(row.plant_id),
        "source_type": row.source_type,
        "source_id": row.source_id,
        "source_refs": row.source_refs,
        "display_kind": row.display_kind,
        "display_payload": row.display_payload,
        "visible_to_roles": row.visible_to_roles,
        "visible_to_agents": row.visible_to_agents,
        "consumable_by_agents": row.consumable_by_agents,
    }


def _persistence_failed() -> None:
    raise CompanionGovernanceError(CompanionGovernanceErrorCode.PERSISTENCE_FAILED)


__all__ = [
    "apply_canonical_proposal_projection",
    "attention_ui_event",
    "new_ui_model",
    "proposal_ui_event",
    "require_canonical_pending_proposal_projection",
]
