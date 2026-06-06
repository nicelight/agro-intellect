"""Plant domain models for the single-Farm workspace.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class PlantStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlantAccessGrantStatus(str, Enum):
    GRANTED = "granted"
    REVOKED = "revoked"


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class Plant:
    plant_id: str
    farm_id: str
    canonical_label: str
    display_name: str
    state: PlantStatus = PlantStatus.ACTIVE
    created_by_actor_ref: str = ""
    created_at: datetime = None  # type: ignore[assignment]
    archived_at: datetime | None = None
    archived_by_actor_ref: str | None = None
    archive_reason: str | None = None
    restored_at: datetime | None = None
    restored_by_actor_ref: str | None = None

    def __post_init__(self) -> None:
        now = utc_now()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        _require_text(self.plant_id, "plant_id")
        _require_text(self.farm_id, "farm_id")
        _require_text(self.canonical_label, "canonical_label")
        _require_text(self.display_name, "display_name")

    @property
    def is_active(self) -> bool:
        return self.state is PlantStatus.ACTIVE

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "farm_id": self.farm_id,
            "canonical_label": self.canonical_label,
            "display_name": self.display_name,
            "state": self.state.value,
            "created_by_actor_ref": self.created_by_actor_ref,
            "created_at": _iso(self.created_at),
            "archived_at": _iso(self.archived_at),
            "archived_by_actor_ref": self.archived_by_actor_ref,
            "archive_reason": self.archive_reason,
            "restored_at": _iso(self.restored_at),
            "restored_by_actor_ref": self.restored_by_actor_ref,
        }


@dataclass(frozen=True, slots=True)
class PlantAccessGrant:
    grant_id: str
    farm_id: str
    plant_id: str
    account_id: str
    membership_id: str
    state: PlantAccessGrantStatus = PlantAccessGrantStatus.GRANTED
    can_view: bool = True
    can_work: bool = True
    plant_approve_actions: bool = False
    created_by_actor_ref: str = ""
    updated_by_actor_ref: str = ""
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.grant_id, "grant_id")
        _require_text(self.farm_id, "farm_id")
        _require_text(self.plant_id, "plant_id")
        _require_text(self.account_id, "account_id")
        _require_text(self.membership_id, "membership_id")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "farm_id": self.farm_id,
            "plant_id": self.plant_id,
            "account_id": self.account_id,
            "membership_id": self.membership_id,
            "state": self.state.value,
            "can_view": self.can_view,
            "can_work": self.can_work,
            "plant_approve_actions": self.plant_approve_actions,
            "created_by_actor_ref": self.created_by_actor_ref,
            "updated_by_actor_ref": self.updated_by_actor_ref,
            "revoked_at": _iso(self.revoked_at),
        }
