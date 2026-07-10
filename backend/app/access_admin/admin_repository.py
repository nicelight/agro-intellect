from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    Plant,
    PlantAccessGrant,
    normalize_login_name,
)


class AdminRepository:
    """Persistence adapter for FT-003 Boss identity and audit operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_farms(self) -> list[Farm]:
        return list(
            self.session.scalars(select(Farm).order_by(Farm.farm_id).with_for_update())
        )

    def find_account_by_login(self, login_name: str) -> Account | None:
        normalized = normalize_login_name(login_name)
        if not normalized:
            return None
        return self.session.scalar(
            select(Account).where(Account.login_name == normalized)
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

    def lock_account_identity(
        self,
        *,
        farm_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> tuple[Account, FarmMembership] | None:
        row = self.session.execute(
            select(Account, FarmMembership)
            .join(FarmMembership, FarmMembership.account_id == Account.account_id)
            .where(
                Account.account_id == account_id,
                FarmMembership.farm_id == farm_id,
            )
            .with_for_update()
        ).one_or_none()
        return (row[0], row[1]) if row is not None else None

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

    def active_boss_count(self, *, farm_id: uuid.UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count(FarmMembership.membership_id))
                .join(Account, Account.account_id == FarmMembership.account_id)
                .where(
                    FarmMembership.farm_id == farm_id,
                    FarmMembership.role_preset == "boss",
                    FarmMembership.membership_status == "active",
                    Account.account_status == "active",
                )
            )
            or 0
        )

    def add_account(self, account: Account) -> None:
        self.session.add(account)

    def add_membership(self, membership: FarmMembership) -> None:
        self.session.add(membership)

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
        before_summary: dict[str, object],
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
                before_summary=before_summary,
                after_summary=after_summary,
                source_refs=[],
            )
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

    def list_personnel(
        self,
        *,
        farm_id: uuid.UUID,
        account_status: str | None = None,
        role_preset: str | None = None,
    ) -> list[tuple[Account, FarmMembership]]:
        statement = (
            select(Account, FarmMembership)
            .join(FarmMembership, FarmMembership.account_id == Account.account_id)
            .where(FarmMembership.farm_id == farm_id)
            .order_by(Account.login_name, Account.account_id)
        )
        if account_status is not None:
            statement = statement.where(Account.account_status == account_status)
        if role_preset is not None:
            statement = statement.where(FarmMembership.role_preset == role_preset)
        return [(row[0], row[1]) for row in self.session.execute(statement)]

    def list_plants(self, *, farm_id: uuid.UUID, include_archived: bool) -> list[Plant]:
        statement = (
            select(Plant)
            .where(Plant.farm_id == farm_id)
            .order_by(Plant.plant_key, Plant.plant_id)
        )
        if not include_archived:
            statement = statement.where(Plant.status == "active")
        return list(self.session.scalars(statement))

    def list_grants_for_plants(
        self, *, plant_ids: list[uuid.UUID]
    ) -> list[PlantAccessGrant]:
        if not plant_ids:
            return []
        return list(
            self.session.scalars(
                select(PlantAccessGrant).where(PlantAccessGrant.plant_id.in_(plant_ids))
            )
        )

    def list_audit_records(
        self,
        *,
        farm_id: uuid.UUID,
        limit: int,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        plant_id: uuid.UUID | None = None,
    ) -> list[AdminAuditRecord]:
        statement = (
            select(AdminAuditRecord)
            .where(AdminAuditRecord.farm_id == farm_id)
            .order_by(
                AdminAuditRecord.created_at.desc(),
                AdminAuditRecord.admin_audit_id.desc(),
            )
            .limit(limit)
        )
        if target_type is not None:
            statement = statement.where(AdminAuditRecord.target_type == target_type)
        if target_id is not None:
            statement = statement.where(AdminAuditRecord.target_id == target_id)
        if plant_id is not None:
            statement = statement.where(AdminAuditRecord.plant_id == plant_id)
        return list(self.session.scalars(statement))


__all__ = ["AdminRepository"]
