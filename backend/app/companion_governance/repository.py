"""Repository and current-authority locks for Companion governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from ..agent_chat.models import UIFeedEvent
from ..safety_gate.models import SafetyClassification
from .models import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)


@dataclass(frozen=True, slots=True)
class CurrentGovernanceScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    plant_status: str
    role_preset: str
    permission_source: str
    grant_id: uuid.UUID | None
    can_read: bool
    can_operate: bool


class CompanionGovernanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        for_update: bool,
    ) -> CurrentGovernanceScope | None:
        now = datetime.now(timezone.utc)
        session_query = select(LocalSession).where(
            LocalSession.session_id == actor.session_id
        )
        account_query = select(Account).where(Account.account_id == actor.account_id)
        membership_query = select(FarmMembership).where(
            FarmMembership.membership_id == actor.membership_id
        )
        plant_query = select(Plant).where(
            Plant.plant_id == plant_id,
            Plant.farm_id == actor.farm_id,
        )
        if for_update:
            session_query = session_query.with_for_update()
            account_query = account_query.with_for_update()
            membership_query = membership_query.with_for_update()
            plant_query = plant_query.with_for_update()
        local_session = self.session.scalar(
            session_query.execution_options(populate_existing=True)
        )
        account = self.session.scalar(
            account_query.execution_options(populate_existing=True)
        )
        membership = self.session.scalar(
            membership_query.execution_options(populate_existing=True)
        )
        plant = self.session.scalar(
            plant_query.execution_options(populate_existing=True)
        )
        if (
            local_session is None
            or account is None
            or membership is None
            or plant is None
            or local_session.account_id != account.account_id
            or local_session.revoked_at is not None
            or local_session.expires_at <= now
            or account.account_status != "active"
            or membership.account_id != account.account_id
            or membership.farm_id != actor.farm_id
            or membership.membership_status != "active"
            or membership.role_preset != actor.role_preset.value
            or membership.role_preset not in {"boss", "engineer", "consultant"}
        ):
            return None

        grant_id: uuid.UUID | None = None
        permission_source = "boss_role"
        if membership.role_preset != "boss":
            grant_query = select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == membership.membership_id,
                PlantAccessGrant.plant_id == plant_id,
                PlantAccessGrant.status == "active",
            )
            if for_update:
                grant_query = grant_query.with_for_update()
            grant = self.session.scalar(
                grant_query.execution_options(populate_existing=True)
            )
            if grant is None:
                return None
            grant_id = grant.grant_id
            permission_source = "plant_access_grant"

        return CurrentGovernanceScope(
            farm_id=actor.farm_id,
            plant_id=plant_id,
            plant_status=plant.status,
            role_preset=membership.role_preset,
            permission_source=permission_source,
            grant_id=grant_id,
            can_read=plant.status in {"active", "archived"},
            can_operate=(
                plant.status == "active"
                and membership.role_preset in {"boss", "engineer"}
            ),
        )

    def classification(
        self,
        message_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> SafetyClassification | None:
        query = select(SafetyClassification).where(
            SafetyClassification.message_id == message_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def proposal_by_run(
        self,
        run_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> CompanionProposal | None:
        query = select(CompanionProposal).where(
            CompanionProposal.source_run_id == run_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def focused_issue(
        self,
        plant_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> CompanionIssue | None:
        query = select(CompanionIssue).where(
            CompanionIssue.plant_id == plant_id,
            CompanionIssue.is_focused.is_(True),
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def issue(
        self,
        issue_id: uuid.UUID,
        *,
        plant_id: uuid.UUID,
        farm_id: uuid.UUID,
        for_update: bool,
    ) -> CompanionIssue | None:
        query = select(CompanionIssue).where(
            CompanionIssue.issue_id == issue_id,
            CompanionIssue.plant_id == plant_id,
            CompanionIssue.farm_id == farm_id,
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def active_attention(
        self,
        issue_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> CompanionHumanAttention | None:
        query = select(CompanionHumanAttention).where(
            CompanionHumanAttention.issue_id == issue_id,
            CompanionHumanAttention.status == "active",
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def proposal(
        self,
        proposal_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> CompanionProposal | None:
        query = select(CompanionProposal).where(
            CompanionProposal.proposal_id == proposal_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def pending_proposal(
        self,
        issue_id: uuid.UUID,
        *,
        attention_id: uuid.UUID,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        for_update: bool,
    ) -> CompanionProposal | None:
        query = select(CompanionProposal).where(
            CompanionProposal.issue_id == issue_id,
            CompanionProposal.attention_id == attention_id,
            CompanionProposal.farm_id == farm_id,
            CompanionProposal.plant_id == plant_id,
            CompanionProposal.state == "pending",
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def attention(
        self,
        attention_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> CompanionHumanAttention | None:
        query = select(CompanionHumanAttention).where(
            CompanionHumanAttention.attention_id == attention_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def next_attention_sequence(self, issue_id: uuid.UUID) -> int:
        return (
            self.session.scalar(
                select(
                    func.coalesce(func.max(CompanionHumanAttention.attention_sequence), 0)
                ).where(CompanionHumanAttention.issue_id == issue_id)
            )
            + 1
        )

    def next_proposal_sequence(self, issue_id: uuid.UUID) -> int:
        return (
            self.session.scalar(
                select(func.coalesce(func.max(CompanionProposal.proposal_sequence), 0))
                .where(CompanionProposal.issue_id == issue_id)
            )
            + 1
        )

    def ui_projection(
        self,
        ui_event_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> UIFeedEvent | None:
        query = select(UIFeedEvent).where(UIFeedEvent.ui_event_id == ui_event_id)
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def list_issues(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        status: str | None,
        cursor: tuple[int, datetime, uuid.UUID] | None,
        limit: int,
    ) -> list[CompanionIssue]:
        rank = _status_rank()
        query = select(CompanionIssue).where(
            CompanionIssue.farm_id == farm_id,
            CompanionIssue.plant_id == plant_id,
        )
        if status is not None:
            query = query.where(CompanionIssue.status == status)
        if cursor is not None:
            cursor_rank, cursor_created, cursor_id = cursor
            query = query.where(
                (rank > cursor_rank)
                | (
                    (rank == cursor_rank)
                    & (CompanionIssue.created_at > cursor_created)
                )
                | (
                    (rank == cursor_rank)
                    & (CompanionIssue.created_at == cursor_created)
                    & (CompanionIssue.issue_id > cursor_id)
                )
            )
        return list(
            self.session.scalars(
                query.order_by(rank, CompanionIssue.created_at, CompanionIssue.issue_id)
                .limit(limit + 1)
            )
        )

    def attentions(
        self,
        issue_id: uuid.UUID,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[CompanionHumanAttention]:
        return list(
            self.session.scalars(
                select(CompanionHumanAttention)
                .where(
                    CompanionHumanAttention.issue_id == issue_id,
                    CompanionHumanAttention.farm_id == farm_id,
                    CompanionHumanAttention.plant_id == plant_id,
                )
                .order_by(
                    CompanionHumanAttention.attention_sequence,
                    CompanionHumanAttention.attention_id,
                )
            )
        )

    def proposals(
        self,
        issue_id: uuid.UUID,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[CompanionProposal]:
        return list(
            self.session.scalars(
                select(CompanionProposal)
                .where(
                    CompanionProposal.issue_id == issue_id,
                    CompanionProposal.farm_id == farm_id,
                    CompanionProposal.plant_id == plant_id,
                )
                .order_by(
                    CompanionProposal.proposal_sequence,
                    CompanionProposal.proposal_id,
                )
            )
        )

    def decisions(
        self,
        issue_id: uuid.UUID,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[DecisionRecord]:
        return list(
            self.session.scalars(
                select(DecisionRecord)
                .where(
                    DecisionRecord.issue_id == issue_id,
                    DecisionRecord.farm_id == farm_id,
                    DecisionRecord.plant_id == plant_id,
                )
                .order_by(
                    DecisionRecord.decided_at,
                    DecisionRecord.decision_record_id,
                )
            )
        )

def _status_rank():
    return case(
        (CompanionIssue.status == "open", 0),
        (CompanionIssue.status == "resolved", 1),
        else_=2,
    )


__all__ = ["CompanionGovernanceRepository", "CurrentGovernanceScope"]
