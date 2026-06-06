"""Role-based authorization helpers.

@docs .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.context.models import ActorContext

BOSS = "boss"
ENGINEER = "engineer"
CONSULTANT = "consultant"

ROLE_PERMISSIONS: dict[str, dict] = {
    BOSS: {
        "manage_accounts": True,
        "manage_memberships": True,
        "manage_roles": True,
        "manage_plants": True,
        "manage_plant_access": True,
        "view_admin_audit": True,
        "approve_physical_actions": True,
    },
    ENGINEER: {
        "manage_accounts": False,
        "manage_memberships": False,
        "manage_roles": False,
        "manage_plants": False,
        "manage_plant_access": False,
        "view_admin_audit": False,
        "approve_physical_actions": False,
    },
    CONSULTANT: {
        "manage_accounts": False,
        "manage_memberships": False,
        "manage_roles": False,
        "manage_plants": False,
        "manage_plant_access": False,
        "view_admin_audit": False,
        "approve_physical_actions": False,
    },
}


def require_role(actor_context: ActorContext, allowed_roles: set[str]) -> None:
    if actor_context.role not in allowed_roles:
        from backend.app.api.errors import AppError, ErrorCode

        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Your role does not have permission for this operation.",
            request_ref=actor_context.request_ref,
            next_actions=["switch_account", "contact_admin"],
        )


def require_boss(actor_context: ActorContext) -> None:
    require_role(actor_context, {BOSS})


def require_engineer_or_boss(actor_context: ActorContext) -> None:
    require_role(actor_context, {BOSS, ENGINEER})


def has_admin_authority(role: str) -> bool:
    return role == BOSS


def get_role_permissions(role: str) -> dict:
    return dict(ROLE_PERMISSIONS.get(role, {}))
