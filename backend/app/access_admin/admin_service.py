from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .actor_context import ActorContext
from .admin_repository import AdminRepository
from .farm_bootstrap import CANONICAL_FARM_KEY
from .models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    Plant,
    PlantAccessGrant,
    normalize_login_name,
)
from .permissions import RolePreset
from .security import hash_password


FIRST_BOSS_REQUEST_ID = "bootstrap-first-boss-local"
_ACCOUNT_LOGIN_UNIQUE_CONSTRAINT = "uq_accounts_login_name"
_ROLE_PRESETS = {role.value for role in RolePreset}
_ACCOUNT_STATUSES = {"active", "disabled"}
_AUDIT_TARGETS = {"account", "membership", "farm", "plant", "plant_access_grant"}


class AdminCommandErrorCode(StrEnum):
    FORBIDDEN = "forbidden"
    FARM_NOT_INITIALIZED = "farm_not_initialized"
    FARM_STATE_CONFLICT = "farm_state_conflict"
    ACCOUNT_NOT_FOUND = "account_not_found"
    MEMBERSHIP_NOT_FOUND = "membership_not_found"
    ACCOUNT_CONFLICT = "account_conflict"
    LAST_BOSS_CONFLICT = "last_boss_conflict"
    INVALID_INPUT = "invalid_input"
    PERSISTENCE_FAILED = "persistence_failed"


