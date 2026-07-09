from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .actor_context import ActorContext
from .farm_repository import FarmRepository
from .models import Farm, FarmMembership, Plant, PlantAccessGrant
from .permissions import RolePreset, role_policy_for


class FarmCommandErrorCode(StrEnum):
    FORBIDDEN = "forbidden"
    PLANT_UNAVAILABLE = "plant_unavailable"
    MEMBERSHIP_UNAVAILABLE = "membership_unavailable"
    INVALID_INPUT = "invalid_input"
    CONFLICT = "conflict"
    PERSISTENCE_FAILED = "persistence_failed"


class FarmCommandError(RuntimeError):
    """Safe service error; details never expose row existence or DB failures."""

    def __init__(self, code: FarmCommandErrorCode) -> None:
        self.code = code
        super().__init__(f"Farm command failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class PlantCreationResult:
    plant: Plant
    creator_grant: PlantAccessGrant | None


@dataclass(frozen=True, slots=True)
class MutationResult:
    entity: Farm | Plant | PlantAccessGrant
    changed: bool


RepositoryFactory = Callable[[Session], FarmRepository]
_PLANT_KEY_UNIQUE_CONSTRAINT = "uq_plants_farm_plant_key"


class FarmService:
    """Single-transaction policy boundary for FT-002 authority mutations."""

    def __init__(
        self,
        session: Session,
        *,
        repository_factory: RepositoryFactory = FarmRepository,
    ) -> None:
        self._session = session
        self._repository_factory = repository_factory

    def change_farm_display_name(
        self,
        actor: ActorContext,
        *,
        display_name: str,
    ) -> MutationResult:
        normalized = _display_name(display_name)

        def command(repository: FarmRepository) -> MutationResult:
            membership = _require_current_actor(repository, actor)
            _require_role(membership, RolePreset.BOSS)
            farm = repository.lock_farm(actor.farm_id)
            if farm is None:
                raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)
            if farm.display_name == normalized:
                return MutationResult(farm, False)
            before = farm.display_name
            farm.display_name = normalized
            farm.updated_at = _now()
            repository.add_account_audit(
                **_audit_actor(actor, membership),
                action_type="farm_display_name_changed",
                target_type="farm",
                target_id=farm.farm_id,
                plant_id=None,
                before_summary={"farm_id": str(farm.farm_id), "display_name": before},
                after_summary={
                    "farm_id": str(farm.farm_id),
                    "display_name": farm.display_name,
                },
            )
            repository.flush()
            return MutationResult(farm, True)

        return self._run(command)

    def create_plant(
        self,
        actor: ActorContext,
        *,
        plant_key: str,
        display_name: str,
    ) -> PlantCreationResult:
        normalized_name = _display_name(display_name)
        if not isinstance(plant_key, str):
            raise FarmCommandError(FarmCommandErrorCode.INVALID_INPUT)

        def command(repository: FarmRepository) -> PlantCreationResult:
            membership = _require_current_actor(repository, actor)
            policy = role_policy_for(membership.role_preset)
            if policy is None or not policy.can_create_plants:
                raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)
            farm = repository.lock_farm(actor.farm_id)
            if farm is None:
                raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)
            if repository.lock_plant_by_key(
                farm_id=actor.farm_id, plant_key=plant_key
            ) is not None:
                raise FarmCommandError(FarmCommandErrorCode.CONFLICT)
            try:
                plant = Plant(
                    farm_id=actor.farm_id,
                    plant_key=plant_key,
                    display_name=normalized_name,
                    status="active",
                )
            except (TypeError, ValueError):
                raise FarmCommandError(FarmCommandErrorCode.INVALID_INPUT) from None
            repository.add_plant(plant)
            repository.flush()
            repository.add_account_audit(
                **_audit_actor(actor, membership),
                action_type="plant_created",
                target_type="plant",
                target_id=plant.plant_id,
                plant_id=plant.plant_id,
                before_summary={},
                after_summary=_plant_summary(plant),
            )
            creator_grant = None
            if membership.role_preset == RolePreset.ENGINEER.value:
                creator_grant = PlantAccessGrant(
                    membership_id=membership.membership_id,
                    plant_id=plant.plant_id,
                    status="active",
                    plant_approve_actions=False,
                )
                repository.add_grant(creator_grant)
                repository.flush()
                repository.add_account_audit(
                    **_audit_actor(actor, membership),
                    action_type="plant_access_granted",
                    target_type="plant_access_grant",
                    target_id=creator_grant.grant_id,
                    plant_id=plant.plant_id,
                    before_summary={},
                    after_summary=_grant_summary(creator_grant, actor.farm_id),
                )
            repository.flush()
            return PlantCreationResult(plant, creator_grant)

        return self._run(command)

    def rename_plant(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        display_name: str,
    ) -> MutationResult:
        normalized = _display_name(display_name)

        def command(repository: FarmRepository) -> MutationResult:
            membership = _require_current_actor(repository, actor)
            plant = repository.lock_plant(farm_id=actor.farm_id, plant_id=plant_id)
            if plant is None or plant.status != "active":
                raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            if membership.role_preset == RolePreset.ENGINEER.value:
                grant = repository.lock_grant(
                    membership_id=membership.membership_id, plant_id=plant_id
                )
                if grant is None or grant.status != "active":
                    raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            elif membership.role_preset != RolePreset.BOSS.value:
                raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            if plant.display_name == normalized:
                return MutationResult(plant, False)
            before = plant.display_name
            plant.display_name = normalized
            plant.updated_at = _now()
            repository.add_account_audit(
                **_audit_actor(actor, membership),
                action_type="plant_display_name_changed",
                target_type="plant",
                target_id=plant.plant_id,
                plant_id=plant.plant_id,
                before_summary={"plant_id": str(plant.plant_id), "display_name": before},
                after_summary={
                    "plant_id": str(plant.plant_id),
                    "display_name": plant.display_name,
                },
            )
            repository.flush()
            return MutationResult(plant, True)

        return self._run(command)

    def archive_plant(
        self, actor: ActorContext, *, plant_id: uuid.UUID
    ) -> MutationResult:
        return self._set_plant_status(actor, plant_id=plant_id, target="archived")

    def restore_plant(
        self, actor: ActorContext, *, plant_id: uuid.UUID
    ) -> MutationResult:
        return self._set_plant_status(actor, plant_id=plant_id, target="active")

    def _set_plant_status(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        target: str,
    ) -> MutationResult:
        def command(repository: FarmRepository) -> MutationResult:
            membership = _require_current_actor(repository, actor)
            _require_role(membership, RolePreset.BOSS)
            plant = repository.lock_plant(farm_id=actor.farm_id, plant_id=plant_id)
            if plant is None:
                raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            if plant.status == target:
                return MutationResult(plant, False)
            before = plant.status
            plant.status = target
            plant.updated_at = _now()
            action_type = "plant_archived" if target == "archived" else "plant_restored"
            repository.add_account_audit(
                **_audit_actor(actor, membership),
                action_type=action_type,
                target_type="plant",
                target_id=plant.plant_id,
                plant_id=plant.plant_id,
                before_summary={"plant_id": str(plant.plant_id), "status": before},
                after_summary={"plant_id": str(plant.plant_id), "status": target},
            )
            repository.flush()
            return MutationResult(plant, True)

        return self._run(command)

    def grant_access(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_approve_actions: bool = False,
    ) -> MutationResult:
        if type(plant_approve_actions) is not bool:
            raise FarmCommandError(FarmCommandErrorCode.INVALID_INPUT)

        def command(repository: FarmRepository) -> MutationResult:
            actor_membership = _require_current_actor(repository, actor)
            _require_role(actor_membership, RolePreset.BOSS)
            plant = repository.lock_plant(farm_id=actor.farm_id, plant_id=plant_id)
            if plant is None:
                raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            target_identity = repository.lock_membership_identity(
                farm_id=actor.farm_id, membership_id=membership_id
            )
            target_account, target = (
                target_identity if target_identity is not None else (None, None)
            )
            if (
                target is None
                or target_account is None
                or target_account.account_status != "active"
                or target.membership_status != "active"
                or target.role_preset not in {
                    RolePreset.ENGINEER.value,
                    RolePreset.CONSULTANT.value,
                }
            ):
                raise FarmCommandError(FarmCommandErrorCode.MEMBERSHIP_UNAVAILABLE)
            if target.role_preset == RolePreset.CONSULTANT.value and plant_approve_actions:
                raise FarmCommandError(FarmCommandErrorCode.INVALID_INPUT)
            grant = repository.lock_grant(
                membership_id=membership_id, plant_id=plant_id
            )
            if grant is None:
                grant = PlantAccessGrant(
                    membership_id=membership_id,
                    plant_id=plant_id,
                    status="active",
                    plant_approve_actions=plant_approve_actions,
                )
                repository.add_grant(grant)
                repository.flush()
                before_summary: dict[str, object] = {}
                action_type = "plant_access_granted"
            elif grant.status == "revoked":
                before_summary = _grant_summary(grant, actor.farm_id)
                grant.status = "active"
                grant.plant_approve_actions = plant_approve_actions
                grant.updated_at = _now()
                action_type = "plant_access_granted"
            elif grant.plant_approve_actions != plant_approve_actions:
                before_summary = _grant_summary(grant, actor.farm_id)
                grant.plant_approve_actions = plant_approve_actions
                grant.updated_at = _now()
                action_type = "plant_approve_actions_changed"
            else:
                return MutationResult(grant, False)
            repository.add_account_audit(
                **_audit_actor(actor, actor_membership),
                action_type=action_type,
                target_type="plant_access_grant",
                target_id=grant.grant_id,
                plant_id=plant.plant_id,
                before_summary=before_summary,
                after_summary=_grant_summary(grant, actor.farm_id),
            )
            repository.flush()
            return MutationResult(grant, True)

        return self._run(command)

    def revoke_access(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        membership_id: uuid.UUID,
    ) -> MutationResult:
        def command(repository: FarmRepository) -> MutationResult:
            actor_membership = _require_current_actor(repository, actor)
            _require_role(actor_membership, RolePreset.BOSS)
            plant = repository.lock_plant(farm_id=actor.farm_id, plant_id=plant_id)
            target = repository.lock_membership(
                farm_id=actor.farm_id, membership_id=membership_id
            )
            grant = repository.lock_grant(
                membership_id=membership_id, plant_id=plant_id
            )
            if plant is None or target is None or grant is None:
                raise FarmCommandError(FarmCommandErrorCode.PLANT_UNAVAILABLE)
            if grant.status == "revoked":
                return MutationResult(grant, False)
            before = _grant_summary(grant, actor.farm_id)
            grant.status = "revoked"
            grant.updated_at = _now()
            repository.add_account_audit(
                **_audit_actor(actor, actor_membership),
                action_type="plant_access_revoked",
                target_type="plant_access_grant",
                target_id=grant.grant_id,
                plant_id=plant.plant_id,
                before_summary=before,
                after_summary=_grant_summary(grant, actor.farm_id),
            )
            repository.flush()
            return MutationResult(grant, True)

        return self._run(command)

    def _run(self, command):
        try:
            with self._session.begin():
                return command(self._repository_factory(self._session))
        except FarmCommandError:
            raise
        except IntegrityError as error:
            code = (
                FarmCommandErrorCode.CONFLICT
                if _is_plant_key_unique_violation(error)
                else FarmCommandErrorCode.PERSISTENCE_FAILED
            )
            raise FarmCommandError(code) from None
        except Exception:
            raise FarmCommandError(FarmCommandErrorCode.PERSISTENCE_FAILED) from None


