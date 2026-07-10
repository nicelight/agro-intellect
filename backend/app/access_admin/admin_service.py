from __future__ import annotations

from collections.abc import Callable
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .actor_context import ActorContext
from .admin_repository import AdminRepository
from .admin_rules import (
    display_name as normalize_display_name,
    is_account_login_unique_violation,
    limit as normalize_limit,
    normalize_login,
    offset as normalize_offset,
    optional_account_status,
    optional_reason,
    optional_role,
    optional_target_type,
    password_hash,
    request_id as normalize_request_id,
    require_boss_actor,
    require_canonical_actor_farm,
    require_canonical_farm,
    role as normalize_role,
)
from .admin_summaries import (
    account_membership_summary,
    account_summary,
    audit_actor,
    audit_summary,
    membership_summary,
    now,
)
from .admin_types import (
    FIRST_BOSS_REQUEST_ID,
    AccountMembershipProjection,
    AccountMembershipResult,
    AdminCommandError,
    AdminCommandErrorCode,
    PlantProjection,
)
from .models import Account, FarmMembership
from .permissions import RolePreset


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
        normalized_login = normalize_login(login_name)
        normalized_display_name = normalize_display_name(display_name)
        hashed_password = password_hash(password)
        normalized_request_id = normalize_request_id(request_id)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            farm = require_canonical_farm(repository)
            if repository.active_boss_count(farm_id=farm.farm_id) > 0:
                raise AdminCommandError(AdminCommandErrorCode.LAST_BOSS_CONFLICT)
            if repository.find_account_by_login(normalized_login) is not None:
                raise AdminCommandError(AdminCommandErrorCode.ACCOUNT_CONFLICT)
            account = Account(
                login_name=normalized_login,
                display_name=normalized_display_name,
                account_status="active",
                password_hash=hashed_password,
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
                after_summary=account_membership_summary(
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
        normalized_login = normalize_login(login_name)
        normalized_display_name = normalize_display_name(display_name)
        hashed_password = password_hash(password)
        normalized_role = normalize_role(role_preset)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = require_boss_actor(repository, actor)
            require_canonical_actor_farm(repository, actor.farm_id)
            if repository.find_account_by_login(normalized_login) is not None:
                raise AdminCommandError(AdminCommandErrorCode.ACCOUNT_CONFLICT)
            account = Account(
                login_name=normalized_login,
                display_name=normalized_display_name,
                account_status="active",
                password_hash=hashed_password,
            )
            repository.add_account(account)
            repository.flush()
            membership = FarmMembership(
                account_id=account.account_id,
                farm_id=actor.farm_id,
                role_preset=normalized_role,
                membership_status="active",
            )
            repository.add_membership(membership)
            repository.flush()
            repository.add_account_audit(
                **audit_actor(actor, actor_membership),
                action_type="account_created",
                target_type="account",
                target_id=account.account_id,
                plant_id=None,
                before_summary={},
                after_summary=account_membership_summary(account, membership),
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
        safe_reason = optional_reason(reason)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = require_boss_actor(repository, actor)
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
            before = account_summary(account)
            account.account_status = "disabled"
            account.disabled_at = now()
            account.updated_at = account.disabled_at
            after = account_summary(account)
            if safe_reason is not None:
                after["reason"] = safe_reason
            repository.add_account_audit(
                **audit_actor(actor, actor_membership),
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
        normalized_role = normalize_role(role_preset)

        def command(repository: AdminRepository) -> AccountMembershipResult:
            actor_membership = require_boss_actor(repository, actor)
            target_identity = repository.lock_membership_identity(
                farm_id=actor.farm_id, membership_id=membership_id
            )
            if target_identity is None:
                raise AdminCommandError(AdminCommandErrorCode.MEMBERSHIP_NOT_FOUND)
            account, membership = target_identity
            if membership.role_preset == normalized_role:
                return AccountMembershipResult(
                    account=account, membership=membership, changed=False
                )
            if (
                membership.role_preset == RolePreset.BOSS.value
                and membership.membership_status == "active"
                and account.account_status == "active"
                and normalized_role != RolePreset.BOSS.value
                and repository.active_boss_count(farm_id=actor.farm_id) <= 1
            ):
                raise AdminCommandError(AdminCommandErrorCode.LAST_BOSS_CONFLICT)
            before = membership_summary(membership)
            membership.role_preset = normalized_role
            membership.updated_at = now()
            repository.add_account_audit(
                **audit_actor(actor, actor_membership),
                action_type="membership_role_changed",
                target_type="membership",
                target_id=membership.membership_id,
                plant_id=None,
                before_summary=before,
                after_summary=membership_summary(membership),
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
    ) -> list[AccountMembershipProjection]:
        status = optional_account_status(account_status)
        normalized_role = optional_role(role_preset)

        def command(repository: AdminRepository) -> list[AccountMembershipProjection]:
            require_boss_actor(repository, actor)
            return [
                AccountMembershipProjection(account=account, membership=membership)
                for account, membership in repository.list_personnel(
                    farm_id=actor.farm_id,
                    account_status=status,
                    role_preset=normalized_role,
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
            require_boss_actor(repository, actor)
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
        offset: object = 0,
        target_type: object | None = None,
        target_id: uuid.UUID | None = None,
        plant_id: uuid.UUID | None = None,
    ) -> list[dict[str, object]]:
        normalized_limit = normalize_limit(limit)
        normalized_offset = normalize_offset(offset)
        normalized_target_type = optional_target_type(target_type)

        def command(repository: AdminRepository) -> list[dict[str, object]]:
            require_boss_actor(repository, actor)
            return [
                audit_summary(record)
                for record in repository.list_audit_records(
                    farm_id=actor.farm_id,
                    limit=normalized_limit,
                    offset=normalized_offset,
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
                if is_account_login_unique_violation(error)
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

__all__ = [
    "FIRST_BOSS_REQUEST_ID",
    "AccountMembershipProjection",
    "AccountMembershipResult",
    "AdminCommandError",
    "AdminCommandErrorCode",
    "AdminService",
    "PlantProjection",
]
