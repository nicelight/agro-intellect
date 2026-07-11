from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..access_admin.models import (
    Account,
    AdminAuditRecord,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from ..access_admin.permissions import (
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
)
from ..photo_intake.models import PhotoCatalogItem
from ..plant_operations.models import DailyCheckIn, ManualMeasurement


class PlantHistoryRepository:
    """Read-only persistence adapter for FT-006 Plant history projections."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_actor_identity(
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
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None

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
                    PlantAccessGrant.membership_id == FarmMembership.membership_id,
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

    def get_plant(self, *, farm_id: uuid.UUID, plant_id: uuid.UUID) -> Plant | None:
        return self.session.scalar(
            select(Plant).where(Plant.farm_id == farm_id, Plant.plant_id == plant_id)
        )

    def latest_check_in(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> DailyCheckIn | None:
        return self.session.scalar(
            select(DailyCheckIn)
            .where(
                DailyCheckIn.farm_id == farm_id,
                DailyCheckIn.plant_id == plant_id,
            )
            .order_by(
                DailyCheckIn.observed_at.desc(),
                DailyCheckIn.recorded_at.desc(),
                DailyCheckIn.check_in_id.desc(),
            )
            .limit(1)
        )

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

    def count_photos(self, *, farm_id: uuid.UUID, plant_id: uuid.UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count(PhotoCatalogItem.photo_id)).where(
                    PhotoCatalogItem.farm_id == farm_id,
                    PhotoCatalogItem.plant_id == plant_id,
                )
            )
            or 0
        )

    def count_history_entries(self, *, farm_id: uuid.UUID, plant_id: uuid.UUID) -> int:
        counts = [
            self.session.scalar(
                select(func.count(DailyCheckIn.check_in_id)).where(
                    DailyCheckIn.farm_id == farm_id,
                    DailyCheckIn.plant_id == plant_id,
                )
            ),
            self.session.scalar(
                select(func.count(ManualMeasurement.measurement_id)).where(
                    ManualMeasurement.farm_id == farm_id,
                    ManualMeasurement.plant_id == plant_id,
                )
            ),
            self.session.scalar(
                select(func.count(PhotoCatalogItem.photo_id)).where(
                    PhotoCatalogItem.farm_id == farm_id,
                    PhotoCatalogItem.plant_id == plant_id,
                )
            ),
            self.session.scalar(
                select(func.count(AdminAuditRecord.admin_audit_id)).where(
                    AdminAuditRecord.farm_id == farm_id,
                    AdminAuditRecord.plant_id == plant_id,
                )
            ),
        ]
        return sum(int(count or 0) for count in counts)

    def list_check_ins(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[DailyCheckIn]:
        return list(
            self.session.scalars(
                select(DailyCheckIn).where(
                    DailyCheckIn.farm_id == farm_id,
                    DailyCheckIn.plant_id == plant_id,
                )
            )
        )

    def list_measurements(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[ManualMeasurement]:
        return list(
            self.session.scalars(
                select(ManualMeasurement).where(
                    ManualMeasurement.farm_id == farm_id,
                    ManualMeasurement.plant_id == plant_id,
                )
            )
        )

    def list_photos(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[PhotoCatalogItem]:
        return list(
            self.session.scalars(
                select(PhotoCatalogItem).where(
                    PhotoCatalogItem.farm_id == farm_id,
                    PhotoCatalogItem.plant_id == plant_id,
                )
            )
        )

    def list_admin_audits(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> list[AdminAuditRecord]:
        return list(
            self.session.scalars(
                select(AdminAuditRecord).where(
                    AdminAuditRecord.farm_id == farm_id,
                    AdminAuditRecord.plant_id == plant_id,
                )
            )
        )


__all__ = ["PlantHistoryRepository"]
