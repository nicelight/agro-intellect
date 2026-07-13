from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import Account, FarmMembership, Plant, PlantAccessGrant


@dataclass(frozen=True, slots=True)
class CurrentPlantAuthorization:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    role_preset: str
    permission_source: str
    grant_id: uuid.UUID | None
    archived: bool

    def scope_value(self) -> dict[str, object]:
        return {"farm_id": str(self.farm_id), "plant_id": str(self.plant_id), "role_preset": self.role_preset, "operation_kind": "normal_read", "permission_source": self.permission_source, "grant_id": str(self.grant_id) if self.grant_id else None}


def lock_current_plant_authorization(
    session: Session,
    actor: ActorContext,
    plant_id: uuid.UUID,
    *,
    allow_archived: bool,
) -> CurrentPlantAuthorization | None:
    identity = session.execute(
        select(Account, FarmMembership)
        .join(FarmMembership, FarmMembership.account_id == Account.account_id)
        .where(Account.account_id == actor.account_id, Account.account_status == "active", FarmMembership.membership_id == actor.membership_id, FarmMembership.farm_id == actor.farm_id, FarmMembership.membership_status == "active", FarmMembership.role_preset == actor.role_preset.value)
        .with_for_update()
    ).one_or_none()
    plant = session.scalar(select(Plant).where(Plant.plant_id == plant_id, Plant.farm_id == actor.farm_id).with_for_update())
    if identity is None or plant is None or (plant.status != "active" and not (allow_archived and plant.status == "archived")):
        return None
    if actor.role_preset.value == "boss":
        return CurrentPlantAuthorization(actor.farm_id, plant_id, "boss", "boss_role", None, plant.status == "archived")
    grant = session.scalar(select(PlantAccessGrant).where(PlantAccessGrant.membership_id == actor.membership_id, PlantAccessGrant.plant_id == plant_id, PlantAccessGrant.status == "active").with_for_update())
    if grant is None or actor.role_preset.value not in {"engineer", "consultant"}:
        return None
    return CurrentPlantAuthorization(actor.farm_id, plant_id, actor.role_preset.value, "plant_access_grant", grant.grant_id, plant.status == "archived")


__all__ = ["CurrentPlantAuthorization", "lock_current_plant_authorization"]
