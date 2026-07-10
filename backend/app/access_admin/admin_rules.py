from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from .actor_context import ActorContext
from .admin_repository import AdminRepository
from .admin_types import AdminCommandError, AdminCommandErrorCode
from .farm_bootstrap import CANONICAL_FARM_KEY
from .models import Farm, FarmMembership, normalize_login_name
from .permissions import RolePreset
from .security import hash_password


ACCOUNT_LOGIN_UNIQUE_CONSTRAINT = "uq_accounts_login_name"
ROLE_PRESETS = {role.value for role in RolePreset}
ACCOUNT_STATUSES = {"active", "disabled"}
AUDIT_TARGETS = {"account", "membership", "farm", "plant", "plant_access_grant"}


def require_canonical_farm(repository: AdminRepository) -> Farm:
    farms = repository.lock_farms()
    if not farms:
        raise AdminCommandError(AdminCommandErrorCode.FARM_NOT_INITIALIZED)
    if len(farms) != 1 or farms[0].farm_key != CANONICAL_FARM_KEY:
        raise AdminCommandError(AdminCommandErrorCode.FARM_STATE_CONFLICT)
    return farms[0]


def require_canonical_actor_farm(
    repository: AdminRepository, farm_id: uuid.UUID
) -> Farm:
    farm = require_canonical_farm(repository)
    if farm.farm_id != farm_id:
        raise AdminCommandError(AdminCommandErrorCode.FORBIDDEN)
    return farm


def require_boss_actor(
    repository: AdminRepository, actor: ActorContext
) -> FarmMembership:
    try:
        identity = repository.lock_actor_identity(
            account_id=actor.account_id,
            membership_id=actor.membership_id,
            farm_id=actor.farm_id,
        )
    except (AttributeError, TypeError):
        raise AdminCommandError(AdminCommandErrorCode.FORBIDDEN) from None
    if identity is None:
        raise AdminCommandError(AdminCommandErrorCode.FORBIDDEN)
    account, membership = identity
    if (
        account.account_status != "active"
        or membership.membership_status != "active"
        or membership.role_preset != RolePreset.BOSS.value
        or actor.role_preset is not RolePreset.BOSS
        or membership.account_id != actor.account_id
    ):
        raise AdminCommandError(AdminCommandErrorCode.FORBIDDEN)
    return membership


def normalize_login(value: object) -> str:
    if not isinstance(value, str):
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    normalized = normalize_login_name(value)
    if not normalized:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return normalized


def display_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value.strip()


def password_hash(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    try:
        return hash_password(value)
    except Exception:
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED) from None


def role(value: object) -> str:
    if not isinstance(value, str) or value not in ROLE_PRESETS:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def optional_role(value: object | None) -> str | None:
    if value is None:
        return None
    return role(value)


def optional_account_status(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in ACCOUNT_STATUSES:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def optional_target_type(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in AUDIT_TARGETS:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def optional_reason(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    reason = value.strip()
    if not reason:
        return None
    forbidden_fragments = ("password", "token", "authorization", "cookie", "dsn")
    lowered = reason.lower()
    if any(fragment in lowered for fragment in forbidden_fragments):
        return "[redacted]"
    return reason[:200]


def request_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value.strip()


def limit(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 100:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def offset(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def is_account_login_unique_violation(error: IntegrityError) -> bool:
    original = getattr(error, "orig", None)
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None)
        == ACCOUNT_LOGIN_UNIQUE_CONSTRAINT
    )


__all__ = [
    "display_name",
    "is_account_login_unique_violation",
    "limit",
    "normalize_login",
    "offset",
    "optional_account_status",
    "optional_reason",
    "optional_role",
    "optional_target_type",
    "password_hash",
    "request_id",
    "require_boss_actor",
    "require_canonical_actor_farm",
    "require_canonical_farm",
    "role",
]
