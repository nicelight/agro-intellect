from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..access_admin.models import Account, FarmMembership, Plant, PlantAccessGrant
from ..access_admin.permissions import (
    PlantAccessSnapshot,
    PlantGrantSnapshot,
    PlantSnapshot,
)
from ..plant_operations.models import DailyCheckIn
from .models import PhotoCatalogItem


class PhotoIntakeRepository:
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
            .join(Plant, Plant.farm_id == FarmMembership.farm_id)
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

    def check_in_belongs_to_plant(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        check_in_id: uuid.UUID,
    ) -> bool:
        return (
            self.session.scalar(
                select(DailyCheckIn.check_in_id)
                .where(
                    DailyCheckIn.check_in_id == check_in_id,
                    DailyCheckIn.farm_id == farm_id,
                    DailyCheckIn.plant_id == plant_id,
                )
                .with_for_update()
            )
            is not None
        )

    def add_photo(self, item: PhotoCatalogItem) -> None:
        self.session.add(item)

    def list_photos(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        limit: int,
        after: tuple[datetime, uuid.UUID] | None = None,
    ) -> list[PhotoCatalogItem]:
        statement = select(PhotoCatalogItem).where(
            PhotoCatalogItem.farm_id == farm_id,
            PhotoCatalogItem.plant_id == plant_id,
        )
        if after is not None:
            uploaded_at, photo_id = after
            statement = statement.where(
                or_(
                    PhotoCatalogItem.uploaded_at < uploaded_at,
                    and_(
                        PhotoCatalogItem.uploaded_at == uploaded_at,
                        PhotoCatalogItem.photo_id > photo_id,
                    ),
                )
            )
        return list(
            self.session.scalars(
                statement.order_by(
                    PhotoCatalogItem.uploaded_at.desc(),
                    PhotoCatalogItem.photo_id,
                )
                .limit(limit)
            )
        )

    def get_photo(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> PhotoCatalogItem | None:
        return self.session.scalar(
            select(PhotoCatalogItem).where(
                PhotoCatalogItem.farm_id == farm_id,
                PhotoCatalogItem.plant_id == plant_id,
                PhotoCatalogItem.photo_id == photo_id,
            )
        )

    def flush(self) -> None:
        self.session.flush()


__all__ = ["PhotoIntakeRepository"]