class AdminCommandError(RuntimeError):
    """Safe admin-service error; message contains no DB or credential detail."""

    def __init__(self, code: AdminCommandErrorCode) -> None:
        self.code = code
        super().__init__(f"Admin command failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class AccountMembershipResult:
    account: Account
    membership: FarmMembership
    changed: bool = True


@dataclass(frozen=True, slots=True)
class PlantProjection:
    plant: Plant
    grant_counts: dict[str, int]


RepositoryFactory = Callable[[Session], AdminRepository]


class AdminService:
    """Single-transaction policy boundary for FT-003 admin identity changes."""

    def __init__(
        self,
        session: Session,
        *,
        repository_factory: RepositoryFactory = AdminRepository,
    ) -> None:
        self._session = session
        self._repository_factory = repository_factory

    def bootstrap_first_boss(
        self,
        *,
        login_name: object,
        display_name: object,
        password: object,
        request_id: str = FIRST_BOSS_REQUEST_ID,
    ) -> AccountMembershipResult:
        normalized_login = _login(login_name)
        normalized_display_name = _display_name(display_name)
        password_hash = _password_hash(password)
        normalized_request_id = _request_id(request_id)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            farm = _require_canonical_farm(repository)
            if repository.active_boss_count(farm_id=farm.farm_id) > 0:
                raise AdminCommandError(AdminCommandErrorCode.LAST_BOSS_CONFLICT)
            if repository.find_account_by_login(normalized_login) is not None:
                raise AdminCommandError(AdminCommandErrorCode.ACCOUNT_CONFLICT)
            account = Account(
                login_name=normalized_login,
                display_name=normalized_display_name,
                account_status="active",
                password_hash=password_hash,
            )
            repository.add_account(account)
            repository.flush()
            membership = FarmMembership(
                account_id=account.account_id,
                farm_id=farm.farm_id,
                role_preset=RolePreset.BOSS.value,
                membership_status="active",
            )
            repository.add_membership(membership)
            repository.flush()
            repository.add_system_audit(
                farm_id=farm.farm_id,
                action_type="account_created",
                target_type="account",
                target_id=account.account_id,
                plant_id=None,
                request_id=normalized_request_id,
                before_summary={},
                after_summary=_account_membership_summary(
                    account, membership, bootstrap=True
                ),
            )
            repository.flush()
            return AccountMembershipResult(account=account, membership=membership)

        return self._run(command)

    def create_account(
        self,
        actor: ActorContext,
        *,
        login_name: object,
        display_name: object,
        password: object,
        role_preset: object,
    ) -> AccountMembershipResult:
        normalized_login = _login(login_name)
        normalized_display_name = _display_name(display_name)
        password_hash = _password_hash(password)
        role = _role(role_preset)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = _require_boss_actor(repository, actor)
            _require_canonical_actor_farm(repository, actor.farm_id)
            if repository.find_account_by_login(normalized_login) is not None:
                raise AdminCommandError(AdminCommandErrorCode.ACCOUNT_CONFLICT)
            account = Account(
                login_name=normalized_login,
                display_name=normalized_display_name,
                account_status="active",
                password_hash=password_hash,
            )
            repository.add_account(account)
            repository.flush()
            membership = FarmMembership(
                account_id=account.account_id,
                farm_id=actor.farm_id,
                role_preset=role,
                membership_status="active",
            )
            repository.add_membership(membership)
            repository.flush()
            repository.add_account_audit(
                **_audit_actor(actor, actor_membership),
                action_type="account_created",
                target_type="account",
                target_id=account.account_id,
                plant_id=None,
                before_summary={},
                after_summary=_account_membership_summary(account, membership),
            )
            repository.flush()
            return AccountMembershipResult(account=account, membership=membership)

        return self._run(command)

    def disable_account(
        self,
        actor: ActorContext,
        *,
        account_id: uuid.UUID,
        reason: object | None = None,
    ) -> AccountMembershipResult:
        safe_reason = _optional_reason(reason)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = _require_boss_actor(repository, actor)
            target_identity = repository.lock_account_identity(
                farm_id=actor.farm_id, account_id=account_id
            )
            if target_identity is None:
                raise AdminCommandError(AdminCommandErrorCode.ACCOUNT_NOT_FOUND)
            account, membership = target_identity
            if account.account_status == "disabled":
                return AccountMembershipResult(
                    account=account, membership=membership, changed=False
                )
            if (
                membership.role_preset == RolePreset.BOSS.value
                and membership.membership_status == "active"
                and repository.active_boss_count(farm_id=actor.farm_id) <= 1
            ):
                raise AdminCommandError(AdminCommandErrorCode.LAST_BOSS_CONFLICT)
            before = _account_summary(account)
            account.account_status = "disabled"
            account.disabled_at = _now()
            account.updated_at = account.disabled_at
            after = _account_summary(account)
            if safe_reason is not None:
                after["reason"] = safe_reason
            repository.add_account_audit(
                **_audit_actor(actor, actor_membership),
                action_type="account_disabled",
                target_type="account",
                target_id=account.account_id,
                plant_id=None,
                before_summary=before,
                after_summary=after,
            )
            repository.flush()
            return AccountMembershipResult(account=account, membership=membership)

        return self._run(command)

    def change_membership_role(
        self,
        actor: ActorContext,
        *,
        membership_id: uuid.UUID,
        role_preset: object,
    ) -> AccountMembershipResult:
        role = _role(role_preset)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = _require_boss_actor(repository, actor)
            target_identity = repository.lock_membership_identity(
                farm_id=actor.farm_id, membership_id=membership_id
            )
            if target_identity is None:
                raise AdminCommandError(AdminCommandErrorCode.MEMBERSHIP_NOT_FOUND)
            account, membership = target_identity
            if membership.role_preset == role:
                return AccountMembershipResult(
                    account=account, membership=membership, changed=False
                )
            if (
                membership.role_preset == RolePreset.BOSS.value
                and membership.membership_status == "active"
                and account.account_status == "active"
                and role != RolePreset.BOSS.value
                and repository.active_boss_count(farm_id=actor.farm_id) <= 1
            ):
                raise AdminCommandError(AdminCommandErrorCode.LAST_BOSS_CONFLICT)
            before = _membership_summary(membership)
            membership.role_preset = role
            membership.updated_at = _now()
            repository.add_account_audit(
                **_audit_actor(actor, actor_membership),
                action_type="membership_role_changed",
                target_type="membership",
                target_id=membership.membership_id,
                plant_id=None,
                before_summary=before,
                after_summary=_membership_summary(membership),
            )
            repository.flush()
            return AccountMembershipResult(account=account, membership=membership)

        return self._run(command)

    def list_personnel(
        self,
        actor: ActorContext,
        *,
        account_status: object | None = None,
        role_preset: object | None = None,
    ) -> list[dict[str, object]]:
        status = _optional_account_status(account_status)
        role = _optional_role(role_preset)

        def command(repository: AdminRepository) -> list[dict[str, object]]:
            _require_boss_actor(repository, actor)
            return [
                _account_membership_summary(account, membership)
                for account, membership in repository.list_personnel(
                    farm_id=actor.farm_id,
                    account_status=status,
                    role_preset=role,
                )
            ]

        return self._run_read(command)

    def list_plant_projections(
        self,
        actor: ActorContext,
        *,
        include_archived: bool = False,
    ) -> list[PlantProjection]:
        if type(include_archived) is not bool:
            raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)

        def command(repository: AdminRepository) -> list[PlantProjection]:
            _require_boss_actor(repository, actor)
            plants = repository.list_plants(
                farm_id=actor.farm_id, include_archived=include_archived
            )
            grants = repository.list_grants_for_plants(
                plant_ids=[plant.plant_id for plant in plants]
            )
            by_plant: dict[uuid.UUID, dict[str, int]] = {
                plant.plant_id: {
                    "active": 0,
                    "revoked": 0,
                    "approve_actions_enabled": 0,
                }
                for plant in plants
            }
            for grant in grants:
                counts = by_plant.get(grant.plant_id)
                if counts is None:
                    continue
                if grant.status in {"active", "revoked"}:
                    counts[grant.status] += 1
                if grant.status == "active" and grant.plant_approve_actions:
                    counts["approve_actions_enabled"] += 1
            return [
                PlantProjection(plant=plant, grant_counts=by_plant[plant.plant_id])
                for plant in plants
            ]

        return self._run_read(command)

    def list_audit(
        self,
        actor: ActorContext,
        *,
        limit: object = 50,
        target_type: object | None = None,
        target_id: uuid.UUID | None = None,
        plant_id: uuid.UUID | None = None,
    ) -> list[dict[str, object]]:
        normalized_limit = _limit(limit)
        normalized_target_type = _optional_target_type(target_type)

        def command(repository: AdminRepository) -> list[dict[str, object]]:
            _require_boss_actor(repository, actor)
            return [
                _audit_summary(record)
                for record in repository.list_audit_records(
                    farm_id=actor.farm_id,
                    limit=normalized_limit,
                    target_type=normalized_target_type,
                    target_id=target_id,
                    plant_id=plant_id,
                )
            ]

        return self._run_read(command)

    def _run(self, command):
        try:
            with self._session.begin():
                return command(self._repository_factory(self._session))
        except AdminCommandError:
            raise
        except IntegrityError as error:
            code = (
                AdminCommandErrorCode.ACCOUNT_CONFLICT
                if _is_account_login_unique_violation(error)
                else AdminCommandErrorCode.PERSISTENCE_FAILED
            )
            raise AdminCommandError(code) from None
        except Exception:
            raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED) from None

    def _run_read(self, command):
        try:
            return command(self._repository_factory(self._session))
        except AdminCommandError:
            raise
        except Exception:
            raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED) from None


