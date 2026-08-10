"""Repository and current-authority locks for Dataset Governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from .models import DatasetCandidate


@dataclass(frozen=True, slots=True)
class CurrentDatasetScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    plant_status: str
    role_preset: str
    permission_source: str
    grant_id: uuid.UUID | None
    can_operate: bool


class DatasetGovernanceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def current_scope(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        for_update: bool,
    ) -> CurrentDatasetScope | None:
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

        return CurrentDatasetScope(
            farm_id=actor.farm_id,
            plant_id=plant_id,
            plant_status=plant.status,
            role_preset=membership.role_preset,
            permission_source=permission_source,
            grant_id=grant_id,
            can_operate=(
                plant.status == "active"
                and membership.role_preset in {"boss", "engineer"}
            ),
        )

    def candidate_by_source_identity(
        self,
        *,
        plant_id: uuid.UUID,
        source_kind: str,
        source_ref: uuid.UUID,
        for_update: bool,
    ) -> DatasetCandidate | None:
        query = select(DatasetCandidate).where(
            DatasetCandidate.plant_id == plant_id,
            DatasetCandidate.source_kind == source_kind,
            DatasetCandidate.source_ref == source_ref,
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))

    def candidate(
        self,
        candidate_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> DatasetCandidate | None:
        query = select(DatasetCandidate).where(
            DatasetCandidate.candidate_id == candidate_id
        )
        if for_update:
            query = query.with_for_update()
        return self.session.scalar(query.execution_options(populate_existing=True))


__all__ = ["CurrentDatasetScope", "DatasetGovernanceRepository"]
