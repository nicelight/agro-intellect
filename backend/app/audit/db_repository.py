from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.audit.models import AdminAuditAction, AdminAuditRecord
from backend.app.db import models as orm


class DbAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _record_from_orm(o: orm.AdminAuditRecord) -> AdminAuditRecord:
        return AdminAuditRecord(
            audit_id=o.audit_id,
            action=AdminAuditAction(o.action),
            actor_account_id=o.actor_account_id,
            target_account_id=o.target_account_id,
            farm_id=o.farm_id,
            membership_id=o.membership_id,
            details=o.details,
            auth_provenance_ref=o.auth_provenance_ref,
            request_ref=o.request_ref,
            created_at=o.created_at,
        )

    async def add_record(self, record: AdminAuditRecord) -> None:
        orm_obj = orm.AdminAuditRecord(
            audit_id=record.audit_id,
            action=record.action.value,
            actor_account_id=record.actor_account_id,
            target_account_id=record.target_account_id,
            farm_id=record.farm_id,
            membership_id=record.membership_id,
            details=record.details,
            auth_provenance_ref=record.auth_provenance_ref,
            request_ref=record.request_ref,
            created_at=record.created_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.commit()

    async def list_records(
        self,
        account_id: str | None = None,
        action: AdminAuditAction | None = None,
        limit: int = 50,
    ) -> list[AdminAuditRecord]:
        stmt = select(orm.AdminAuditRecord)
        if account_id is not None:
            stmt = stmt.where(orm.AdminAuditRecord.actor_account_id == account_id)
        if action is not None:
            stmt = stmt.where(orm.AdminAuditRecord.action == action.value)
        stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [self._record_from_orm(row) for row in result.scalars().all()]

    async def get_records_for_farm(
        self,
        farm_id: str,
        limit: int = 50,
    ) -> list[AdminAuditRecord]:
        stmt = (
            select(orm.AdminAuditRecord)
            .where(orm.AdminAuditRecord.farm_id == farm_id)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._record_from_orm(row) for row in result.scalars().all()]
