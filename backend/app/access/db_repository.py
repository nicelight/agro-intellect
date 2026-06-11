from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.access.models import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    FarmStatus,
    LocalSession,
    MembershipRole,
    MembershipStatus,
    OneFarmViolation,
    SessionStatus,
)
from backend.app.config import SyncStatus
from backend.app.db import models as orm


class DbAccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _account_from_orm(o: orm.Account) -> Account:
        return Account(
            account_id=o.account_id,
            display_name=o.display_name,
            login_identifier=o.login_identifier,
            status=AccountStatus(o.status),
            created_at=o.created_at,
            updated_at=o.updated_at,
            created_by_account_id=o.created_by_account_id,
            updated_by_account_id=o.updated_by_account_id,
        )

    @staticmethod
    def _farm_from_orm(o: orm.Farm) -> Farm:
        return Farm(
            farm_id=o.farm_id,
            display_name=o.display_name,
            status=FarmStatus(o.status),
            sync_status=SyncStatus(o.sync_status),
            created_at=o.created_at,
            updated_at=o.updated_at,
        )

    @staticmethod
    def _membership_from_orm(o: orm.FarmMembership) -> FarmMembership:
        return FarmMembership(
            membership_id=o.membership_id,
            account_id=o.account_id,
            farm_id=o.farm_id,
            role=MembershipRole(o.role_preset),
            status=MembershipStatus(o.status),
            created_at=o.created_at,
            updated_at=o.updated_at,
            changed_by_account_id=o.changed_by_account_id,
        )

    @staticmethod
    def _session_from_orm(o: orm.LocalSession) -> LocalSession:
        return LocalSession(
            session_id=o.session_id,
            account_id=o.account_id,
            farm_id=o.farm_id,
            membership_id=o.membership_id,
            session_hash=o.session_hash,
            session_ref=o.session_ref,
            auth_provenance_ref=o.auth_provenance_ref,
            status=SessionStatus(o.status),
            created_at=o.created_at,
            expires_at=o.expires_at,
            revoked_at=o.revoked_at,
            last_seen_at=o.last_seen_at,
            created_request_ref=o.created_request_ref,
            revoked_request_ref=o.revoked_request_ref,
        )

    # ── public API ───────────────────────────────────────────

    async def add_account(self, account: Account) -> Account:
        orm_obj = orm.Account(
            account_id=account.account_id,
            display_name=account.display_name,
            login_identifier=account.login_identifier,
            status=account.status.value,
            created_at=account.created_at,
            updated_at=account.updated_at,
            created_by_account_id=account.created_by_account_id,
            updated_by_account_id=account.updated_by_account_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.commit()
        return account

    async def add_farm(self, farm: Farm) -> Farm:
        result = await self._session.execute(
            select(orm.Farm.farm_id).where(orm.Farm.farm_id != farm.farm_id).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            raise OneFarmViolation("MVP supports exactly one local Farm")

        orm_obj = orm.Farm(
            farm_id=farm.farm_id,
            display_name=farm.display_name,
            status=farm.status.value,
            sync_status=farm.sync_status.value,
            one_farm_guard=True,
            created_at=farm.created_at,
            updated_at=farm.updated_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.commit()
        return farm

    async def add_membership(self, membership: FarmMembership) -> FarmMembership:
        account = await self._session.get(orm.Account, membership.account_id)
        if account is None:
            raise KeyError("membership account does not exist")

        farm = await self._session.get(orm.Farm, membership.farm_id)
        if farm is None:
            raise KeyError("membership farm does not exist")

        result = await self._session.execute(
            select(orm.FarmMembership).where(
                orm.FarmMembership.account_id == membership.account_id
            ).limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            if existing.farm_id != membership.farm_id:
                raise OneFarmViolation("MVP forbids multi-Farm membership")
            if existing.membership_id != membership.membership_id:
                raise ValueError("account already has a FarmMembership")

        orm_obj = orm.FarmMembership(
            membership_id=membership.membership_id,
            account_id=membership.account_id,
            farm_id=membership.farm_id,
            role_preset=membership.role.value,
            status=membership.status.value,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
            changed_by_account_id=membership.changed_by_account_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.commit()
        return membership

    async def add_session(self, session: LocalSession) -> LocalSession:
        account = await self._session.get(orm.Account, session.account_id)
        if account is None:
            raise KeyError("session account does not exist")

        farm = await self._session.get(orm.Farm, session.farm_id)
        if farm is None:
            raise KeyError("session farm does not exist")

        membership = await self._session.get(orm.FarmMembership, session.membership_id)
        if membership is None:
            raise KeyError("session membership does not exist")

        orm_obj = orm.LocalSession(
            session_id=session.session_id,
            account_id=session.account_id,
            farm_id=session.farm_id,
            membership_id=session.membership_id,
            session_hash=session.session_hash,
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            status=session.status.value,
            created_at=session.created_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            last_seen_at=session.last_seen_at,
            created_request_ref=session.created_request_ref,
            revoked_request_ref=session.revoked_request_ref,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.commit()
        return session

    async def get_account(self, account_id: str) -> Account | None:
        o = await self._session.get(orm.Account, account_id)
        if o is None:
            return None
        return self._account_from_orm(o)

    async def get_farm(self, farm_id: str) -> Farm | None:
        o = await self._session.get(orm.Farm, farm_id)
        if o is None:
            return None
        return self._farm_from_orm(o)

    async def get_single_farm(self) -> Farm | None:
        result = await self._session.execute(select(orm.Farm))
        rows = list(result.scalars().all())
        if len(rows) > 1:
            raise OneFarmViolation("MVP supports exactly one local Farm")
        if not rows:
            return None
        return self._farm_from_orm(rows[0])

    async def get_membership(self, membership_id: str) -> FarmMembership | None:
        o = await self._session.get(orm.FarmMembership, membership_id)
        if o is None:
            return None
        return self._membership_from_orm(o)

    async def get_membership_for_account(self, account_id: str) -> FarmMembership | None:
        result = await self._session.execute(
            select(orm.FarmMembership).where(
                orm.FarmMembership.account_id == account_id
            )
        )
        rows = list(result.scalars().all())
        if len(rows) > 1:
            raise OneFarmViolation("MVP forbids multi-Farm membership")
        if not rows:
            return None
        return self._membership_from_orm(rows[0])

    async def get_session_by_hash(self, session_hash: str) -> LocalSession | None:
        result = await self._session.execute(
            select(orm.LocalSession).where(
                orm.LocalSession.session_hash == session_hash
            ).limit(1)
        )
        o = result.scalar_one_or_none()
        if o is None:
            return None
        return self._session_from_orm(o)

    async def get_session_by_ref(self, session_ref: str) -> LocalSession | None:
        result = await self._session.execute(
            select(orm.LocalSession).where(
                orm.LocalSession.session_ref == session_ref
            ).limit(1)
        )
        o = result.scalar_one_or_none()
        if o is None:
            return None
        return self._session_from_orm(o)

    async def get_account_by_login(self, login_identifier: str) -> Account | None:
        result = await self._session.execute(
            select(orm.Account).where(
                orm.Account.login_identifier == login_identifier
            ).limit(1)
        )
        o = result.scalar_one_or_none()
        if o is None:
            return None
        return self._account_from_orm(o)

    async def update_account_status(
        self, account_id: str, status: AccountStatus
    ) -> Account:
        o = await self._session.get(orm.Account, account_id)
        if o is None:
            raise KeyError(account_id)
        o.status = status.value
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(o)
        return self._account_from_orm(o)

    async def update_membership_status(
        self, membership_id: str, status: MembershipStatus
    ) -> FarmMembership:
        o = await self._session.get(orm.FarmMembership, membership_id)
        if o is None:
            raise KeyError(membership_id)
        o.status = status.value
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(o)
        return self._membership_from_orm(o)

    async def revoke_session(
        self,
        session_id: str,
        *,
        revoked_at: datetime,
        request_ref: str | None = None,
    ) -> LocalSession:
        o = await self._session.get(orm.LocalSession, session_id)
        if o is None:
            raise KeyError(session_id)
        o.status = SessionStatus.REVOKED.value
        o.revoked_at = revoked_at
        o.revoked_request_ref = request_ref
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(o)
        return self._session_from_orm(o)

    async def get_accounts_iter(self) -> list[Account]:
        result = await self._session.execute(select(orm.Account))
        return [self._account_from_orm(row) for row in result.scalars().all()]

    async def get_sessions_iter(self) -> list[LocalSession]:
        result = await self._session.execute(select(orm.LocalSession))
        return [self._session_from_orm(row) for row in result.scalars().all()]
