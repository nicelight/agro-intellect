from __future__ import annotations

from datetime import datetime, timezone

from .actor_context import ActorContext
from .admin_types import FIRST_BOSS_REQUEST_ID
from .models import Account, AdminAuditRecord, FarmMembership


def audit_actor(actor: ActorContext, membership: FarmMembership) -> dict[str, object]:
    return {
        "account_id": actor.account_id,
        "membership_id": membership.membership_id,
        "role_preset": membership.role_preset,
        "farm_id": actor.farm_id,
        "request_id": actor.request_id,
    }


def account_summary(account: Account) -> dict[str, object]:
    return {
        "account_id": str(account.account_id),
        "login_name": account.login_name,
        "display_name": account.display_name,
        "account_status": account.account_status,
    }


def membership_summary(membership: FarmMembership) -> dict[str, object]:
    return {
        "membership_id": str(membership.membership_id),
        "account_id": str(membership.account_id),
        "farm_id": str(membership.farm_id),
        "role_preset": membership.role_preset,
        "membership_status": membership.membership_status,
    }


def account_membership_summary(
    account: Account,
    membership: FarmMembership,
    *,
    bootstrap: bool = False,
) -> dict[str, object]:
    summary: dict[str, object] = account_summary(account)
    summary["membership"] = membership_summary(membership)
    if bootstrap:
        summary["bootstrap"] = FIRST_BOSS_REQUEST_ID
    return summary


def audit_summary(record: AdminAuditRecord) -> dict[str, object]:
    return {
        "admin_audit_id": str(record.admin_audit_id),
        "farm_id": str(record.farm_id),
        "actor_kind": record.actor_kind,
        "actor_account_id": (
            str(record.actor_account_id) if record.actor_account_id else None
        ),
        "actor_membership_id": (
            str(record.actor_membership_id) if record.actor_membership_id else None
        ),
        "actor_role_preset": record.actor_role_preset,
        "action_type": record.action_type,
        "target_type": record.target_type,
        "target_id": str(record.target_id),
        "plant_id": str(record.plant_id) if record.plant_id else None,
        "request_id": record.request_id,
        "before_summary": record.before_summary,
        "after_summary": record.after_summary,
        "source_refs": record.source_refs,
        "created_at": record.created_at,
    }


def now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "account_membership_summary",
    "account_summary",
    "audit_actor",
    "audit_summary",
    "membership_summary",
    "now",
]