def _require_current_actor(
    repository: FarmRepository, actor: ActorContext
) -> FarmMembership:
    try:
        identity = repository.lock_actor_identity(
            account_id=actor.account_id,
            membership_id=actor.membership_id,
            farm_id=actor.farm_id,
        )
    except (AttributeError, TypeError):
        raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN) from None
    if identity is None:
        raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)
    account, membership = identity
    if (
        account.account_status != "active"
        or membership.membership_status != "active"
        or membership.role_preset != actor.role_preset.value
        or membership.account_id != actor.account_id
    ):
        raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)
    return membership


def _require_role(membership: FarmMembership, role: RolePreset) -> None:
    if membership.role_preset != role.value:
        raise FarmCommandError(FarmCommandErrorCode.FORBIDDEN)


def _display_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FarmCommandError(FarmCommandErrorCode.INVALID_INPUT)
    return value.strip()


def _audit_actor(actor: ActorContext, membership: FarmMembership) -> dict[str, object]:
    return {
        "account_id": actor.account_id,
        "membership_id": membership.membership_id,
        "role_preset": membership.role_preset,
        "farm_id": actor.farm_id,
        "request_id": actor.request_id,
    }


def _plant_summary(plant: Plant) -> dict[str, object]:
    return {
        "plant_id": str(plant.plant_id),
        "farm_id": str(plant.farm_id),
        "plant_key": plant.plant_key,
        "display_name": plant.display_name,
        "status": plant.status,
    }


def _grant_summary(
    grant: PlantAccessGrant, farm_id: uuid.UUID
) -> dict[str, object]:
    return {
        "grant_id": str(grant.grant_id),
        "farm_id": str(farm_id),
        "plant_id": str(grant.plant_id),
        "membership_id": str(grant.membership_id),
        "status": grant.status,
        "plant_approve_actions": grant.plant_approve_actions,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_plant_key_unique_violation(error: IntegrityError) -> bool:
    original = getattr(error, "orig", None)
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None)
        == _PLANT_KEY_UNIQUE_CONSTRAINT
    )


__all__ = [
    "FarmCommandError",
    "FarmCommandErrorCode",
    "FarmService",
    "MutationResult",
    "PlantCreationResult",
]
