from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.models import Account, FarmMembership, Plant, PlantAccessGrant
from ..access_admin.permissions import (
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
)
from .models import DailyCheckIn, ManualMeasurement


class PlantOperationsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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

    def lock_plant_access_snapshot(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessSnapshot | None:
        row = self.session.execute(
            select(Plant)
            .select_from(FarmMembership)
            .join(Account, Account.account_id == FarmMembership.account_id)
            .join(
                Plant,
                Plant.farm_id == FarmMembership.farm_id,
            )
            .where(
                FarmMembership.membership_id == membership_id,
                FarmMembership.farm_id == farm_id,
                FarmMembership.membership_status == "active",
                Account.account_status == "active",
                Plant.plant_id == plant_id,
            )
            .with_for_update(of=(FarmMembership, Account, Plant))
        ).one_or_none()
        if row is None:
            return None
        plant = row[0]
        grant = self.session.scalar(
            select(PlantAccessGrant)
            .where(
                PlantAccessGrant.membership_id == membership_id,
                PlantAccessGrant.plant_id == plant_id,
            )
            .with_for_update()
        )
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

    def add_check_in(self, check_in: DailyCheckIn) -> None:
        self.session.add(check_in)

    def add_measurement(self, measurement: ManualMeasurement) -> None:
        self.session.add(measurement)

    def flush(self) -> None:
        self.session.flush()

    def latest_ph_measurement(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> ManualMeasurement | None:
        return self.session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == farm_id,
                ManualMeasurement.plant_id == plant_id,
                ManualMeasurement.ph.is_not(None),
            )
            .order_by(
                ManualMeasurement.measured_at.desc(),
                ManualMeasurement.recorded_at.desc(),
                ManualMeasurement.measurement_id.desc(),
            )
            .limit(1)
        )

    def latest_ec_measurement(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> ManualMeasurement | None:
        return self.session.scalar(
            select(ManualMeasurement)
            .where(
                ManualMeasurement.farm_id == farm_id,
                ManualMeasurement.plant_id == plant_id,
                ManualMeasurement.ec_ms_cm.is_not(None),
            )
            .order_by(
                ManualMeasurement.measured_at.desc(),
                ManualMeasurement.recorded_at.desc(),
                ManualMeasurement.measurement_id.desc(),
            )
            .limit(1)
        )


__all__ = ["PlantOperationsRepository"]
