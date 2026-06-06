"""Access and local session foundation."""

from backend.app.access.authorization import (
    get_role_permissions,
    has_admin_authority,
    require_boss,
    require_engineer_or_boss,
    require_role,
)
from backend.app.access.models import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    FarmStatus,
    LocalSession,
    MembershipRole,
    MembershipStatus,
    SessionStatus,
    SessionValidationResult,
    SessionValidationState,
)
from backend.app.access.repository import InMemoryAccessRepository, OneFarmViolation
from backend.app.access.session_service import (
    create_local_session,
    revoke_local_session,
    validate_local_session,
)

__all__ = [
    "Account",
    "AccountStatus",
    "Farm",
    "FarmMembership",
    "FarmStatus",
    "InMemoryAccessRepository",
    "LocalSession",
    "MembershipRole",
    "MembershipStatus",
    "OneFarmViolation",
    "SessionStatus",
    "SessionValidationResult",
    "SessionValidationState",
    "create_local_session",
    "get_role_permissions",
    "has_admin_authority",
    "require_boss",
    "require_engineer_or_boss",
    "require_role",
    "revoke_local_session",
    "validate_local_session",
]
