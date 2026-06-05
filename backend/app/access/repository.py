"""Small repository boundary for local access foundation tests and services."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from backend.app.access.models import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    LocalSession,
    MembershipStatus,
    SessionStatus,
)


class OneFarmViolation(ValueError):
    """Raised when code attempts to create multi-Farm state in the MVP."""


class InMemoryAccessRepository:
    """Deterministic repository used until a PostgreSQL adapter exists.

    The SQL migration is the runtime authority target. This in-memory repository keeps
    TASK-001 unit tests focused on domain/session behavior without choosing an ORM.
    """

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.farms: dict[str, Farm] = {}
        self.memberships: dict[str, FarmMembership] = {}
        self.sessions_by_hash: dict[str, LocalSession] = {}
        self.sessions_by_id: dict[str, LocalSession] = {}

    def add_account(self, account: Account) -> Account:
        self.accounts[account.account_id] = account
        return account

    def add_farm(self, farm: Farm) -> Farm:
        existing = self.get_single_farm()
        if existing is not None and existing.farm_id != farm.farm_id:
            raise OneFarmViolation("MVP supports exactly one local Farm")
        self.farms[farm.farm_id] = farm
        return farm

    def add_membership(self, membership: FarmMembership) -> FarmMembership:
        if membership.account_id not in self.accounts:
            raise KeyError("membership account does not exist")
        if membership.farm_id not in self.farms:
            raise KeyError("membership farm does not exist")
        for existing in self.memberships.values():
            if (
                existing.account_id == membership.account_id
                and existing.farm_id != membership.farm_id
            ):
                raise OneFarmViolation("MVP forbids multi-Farm membership")
            if (
                existing.account_id == membership.account_id
                and existing.membership_id != membership.membership_id
            ):
                raise ValueError("account already has a FarmMembership")
        self.memberships[membership.membership_id] = membership
        return membership

    def add_session(self, session: LocalSession) -> LocalSession:
        if session.account_id not in self.accounts:
            raise KeyError("session account does not exist")
        if session.farm_id not in self.farms:
            raise KeyError("session farm does not exist")
        if session.membership_id not in self.memberships:
            raise KeyError("session membership does not exist")
        self.sessions_by_hash[session.session_hash] = session
        self.sessions_by_id[session.session_id] = session
        return session

    def get_account(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    def get_farm(self, farm_id: str) -> Farm | None:
        return self.farms.get(farm_id)

    def get_single_farm(self) -> Farm | None:
        if not self.farms:
            return None
        if len(self.farms) > 1:
            raise OneFarmViolation("MVP supports exactly one local Farm")
        return next(iter(self.farms.values()))

    def get_membership(self, membership_id: str) -> FarmMembership | None:
        return self.memberships.get(membership_id)

    def get_membership_for_account(self, account_id: str) -> FarmMembership | None:
        matches = [
            membership
            for membership in self.memberships.values()
            if membership.account_id == account_id
        ]
        if len(matches) > 1:
            raise OneFarmViolation("MVP forbids multi-Farm membership")
        return matches[0] if matches else None

    def get_session_by_hash(self, session_hash: str) -> LocalSession | None:
        return self.sessions_by_hash.get(session_hash)

    def update_account_status(self, account_id: str, status: AccountStatus) -> Account:
        account = self.accounts[account_id]
        updated = replace(account, status=status)
        self.accounts[account_id] = updated
        return updated

    def update_membership_status(
        self, membership_id: str, status: MembershipStatus
    ) -> FarmMembership:
        membership = self.memberships[membership_id]
        updated = replace(membership, status=status)
        self.memberships[membership_id] = updated
        return updated

    def revoke_session(
        self,
        session_id: str,
        *,
        revoked_at: datetime,
        request_ref: str | None = None,
    ) -> LocalSession:
        session = self.sessions_by_id[session_id]
        updated = replace(
            session,
            status=SessionStatus.REVOKED,
            revoked_at=revoked_at,
            revoked_request_ref=request_ref,
        )
        self.sessions_by_id[session_id] = updated
        self.sessions_by_hash[updated.session_hash] = updated
        return updated