def _require_canonical_farm(repository: AdminRepository) -> Farm:
    farms = repository.lock_farms()
    if not farms:
        raise AdminCommandError(AdminCommandErrorCode.FARM_NOT_INITIALIZED)
    if len(farms) != 1 or farms[0].farm_key != CANONICAL_FARM_KEY:
        raise AdminCommandError(AdminCommandErrorCode.FARM_STATE_CONFLICT)
    return farms[0]


def _require_canonical_actor_farm(
    repository: AdminRepository, farm_id: uuid.UUID
) -> Farm:
    farm = _require_canonical_farm(repository)
    if farm.farm_id != farm_id:
        raise AdminCommandError(AdminCommandErrorCode.FORBIDDEN)
    return farm


def _require_boss_actor(
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


def _login(value: object) -> str:
    if not isinstance(value, str):
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    normalized = normalize_login_name(value)
    if not normalized:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return normalized


def _display_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value.strip()


def _password_hash(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    try:
        return hash_password(value)
    except Exception:
        raise AdminCommandError(AdminCommandErrorCode.PERSISTENCE_FAILED) from None


def _role(value: object) -> str:
    if not isinstance(value, str) or value not in _ROLE_PRESETS:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def _optional_role(value: object | None) -> str | None:
    if value is None:
        return None
    return _role(value)


def _optional_account_status(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in _ACCOUNT_STATUSES:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def _optional_target_type(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value not in _AUDIT_TARGETS:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def _optional_reason(value: object | None) -> str | None:
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


def _request_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value.strip()


def _limit(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 100:
        raise AdminCommandError(AdminCommandErrorCode.INVALID_INPUT)
    return value


def _audit_actor(actor: ActorContext, membership: FarmMembership) -> dict[str, object]:
    return {
        "account_id": actor.account_id,
        "membership_id": membership.membership_id,
        "role_preset": membership.role_preset,
        "farm_id": actor.farm_id,
        "request_id": actor.request_id,
    }


def _account_summary(account: Account) -> dict[str, object]:
    return {
        "account_id": str(account.account_id),
        "login_name": account.login_name,
        "display_name": account.display_name,
        "account_status": account.account_status,
    }


def _membership_summary(membership: FarmMembership) -> dict[str, object]:
    return {
        "membership_id": str(membership.membership_id),
        "account_id": str(membership.account_id),
        "farm_id": str(membership.farm_id),
        "role_preset": membership.role_preset,
        "membership_status": membership.membership_status,
    }


def _account_membership_summary(
    account: Account,
    membership: FarmMembership,
    *,
    bootstrap: bool = False,
) -> dict[str, object]:
    summary: dict[str, object] = _account_summary(account)
    summary["membership"] = _membership_summary(membership)
    if bootstrap:
        summary["bootstrap"] = FIRST_BOSS_REQUEST_ID
    return summary


def _audit_summary(record: AdminAuditRecord) -> dict[str, object]:
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_account_login_unique_violation(error: IntegrityError) -> bool:
    original = getattr(error, "orig", None)
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None)
        == _ACCOUNT_LOGIN_UNIQUE_CONSTRAINT
    )


__all__ = [
    "FIRST_BOSS_REQUEST_ID",
    "AccountMembershipResult",
    "AdminCommandError",
    "AdminCommandErrorCode",
    "AdminService",
    "PlantProjection",
]
