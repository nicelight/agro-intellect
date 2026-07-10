from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import Account, FarmMembership, Plant


FIRST_BOSS_REQUEST_ID = "bootstrap-first-boss-local"


class AdminCommandErrorCode(StrEnum):
    FORBIDDEN = "forbidden"
    FARM_NOT_INITIALIZED = "farm_not_initialized"
    FARM_STATE_CONFLICT = "farm_state_conflict"
    ACCOUNT_NOT_FOUND = "account_not_found"
    MEMBERSHIP_NOT_FOUND = "membership_not_found"
    ACCOUNT_CONFLICT = "account_conflict"
    LAST_BOSS_CONFLICT = "last_boss_conflict"
    INVALID_INPUT = "invalid_input"
    PERSISTENCE_FAILED = "persistence_failed"


class AdminCommandError(RuntimeError):
    """Safe admin-service error; message contains no DB or credential detail."""

    def __init__(self, code: AdminCommandErrorCode) -> None:
        self.code = code
        super().__init__(f"Admin command failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class AccountMembershipResult:
    account: Account
    membership: FarmMembership
    changed: bool = True


@dataclass(frozen=True, slots=True)
class AccountMembershipProjection:
    account: Account
    membership: FarmMembership


@dataclass(frozen=True, slots=True)
class PlantProjection:
    plant: Plant
    grant_counts: dict[str, int]


__all__ = [
    "FIRST_BOSS_REQUEST_ID",
    "AccountMembershipProjection",
    "AccountMembershipResult",
    "AdminCommandError",
    "AdminCommandErrorCode",
    "PlantProjection",
]
