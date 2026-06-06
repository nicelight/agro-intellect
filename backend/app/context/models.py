"""ActorContext domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class ActorContextState(str, Enum):
    RESOLVED = "resolved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class PlantPermission:
    plant_id: str
    grant_state: str
    can_view: bool
    can_work: bool
    plant_approve_actions: bool


@dataclass(frozen=True, slots=True)
class ActorContext:
    state: ActorContextState
    account_id: str | None = None
    farm_id: str | None = None
    membership_id: str | None = None
    role: str | None = None
    membership_status: str | None = None
    plant_permissions: tuple[PlantPermission, ...] = ()
    session_ref: str | None = None
    auth_provenance_ref: str | None = None
    request_ref: str | None = None
    resolved_at: datetime | None = None
