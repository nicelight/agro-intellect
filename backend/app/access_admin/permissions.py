from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol
import uuid


class RolePreset(StrEnum):
    BOSS = "boss"
    ENGINEER = "engineer"
    CONSULTANT = "consultant"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class PlantStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class GrantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class OperationKind(StrEnum):
    NORMAL_READ = "normal_read"
    OPERATE = "operate"
    RETAINED_HISTORY_READ = "retained_history_read"
    MANAGE_LIFECYCLE = "manage_lifecycle"
    MANAGE_ACCESS = "manage_access"
    APPROVE_ACTION = "approve_action"


class PermissionSource(StrEnum):
    BOSS_ROLE = "boss_role"
    PLANT_ACCESS_GRANT = "plant_access_grant"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class RolePolicy:
    requires_plant_grant: bool
    can_create_plants: bool
    can_manage_lifecycle: bool
    can_read: bool
    can_comment: bool
    can_operate: bool
    can_create_domain_tasks: bool
    can_manage_access: bool
    can_approve_actions: bool
    can_approve_governance: bool


ROLE_POLICIES = MappingProxyType(
    {
        RolePreset.BOSS: RolePolicy(
            requires_plant_grant=False,
            can_create_plants=True,
            can_manage_lifecycle=True,
            can_read=True,
            can_comment=True,
            can_operate=True,
            can_create_domain_tasks=True,
            can_manage_access=True,
            can_approve_actions=True,
            can_approve_governance=False,
        ),
        RolePreset.ENGINEER: RolePolicy(
            requires_plant_grant=True,
            can_create_plants=True,
            can_manage_lifecycle=False,
            can_read=True,
            can_comment=True,
            can_operate=True,
            can_create_domain_tasks=True,
            can_manage_access=False,
            can_approve_actions=False,
            can_approve_governance=False,
        ),
        RolePreset.CONSULTANT: RolePolicy(
            requires_plant_grant=True,
            can_create_plants=False,
            can_manage_lifecycle=False,
            can_read=True,
            can_comment=True,
            can_operate=False,
            can_create_domain_tasks=False,
            can_manage_access=False,
            can_approve_actions=False,
            can_approve_governance=False,
        ),
    }
)


@dataclass(frozen=True, slots=True)
class PlantSnapshot:
    plant_id: uuid.UUID
    farm_id: uuid.UUID
    status: PlantStatus | str


@dataclass(frozen=True, slots=True)
class PlantGrantSnapshot:
    grant_id: uuid.UUID
    membership_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    status: GrantStatus | str
    plant_approve_actions: bool = False


@dataclass(frozen=True, slots=True)
class PlantAccessSnapshot:
    plant: PlantSnapshot
    grant: PlantGrantSnapshot | None = None


