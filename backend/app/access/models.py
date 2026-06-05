"""Domain models for local access and session foundations.

@docs .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AccountStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class FarmStatus(str, Enum):
    ACTIVE = "active"


class MembershipRole(str, Enum):
    BOSS = "boss"
    ENGINEER = "engineer"
    CONSULTANT = "consultant"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"
    REMOVED = "removed"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class SessionValidationState(str, Enum):
    RESOLVED = "resolved"
    DENIED = "denied"
    EXPIRED = "expired"


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class Account:
    account_id: str
    display_name: str
    login_identifier: str
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]
    created_by_account_id: str | None = None
    updated_by_account_id: str | None = None

    def __post_init__(self) -> None:
        now = utc_now()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        _require_text(self.account_id, "account_id")
        _require_text(self.display_name, "display_name")
        _require_text(self.login_identifier, "login_identifier")

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "display_name": self.display_name,
            "login_identifier": self.login_identifier,
            "status": self.status.value,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "created_by_account_id": self.created_by_account_id,
            "updated_by_account_id": self.updated_by_account_id,
        }


@dataclass(frozen=True, slots=True)
class Farm:
    farm_id: str
    display_name: str
    status: FarmStatus = FarmStatus.ACTIVE
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        now = utc_now()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        _require_text(self.farm_id, "farm_id")
        _require_text(self.display_name, "display_name")

    @property
    def is_active(self) -> bool:
        return self.status is FarmStatus.ACTIVE

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "farm_id": self.farm_id,
            "display_name": self.display_name,
            "status": self.status.value,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


@dataclass(frozen=True, slots=True)
class FarmMembership:
    membership_id: str
    account_id: str
    farm_id: str
    role: MembershipRole
    status: MembershipStatus = MembershipStatus.ACTIVE
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]
    changed_by_account_id: str | None = None

    def __post_init__(self) -> None:
        now = utc_now()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)
        _require_text(self.membership_id, "membership_id")
        _require_text(self.account_id, "account_id")
        _require_text(self.farm_id, "farm_id")

    @property
    def is_active(self) -> bool:
        return self.status is MembershipStatus.ACTIVE

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "membership_id": self.membership_id,
            "account_id": self.account_id,
            "farm_id": self.farm_id,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "changed_by_account_id": self.changed_by_account_id,
        }


@dataclass(frozen=True, slots=True)
class LocalSession:
    session_id: str
    account_id: str
    farm_id: str
    membership_id: str
    session_hash: str = field(repr=False)
    session_ref: str
    auth_provenance_ref: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = None  # type: ignore[assignment]
    expires_at: datetime = None  # type: ignore[assignment]
    revoked_at: datetime | None = None
    last_seen_at: datetime | None = None
    created_request_ref: str | None = None
    revoked_request_ref: str | None = None

    def __post_init__(self) -> None:
        now = utc_now()
        if self.created_at is None:
            object.__setattr__(self, "created_at", now)
        if self.expires_at is None:
            raise ValueError("expires_at is required for local sessions")
        _require_text(self.session_id, "session_id")
        _require_text(self.account_id, "account_id")
        _require_text(self.farm_id, "farm_id")
        _require_text(self.membership_id, "membership_id")
        _require_text(self.session_hash, "session_hash")
        _require_text(self.session_ref, "session_ref")
        _require_text(self.auth_provenance_ref, "auth_provenance_ref")
        if len(self.session_hash) != 64:
            raise ValueError("session_hash must be a sha256 hex digest")
        if not self.session_ref.startswith("sess_ref_"):
            raise ValueError("session_ref must be redacted")
        if not self.auth_provenance_ref.startswith("auth_ref_"):
            raise ValueError("auth_provenance_ref must be redacted")

    @property
    def is_revoked(self) -> bool:
        return self.status is SessionStatus.REVOKED or self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "account_id": self.account_id,
            "farm_id": self.farm_id,
            "membership_id": self.membership_id,
            "session_ref": self.session_ref,
            "auth_provenance_ref": self.auth_provenance_ref,
            "status": self.status.value,
            "created_at": _iso(self.created_at),
            "expires_at": _iso(self.expires_at),
            "revoked_at": _iso(self.revoked_at),
            "last_seen_at": _iso(self.last_seen_at),
            "created_request_ref": self.created_request_ref,
            "revoked_request_ref": self.revoked_request_ref,
        }


@dataclass(frozen=True, slots=True)
class SessionValidationResult:
    state: SessionValidationState
    reason: str | None = None
    account_id: str | None = None
    farm_id: str | None = None
    membership_id: str | None = None
    role: MembershipRole | None = None
    membership_status: MembershipStatus | None = None
    session_ref: str | None = None
    auth_provenance_ref: str | None = None
    request_ref: str | None = None
    resolved_at: datetime = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.resolved_at is None:
            object.__setattr__(self, "resolved_at", utc_now())
        if self.state is SessionValidationState.RESOLVED:
            required = (
                self.account_id,
                self.farm_id,
                self.membership_id,
                self.role,
                self.membership_status,
                self.session_ref,
                self.auth_provenance_ref,
            )
            if any(value is None for value in required):
                raise ValueError("resolved session validation requires actor fields")

    @property
    def is_resolved(self) -> bool:
        return self.state is SessionValidationState.RESOLVED

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "reason": self.reason,
            "account_id": self.account_id,
            "farm_id": self.farm_id,
            "membership_id": self.membership_id,
            "role": self.role.value if self.role else None,
            "membership_status": (
                self.membership_status.value if self.membership_status else None
            ),
            "session_ref": self.session_ref,
            "auth_provenance_ref": self.auth_provenance_ref,
            "request_ref": self.request_ref,
            "resolved_at": _iso(self.resolved_at),
        }


def denied_session_result(
    reason: str,
    *,
    state: SessionValidationState = SessionValidationState.DENIED,
    session_ref: str | None = None,
    auth_provenance_ref: str | None = None,
    request_ref: str | None = None,
    now: datetime | None = None,
) -> SessionValidationResult:
    return SessionValidationResult(
        state=state,
        reason=reason,
        session_ref=session_ref,
        auth_provenance_ref=auth_provenance_ref,
        request_ref=request_ref,
        resolved_at=now or utc_now(),
    )


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
