from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import uuid

from ..access_admin.admin_service import (
    AccountMembershipProjection,
    AccountMembershipResult,
    AdminCommandError,
    AdminCommandErrorCode,
    PlantProjection,
)
from ..access_admin.errors import AuthErrorCode
from ..access_admin.models import Account, FarmMembership
from ..access_admin.dependencies import ProtectedRouteDenied
from .admin_schemas import (
    AdminAccountSummary,
    AdminAuditSummary,
    AdminMembershipSummary,
    AdminPlantGrantCounts,
    AdminPlantProjection,
)


def admin_error_code(code: AdminCommandErrorCode) -> AuthErrorCode:
    return {
        AdminCommandErrorCode.FORBIDDEN: AuthErrorCode.FORBIDDEN,
        AdminCommandErrorCode.FARM_NOT_INITIALIZED: AuthErrorCode.FARM_NOT_INITIALIZED,
        AdminCommandErrorCode.FARM_STATE_CONFLICT: AuthErrorCode.FARM_STATE_CONFLICT,
        AdminCommandErrorCode.ACCOUNT_NOT_FOUND: AuthErrorCode.ADMIN_ACCOUNT_NOT_FOUND,
        AdminCommandErrorCode.MEMBERSHIP_NOT_FOUND: (
            AuthErrorCode.ADMIN_MEMBERSHIP_NOT_FOUND
        ),
        AdminCommandErrorCode.ACCOUNT_CONFLICT: AuthErrorCode.ADMIN_ACCOUNT_CONFLICT,
        AdminCommandErrorCode.LAST_BOSS_CONFLICT: (
            AuthErrorCode.ADMIN_LAST_BOSS_CONFLICT
        ),
        AdminCommandErrorCode.INVALID_INPUT: AuthErrorCode.VALIDATION_FAILED,
        AdminCommandErrorCode.PERSISTENCE_FAILED: (
            AuthErrorCode.ADMIN_PERSISTENCE_FAILED
        ),
    }[code]


def account_summary_from_result(
    result: AccountMembershipResult,
) -> AdminAccountSummary:
    return account_summary(result.account, result.membership)


def account_summary_from_projection(
    projection: AccountMembershipProjection,
) -> AdminAccountSummary:
    return account_summary(projection.account, projection.membership)


def account_summary(account: Account, membership: FarmMembership) -> AdminAccountSummary:
    return AdminAccountSummary(
        account_id=account.account_id,
        login_name=account.login_name,
        display_name=account.display_name,
        account_status=account.account_status,
        disabled_at=timestamp_or_none(account.disabled_at),
        created_at=timestamp(account.created_at),
        updated_at=timestamp(account.updated_at),
        membership=AdminMembershipSummary(
            membership_id=membership.membership_id,
            account_id=membership.account_id,
            farm_id=membership.farm_id,
            role_preset=membership.role_preset,
            membership_status=membership.membership_status,
            disabled_at=timestamp_or_none(membership.disabled_at),
            created_at=timestamp(membership.created_at),
            updated_at=timestamp(membership.updated_at),
        ),
    )


def plant_projection_summary(item: PlantProjection) -> AdminPlantProjection:
    plant = item.plant
    return AdminPlantProjection(
        plant_id=plant.plant_id,
        farm_id=plant.farm_id,
        plant_key=plant.plant_key,
        display_name=plant.display_name,
        status=plant.status,
        created_at=timestamp(plant.created_at),
        updated_at=timestamp(plant.updated_at),
        grant_counts=AdminPlantGrantCounts(**item.grant_counts),
    )


def audit_summary(item: dict[str, object]) -> AdminAuditSummary:
    return AdminAuditSummary(
        admin_audit_id=uuid.UUID(str(item["admin_audit_id"])),
        farm_id=uuid.UUID(str(item["farm_id"])),
        actor_kind=str(item["actor_kind"]),
        actor_account_id=uuid_or_none(item["actor_account_id"]),
        actor_membership_id=uuid_or_none(item["actor_membership_id"]),
        actor_role_preset=item["actor_role_preset"],
        action_type=str(item["action_type"]),
        target_type=str(item["target_type"]),
        target_id=uuid.UUID(str(item["target_id"])),
        plant_id=uuid_or_none(item["plant_id"]),
        request_id=str(item["request_id"]),
        before_summary=dict_value(item["before_summary"]),
        after_summary=dict_value(item["after_summary"]),
        source_refs=list_value(item["source_refs"]),
        created_at=timestamp(item["created_at"]),
    )


def decode_audit_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        offset = payload["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError
    except Exception:
        raise ProtectedRouteDenied(AuthErrorCode.ADMIN_AUDIT_CURSOR_INVALID) from None
    return offset


def encode_audit_cursor(offset: int) -> str:
    payload = {"offset": offset}
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def uuid_or_none(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(str(value))


def dict_value(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def timestamp(value: object) -> datetime:
    if not isinstance(value, datetime):
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def timestamp_or_none(value: object) -> datetime | None:
    return None if value is None else timestamp(value)


__all__ = [
    "account_summary_from_projection",
    "account_summary_from_result",
    "admin_error_code",
    "audit_summary",
    "decode_audit_cursor",
    "encode_audit_cursor",
    "plant_projection_summary",
]
