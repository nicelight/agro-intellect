"""Persistence primitives for the Access & Admin bounded module."""

from .farm_bootstrap import (
    CanonicalFarmBootstrapError,
    CanonicalFarmBootstrapResult,
    bootstrap_canonical_farm,
)
from .farm_repository import FarmRepository
from .admin_repository import AdminRepository
from .admin_service import (
    FIRST_BOSS_REQUEST_ID,
    AccountMembershipResult,
    AdminCommandError,
    AdminCommandErrorCode,
    AdminService,
    PlantProjection,
)
from .models import (
    Account,
    AdminAuditRecord,
    Base,
    Farm,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
    normalize_login_name,
)

__all__ = [
    "Account",
    "AccountMembershipResult",
    "AdminCommandError",
    "AdminCommandErrorCode",
    "AdminRepository",
    "AdminService",
    "AdminAuditRecord",
    "Base",
    "CanonicalFarmBootstrapError",
    "CanonicalFarmBootstrapResult",
    "FIRST_BOSS_REQUEST_ID",
    "Farm",
    "FarmMembership",
    "FarmRepository",
    "LocalSession",
    "Plant",
    "PlantAccessGrant",
    "PlantProjection",
    "bootstrap_canonical_farm",
    "normalize_login_name",
]