class PlantAccessSnapshotProvider(Protocol):
    def __call__(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> PlantAccessSnapshot | None: ...


@dataclass(frozen=True, slots=True)
class PlantPermissionContext:
    plant_id: uuid.UUID
    plant_status: PlantStatus | None
    can_read: bool
    can_comment: bool
    can_operate: bool
    can_create_domain_tasks: bool
    can_manage_access: bool
    can_approve_actions: bool
    source: PermissionSource
    grant_id: uuid.UUID | None


class PlantPermissionResolver(Protocol):
    def resolve(
        self,
        plant_id: uuid.UUID,
        operation_kind: OperationKind | str,
    ) -> PlantPermissionContext: ...


@dataclass(frozen=True, slots=True, init=False)
class _BoundedPlantPermissionResolver:
    """Resolve the FT-001 permission seam from a future FT-002 snapshot adapter."""

    _farm_id: uuid.UUID
    _membership_id: uuid.UUID
    _membership_status: MembershipStatus | str
    _role_preset: RolePreset | str
    _snapshot_provider: PlantAccessSnapshotProvider = field(repr=False)

    def __init__(
        self,
        *,
        farm_id: uuid.UUID,
        membership_id: uuid.UUID,
        membership_status: MembershipStatus | str,
        role_preset: RolePreset | str,
        snapshot_provider: PlantAccessSnapshotProvider,
    ) -> None:
        object.__setattr__(self, "_farm_id", farm_id)
        object.__setattr__(self, "_membership_id", membership_id)
        object.__setattr__(self, "_membership_status", membership_status)
        object.__setattr__(self, "_role_preset", role_preset)
        object.__setattr__(self, "_snapshot_provider", snapshot_provider)

    def resolve(
        self,
        plant_id: uuid.UUID,
        operation_kind: OperationKind | str,
    ) -> PlantPermissionContext:
        operation = _coerce_enum(OperationKind, operation_kind)
        role = _coerce_enum(RolePreset, self._role_preset)
        membership_status = _coerce_enum(
            MembershipStatus,
            self._membership_status,
        )
        if (
            not isinstance(plant_id, uuid.UUID)
            or operation is None
            or role is None
            or membership_status is not MembershipStatus.ACTIVE
        ):
            return _denied(plant_id)

        try:
            snapshot = self._snapshot_provider(
                farm_id=self._farm_id,
                membership_id=self._membership_id,
                plant_id=plant_id,
            )
        except Exception:
            return _denied(plant_id)

        if not isinstance(snapshot, PlantAccessSnapshot) or not isinstance(
            snapshot.plant,
            PlantSnapshot,
        ):
            return _denied(plant_id)
        plant_status = _coerce_enum(PlantStatus, snapshot.plant.status)
        if (
            plant_status is None
            or snapshot.plant.plant_id != plant_id
            or snapshot.plant.farm_id != self._farm_id
        ):
            return _denied(plant_id)

        policy = ROLE_POLICIES[role]
        grant_id: uuid.UUID | None = None
        source = PermissionSource.BOSS_ROLE
        approve_override = False
        if policy.requires_plant_grant:
            grant = snapshot.grant
            if not _grant_matches(
                grant,
                farm_id=self._farm_id,
                membership_id=self._membership_id,
                plant_id=plant_id,
            ):
                return _denied(plant_id)
            assert grant is not None
            grant_id = grant.grant_id
            source = PermissionSource.PLANT_ACCESS_GRANT
            approve_override = grant.plant_approve_actions is True

        return _authorized_context(
            plant_id=plant_id,
            plant_status=plant_status,
            operation=operation,
            role=role,
            policy=policy,
            source=source,
            grant_id=grant_id,
            approve_override=approve_override,
        )


def role_policy_for(role_preset: RolePreset | str) -> RolePolicy | None:
    role = _coerce_enum(RolePreset, role_preset)
    return ROLE_POLICIES.get(role) if role is not None else None


def _grant_matches(
    grant: PlantGrantSnapshot | None,
    *,
    farm_id: uuid.UUID,
    membership_id: uuid.UUID,
    plant_id: uuid.UUID,
) -> bool:
    return (
        isinstance(grant, PlantGrantSnapshot)
        and isinstance(grant.grant_id, uuid.UUID)
        and grant.farm_id == farm_id
        and grant.membership_id == membership_id
        and grant.plant_id == plant_id
        and _coerce_enum(GrantStatus, grant.status) is GrantStatus.ACTIVE
    )


def _authorized_context(
    *,
    plant_id: uuid.UUID,
    plant_status: PlantStatus,
    operation: OperationKind,
    role: RolePreset,
    policy: RolePolicy,
    source: PermissionSource,
    grant_id: uuid.UUID | None,
    approve_override: bool,
) -> PlantPermissionContext:
    if plant_status is PlantStatus.ARCHIVED:
        retained_read = operation is OperationKind.RETAINED_HISTORY_READ
        manage_archived = role is RolePreset.BOSS and operation in {
            OperationKind.MANAGE_LIFECYCLE,
            OperationKind.MANAGE_ACCESS,
        }
        return PlantPermissionContext(
            plant_id=plant_id,
            plant_status=plant_status,
            can_read=retained_read and policy.can_read,
            can_comment=retained_read and policy.can_comment,
            can_operate=False,
            can_create_domain_tasks=False,
            can_manage_access=manage_archived,
            can_approve_actions=False,
            source=source,
            grant_id=grant_id,
        )

    can_approve_actions = policy.can_approve_actions
    if role is RolePreset.ENGINEER:
        can_approve_actions = approve_override
    if role is RolePreset.CONSULTANT:
        can_approve_actions = False
    return PlantPermissionContext(
        plant_id=plant_id,
        plant_status=plant_status,
        can_read=policy.can_read,
        can_comment=policy.can_comment,
        can_operate=policy.can_operate,
        can_create_domain_tasks=policy.can_create_domain_tasks,
        can_manage_access=policy.can_manage_access,
        can_approve_actions=can_approve_actions,
        source=source,
        grant_id=grant_id,
    )


def _denied(plant_id: object) -> PlantPermissionContext:
    safe_plant_id = plant_id if isinstance(plant_id, uuid.UUID) else uuid.UUID(int=0)
    return PlantPermissionContext(
        plant_id=safe_plant_id,
        plant_status=None,
        can_read=False,
        can_comment=False,
        can_operate=False,
        can_create_domain_tasks=False,
        can_manage_access=False,
        can_approve_actions=False,
        source=PermissionSource.DENIED,
        grant_id=None,
    )


def _coerce_enum(enum_type, value):
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "GrantStatus",
    "MembershipStatus",
    "OperationKind",
    "PermissionSource",
    "PlantAccessSnapshot",
    "PlantAccessSnapshotProvider",
    "PlantGrantSnapshot",
    "PlantPermissionContext",
    "PlantPermissionResolver",
    "PlantSnapshot",
    "PlantStatus",
    "ROLE_POLICIES",
    "RolePolicy",
    "RolePreset",
    "role_policy_for",
]
