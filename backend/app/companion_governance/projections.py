"""Canonical W1 UI projections derived from governance authority."""

from __future__ import annotations

import uuid

from sqlalchemy import null

from ..agent_chat.contracts import (
    AgentChatContractError,
    BusEventEnvelopeV1,
    UIFeedEventV1,
    timestamp_text,
)
from ..agent_chat.models import AgentBusEvent, UIFeedEvent
from .contracts import CompanionGovernanceError, CompanionGovernanceErrorCode
from .models import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)


_VISIBLE_ROLES = ["boss", "engineer", "consultant"]


def attention_ui_event(
    attention: CompanionHumanAttention,
    *,
    issue: CompanionIssue,
    initial_proposal_id: uuid.UUID,
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
                f"companion_proposal:{initial_proposal_id}",
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


def decision_ui_event(decision: DecisionRecord) -> UIFeedEventV1:
    refs = [
        f"companion_issue:{decision.issue_id}",
        f"companion_proposal:{decision.proposal_id}",
        f"decision_record:{decision.decision_record_id}",
    ]
    if decision.workflow_effect_ref is not None:
        refs.append(decision.workflow_effect_ref)
    return UIFeedEventV1.from_untrusted(
        {
            "schema_version": 1,
            "ui_event_id": str(decision.decision_record_id),
            "created_at": timestamp_text(decision.decided_at),
            "farm_id": str(decision.farm_id),
            "plant_id": str(decision.plant_id),
            "source_type": "companion_governance",
            "source_id": str(decision.decision_record_id),
            "source_refs": refs,
            "display_kind": "companion_governance",
            "display_payload": {
                "payload_kind": "companion_decision",
                "decision_record_ref": (
                    f"decision_record:{decision.decision_record_id}"
                ),
                "issue_ref": f"companion_issue:{decision.issue_id}",
                "proposal_ref": f"companion_proposal:{decision.proposal_id}",
                "decision_summary": decision.decision_summary,
                "safety_gate_authority": "not_granted",
            },
            "visible_to_roles": _VISIBLE_ROLES,
            "visible_to_agents": False,
            "consumable_by_agents": False,
        }
    )


def decision_bus_event(decision: DecisionRecord) -> BusEventEnvelopeV1:
    refs = [
        f"decision_record:{decision.decision_record_id}",
        f"companion_issue:{decision.issue_id}",
        f"companion_proposal:{decision.proposal_id}",
    ]
    if decision.workflow_effect_ref is not None:
        refs.append(decision.workflow_effect_ref)
    return BusEventEnvelopeV1.from_untrusted(
        {
            "schema_version": 1,
            "event_id": str(decision.decision_record_id),
            "event_type": "domain_event_ref",
            "created_at": timestamp_text(decision.decided_at),
            "farm_id": str(decision.farm_id),
            "plant_id": str(decision.plant_id),
            "actor_ref": None,
            "source_type": "domain_record",
            "source_id": str(decision.decision_record_id),
            "payload": {
                "payload_kind": "domain_event_ref",
                "record_type": "decision_record",
                "record_ref": f"decision_record:{decision.decision_record_id}",
            },
            "source_refs": refs,
            "consumable_by_agents": True,
            "authorization_scope": None,
        }
    )


def new_bus_model(event: BusEventEnvelopeV1) -> AgentBusEvent:
    return AgentBusEvent(
        event_id=event.event_id,
        created_at=event.created_at,
        farm_id=event.farm_id,
        plant_id=event.plant_id,
        event_type=event.event_type,
        source_type=event.source_type,
        source_id=event.source_id,
        actor_ref=null(),
        payload=dict(event.payload),
        source_refs=list(event.source_refs),
        authorization_scope=null(),
        consumable_by_agents=True,
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


def repair_canonical_proposal_projection(
    projection: UIFeedEvent | None,
    proposal: CompanionProposal,
) -> UIFeedEvent:
    """Overwrite or rebuild one derived proposal row from proposal authority."""

    try:
        expected = proposal_ui_event(proposal)
        if projection is None:
            projection = new_ui_model(expected)
        else:
            projection.created_at = expected.created_at
            projection.farm_id = expected.farm_id
            projection.plant_id = expected.plant_id
            projection.source_type = expected.source_type
            projection.source_id = expected.source_id
            projection.source_refs = list(expected.source_refs)
            projection.display_kind = expected.display_kind
            projection.display_payload = dict(expected.display_payload)
            projection.visible_to_roles = list(expected.visible_to_roles)
            projection.visible_to_agents = False
            projection.consumable_by_agents = False
            projection.agent_id = None
            projection.roster_version = None
        stored = UIFeedEventV1.from_untrusted(_ui_row_value(projection))
    except (AgentChatContractError, TypeError, ValueError):
        _persistence_failed()
    if stored != expected:
        _persistence_failed()
    return projection


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
    "attention_ui_event",
    "decision_bus_event",
    "decision_ui_event",
    "new_bus_model",
    "new_ui_model",
    "proposal_ui_event",
    "repair_canonical_proposal_projection",
]
