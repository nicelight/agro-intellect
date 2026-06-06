"""Admin audit record models for role/access changes.

@docs .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class AdminAuditAction(str, Enum):
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DISABLED = "account_disabled"
    MEMBERSHIP_ROLE_CHANGED = "membership_role_changed"
    MEMBERSHIP_DISABLED = "membership_disabled"
    MEMBERSHIP_REMOVED = "membership_removed"
    PLANT_ACCESS_GRANTED = "plant_access_granted"
    PLANT_ACCESS_REVOKED = "plant_access_revoked"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class AdminAuditRecord:
    audit_id: str
    action: AdminAuditAction
    actor_account_id: str
    target_account_id: str | None = None
    farm_id: str | None = None
    membership_id: str | None = None
    details: dict | None = None
    auth_provenance_ref: str | None = None
    request_ref: str | None = None
    created_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", _utc_now())
