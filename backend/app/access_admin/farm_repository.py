from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..database import DatabaseHandle
from .models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from .permissions import (
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
)


class FarmRepository:
    """Persistence adapter for canonical Farm bootstrap and FT-002 services."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_farms(self) -> list[Farm]:
        return list(
            self.session.scalars(select(Farm).order_by(Farm.farm_id).with_for_update())
        )

    def membership_farm_ids(self) -> set[uuid.UUID]:
        return set(
            self.session.scalars(select(FarmMembership.farm_id).distinct()).all()
        )

    def lock_canonical_plant(self) -> Plant | None:
        return self.session.scalar(
            select(Plant)
            .where(Plant.plant_key == "tomato_001")
            .with_for_update()
        )

    def add_farm(self, farm: Farm) -> None:
        self.session.add(farm)

    def add_plant(self, plant: Plant) -> None:
        self.session.add(plant)

    def add_grant(self, grant: PlantAccessGrant) -> None:
        self.session.add(grant)

    def flush(self) -> None:
        self.session.flush()

    def add_system_audit(
        self,
        *,
        farm_id: uuid.UUID,
        action_type: str,
        target_type: str,
        target_id: uuid.UUID,
        plant_id: uuid.UUID | None,
        request_id: str,
        after_summary: dict[str, object],
    ) -> None:
        self.session.add(
            AdminAuditRecord(
                farm_id=farm_id,
                actor_kind="system_bootstrap",
                actor_account_id=None,
                actor_membership_id=None,
                actor_role_preset=None,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                plant_id=plant_id,
                request_id=request_id,
                before_summary={},
                after_summary=after_summary,
                source_refs=[],
            )
        )

    def lock_actor_identity(
        self,
        *,
        account_id: uuid.UUID,
        membership_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> tuple[Account, FarmMembership] | None:
        row = self.session.execute(
            select(Account, FarmMembership)
            .join(FarmMembership, FarmMembership.account_id == Account.account_id)
            .where(
                Account.account_id == account_id,
                FarmMembership.membership_id == membership_id,
                FarmMembership.farm_id == farm_id,
            )
            .with_for_update()
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None

    def lock_farm(self, farm_id: uuid.UUID) -> Farm | None:
        return self.session.scalar(
            select(Farm).where(Farm.farm_id == farm_id).with_for_update()
        )

    def lock_plant(self, *, farm_id: uuid.UUID, plant_id: uuid.UUID) -> Plant | None:
        return self.session.scalar(
            select(Plant)
            .where(Plant.farm_id == farm_id, Plant.plant_id == plant_id)
            .with_for_update()
        )

    def lock_plant_by_key(self, *, farm_id: uuid.UUID, plant_key: str) -> Plant | None:
        return self.session.scalar(
            select(Plant)
            .where(Plant.farm_id == farm_id, Plant.plant_key == plant_key)
            .with_for_update()
        )

    def lock_membership(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> FarmMembership | None:
        return self.session.scalar(
            select(FarmMembership)
            .where(
                FarmMembership.farm_id == farm_id,
                FarmMembership.membership_id == membership_id,
            )
            .with_for_update()
        )

    def lock_membership_identity(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> tuple[Account, FarmMembership] | None:
        row = self.session.execute(
            select(Account, FarmMembership)
            .join(FarmMembership, FarmMembership.account_id == Account.account_id)
            .where(
                FarmMembership.farm_id == farm_id,
                FarmMembership.membership_id == membership_id,
            )
            .with_for_update()
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None

    def lock_grant(
        self,
        *,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessGrant | None:
        return self.session.scalar(
            select(PlantAccessGrant)
            .where(
                PlantAccessGrant.membership_id == membership_id,
                PlantAccessGrant.plant_id == plant_id,
            )
            .with_for_update()
        )

    def add_account_audit(
        self,
        *,
        account_id: uuid.UUID,
        membership_id: uuid.UUID,
        role_preset: str,
        farm_id: uuid.UUID,
        action_type: str,
        target_type: str,
        target_id: uuid.UUID,
        plant_id: uuid.UUID | None,
        request_id: str,
        before_summary: dict[str, object],
        after_summary: dict[str, object],
    ) -> None:
        self.session.add(
            AdminAuditRecord(
                farm_id=farm_id,
                actor_kind="account",
                actor_account_id=account_id,
                actor_membership_id=membership_id,
                actor_role_preset=role_preset,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                plant_id=plant_id,
                request_id=request_id,
                before_summary=before_summary,
                after_summary=after_summary,
                source_refs=[],
            )
        )

    def get_plant_access_snapshot(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessSnapshot | None:
        row = self.session.execute(
            select(Plant, PlantAccessGrant)
            .select_from(FarmMembership)
            .join(Account, Account.account_id == FarmMembership.account_id)
            .join(
                Plant,
                and_(
                    Plant.farm_id == FarmMembership.farm_id,
                    Plant.plant_id == plant_id,
                ),
            )
            .outerjoin(
                PlantAccessGrant,
                and_(
                    PlantAccessGrant.membership_id
                    == FarmMembership.membership_id,
                    PlantAccessGrant.plant_id == Plant.plant_id,
                ),
            )
            .where(
                FarmMembership.membership_id == membership_id,
                FarmMembership.farm_id == farm_id,
                FarmMembership.membership_status == "active",
                Account.account_status == "active",
            )
        ).one_or_none()
        if row is None:
            return None
        plant, grant = row
        grant_snapshot = None
        if grant is not None:
            grant_snapshot = PlantGrantSnapshot(
                grant_id=grant.grant_id,
                membership_id=grant.membership_id,
                farm_id=farm_id,
                plant_id=grant.plant_id,
                status=grant.status,
                plant_approve_actions=grant.plant_approve_actions,
            )
        return PlantAccessSnapshot(
            plant=PlantSnapshot(
                plant_id=plant.plant_id,
                farm_id=plant.farm_id,
                status=plant.status,
            ),
            grant=grant_snapshot,
        )


class PersistedPlantAccessSnapshotProvider:
    """Open a short read session for each FT-001 resolver snapshot request."""

    def __init__(self, database: DatabaseHandle) -> None:
        self._database = database

    def __call__(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessSnapshot | None:
        with self._database.session() as session:
            return FarmRepository(session).get_plant_access_snapshot(
                farm_id=farm_id,
                membership_id=membership_id,
                plant_id=plant_id,
            )


__all__ = ["FarmRepository", "PersistedPlantAccessSnapshotProvider"]
