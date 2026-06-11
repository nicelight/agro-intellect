from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from backend.app.access.models import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    LocalSession,
    MembershipRole,
    MembershipStatus,
    OneFarmViolation,
    SessionStatus,
)
from backend.app.audit.models import AdminAuditAction, AdminAuditRecord
from backend.app.config import SyncStatus
from backend.app.plants.models import Plant, PlantAccessGrant, PlantAccessGrantStatus, PlantStatus

TOMATO_001_FARM_ID = "farm_local"
TOMATO_001_PLANT_ID = "tomato_001"


class FakeAccessRepository:
    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.farms: dict[str, Farm] = {}
        self.memberships: dict[str, FarmMembership] = {}
        self.sessions_by_hash: dict[str, LocalSession] = {}
        self.sessions_by_id: dict[str, LocalSession] = {}

    async def add_account(self, account: Account) -> Account:
        self.accounts[account.account_id] = account
        return account

    async def add_farm(self, farm: Farm) -> Farm:
        existing = await self.get_single_farm()
        if existing is not None and existing.farm_id != farm.farm_id:
            raise OneFarmViolation("MVP supports exactly one local Farm")
        self.farms[farm.farm_id] = farm
        return farm

    async def add_membership(self, membership: FarmMembership) -> FarmMembership:
        if membership.account_id not in self.accounts:
            raise KeyError("membership account does not exist")
        if membership.farm_id not in self.farms:
            raise KeyError("membership farm does not exist")
        for existing in self.memberships.values():
            if existing.account_id == membership.account_id and existing.farm_id != membership.farm_id:
                raise OneFarmViolation("MVP forbids multi-Farm membership")
            if existing.account_id == membership.account_id and existing.membership_id != membership.membership_id:
                raise ValueError("account already has a FarmMembership")
        self.memberships[membership.membership_id] = membership
        return membership

    async def add_session(self, session: LocalSession) -> LocalSession:
        if session.account_id not in self.accounts:
            raise KeyError("session account does not exist")
        if session.farm_id not in self.farms:
            raise KeyError("session farm does not exist")
        if session.membership_id not in self.memberships:
            raise KeyError("session membership does not exist")
        self.sessions_by_hash[session.session_hash] = session
        self.sessions_by_id[session.session_id] = session
        return session

    async def get_account(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    async def get_farm(self, farm_id: str) -> Farm | None:
        return self.farms.get(farm_id)

    async def get_single_farm(self) -> Farm | None:
        if not self.farms:
            return None
        if len(self.farms) > 1:
            raise OneFarmViolation("MVP supports exactly one local Farm")
        return next(iter(self.farms.values()))

    async def get_membership(self, membership_id: str) -> FarmMembership | None:
        return self.memberships.get(membership_id)

    async def get_membership_for_account(self, account_id: str) -> FarmMembership | None:
        matches = [m for m in self.memberships.values() if m.account_id == account_id]
        if len(matches) > 1:
            raise OneFarmViolation("MVP forbids multi-Farm membership")
        return matches[0] if matches else None

    async def get_session_by_hash(self, session_hash: str) -> LocalSession | None:
        return self.sessions_by_hash.get(session_hash)

    async def update_account_status(self, account_id: str, status: AccountStatus) -> Account:
        account = self.accounts[account_id]
        updated = replace(account, status=status)
        self.accounts[account_id] = updated
        return updated

    async def update_membership_status(self, membership_id: str, status: MembershipStatus) -> FarmMembership:
        membership = self.memberships[membership_id]
        updated = replace(membership, status=status)
        self.memberships[membership_id] = updated
        return updated

    async def revoke_session(self, session_id: str, *, revoked_at: datetime, request_ref: str | None = None) -> LocalSession:
        session = self.sessions_by_id[session_id]
        updated = replace(session, status=SessionStatus.REVOKED, revoked_at=revoked_at, revoked_request_ref=request_ref)
        self.sessions_by_id[session_id] = updated
        self.sessions_by_hash[updated.session_hash] = updated
        return updated

    async def get_accounts_iter(self) -> list[Account]:
        return list(self.accounts.values())

    async def get_sessions_iter(self) -> list[LocalSession]:
        return list(self.sessions_by_id.values())


class FakeAuditRepository:
    def __init__(self) -> None:
        self._records: list[AdminAuditRecord] = []

    async def add_record(self, record: AdminAuditRecord) -> None:
        self._records.append(record)

    async def list_records(self, account_id: str | None = None, action: AdminAuditAction | None = None, limit: int = 50) -> list[AdminAuditRecord]:
        results = list(self._records)
        if account_id is not None:
            results = [r for r in results if r.actor_account_id == account_id]
        if action is not None:
            results = [r for r in results if r.action is action]
        return results[:limit]

    async def get_records_for_farm(self, farm_id: str, limit: int = 50) -> list[AdminAuditRecord]:
        results = [r for r in self._records if r.farm_id == farm_id]
        return results[:limit]


class FakePlantRepository:
    def __init__(self, auto_seed: bool = True) -> None:
        self.plants: dict[str, Plant] = {}
        self.grants: dict[str, PlantAccessGrant] = {}
        if auto_seed:
            import uuid
            from datetime import UTC, datetime

            now = datetime.now(UTC)
            self.plants[TOMATO_001_PLANT_ID] = Plant(
                plant_id=TOMATO_001_PLANT_ID,
                farm_id=TOMATO_001_FARM_ID,
                canonical_label="Tomato 001",
                display_name="Tomato 001",
                state=PlantStatus.ACTIVE,
                created_by_actor_ref="system_seed",
                created_at=now,
            )

    async def add_plant(self, plant: Plant) -> Plant:
        self.plants[plant.plant_id] = plant
        return plant

    async def get_plant(self, plant_id: str) -> Plant | None:
        return self.plants.get(plant_id)

    async def get_plants_by_farm(self, farm_id: str) -> list[Plant]:
        return [p for p in self.plants.values() if p.farm_id == farm_id]

    async def get_active_plants_by_farm(self, farm_id: str) -> list[Plant]:
        return [p for p in self.plants.values() if p.farm_id == farm_id and p.state is PlantStatus.ACTIVE]

    async def get_plant_count(self, farm_id: str | None = None) -> int:
        if farm_id is not None:
            return len([p for p in self.plants.values() if p.farm_id == farm_id])
        return len(self.plants)

    async def add_grant(self, grant: PlantAccessGrant) -> PlantAccessGrant:
        self.grants[grant.grant_id] = grant
        return grant

    async def get_grant(self, grant_id: str) -> PlantAccessGrant | None:
        return self.grants.get(grant_id)

    async def get_grants_for_plant(self, plant_id: str) -> list[PlantAccessGrant]:
        return [g for g in self.grants.values() if g.plant_id == plant_id]

    async def get_grants_for_account(self, account_id: str) -> list[PlantAccessGrant]:
        return [g for g in self.grants.values() if g.account_id == account_id]
