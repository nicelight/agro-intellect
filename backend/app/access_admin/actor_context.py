from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
import uuid

from .permissions import (
    MembershipStatus,
    OperationKind,
    PlantAccessSnapshotProvider,
    PlantPermissionContext,
    PlantPermissionResolver,
    RolePreset,
    _BoundedPlantPermissionResolver,
    role_policy_for,
)
from .models import Account, FarmMembership, LocalSession
from .session_service import ValidatedSession


class AuthTransport(StrEnum):
    COOKIE = "cookie"
    BEARER = "bearer"


class ActorContextDenied(Exception):
    """Generic fail-closed ActorContext resolution failure."""

    def __init__(self) -> None:
        super().__init__("Actor context unavailable.")


class SessionValidator(Protocol):
    """Return only current, unrevoked sessions for active identities.

    Session expiry and lifecycle policy remain owned by TASK-007's
    ``SessionService``. ActorContext resolution trusts this postcondition and
    validates identity consistency before constructing the authorization
    envelope.
    """

    def validate_session(self, raw_token: object) -> ValidatedSession | None: ...


@dataclass(frozen=True, slots=True)
class AuthProvenance:
    auth_method: str
    session_created_at: datetime
    session_expires_at: datetime
    transport: AuthTransport


@dataclass(frozen=True, slots=True, init=False)
class ActorContext:
    request_id: str
    session_id: uuid.UUID
    account_id: uuid.UUID
    farm_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: RolePreset
    membership_status: MembershipStatus
    auth_provenance: AuthProvenance
    plant_permission_resolver: PlantPermissionResolver

    @classmethod
    def _from_validated(
        cls,
        *,
        request_id: str,
        validated_session: ValidatedSession,
        role_preset: RolePreset,
        membership_status: MembershipStatus,
        transport: AuthTransport,
        plant_permission_resolver: PlantPermissionResolver,
    ) -> ActorContext:
        instance = object.__new__(cls)
        values = {
            "request_id": request_id,
            "session_id": validated_session.session.session_id,
            "account_id": validated_session.account.account_id,
            "farm_id": validated_session.membership.farm_id,
            "membership_id": validated_session.membership.membership_id,
            "role_preset": role_preset,
            "membership_status": membership_status,
            "auth_provenance": AuthProvenance(
                auth_method=validated_session.session.auth_method,
                session_created_at=validated_session.session.created_at,
                session_expires_at=validated_session.session.expires_at,
                transport=transport,
            ),
            "plant_permission_resolver": plant_permission_resolver,
        }
        for name, value in values.items():
            object.__setattr__(instance, name, value)
        return instance

    def resolve_plant_permission(
        self,
        plant_id: uuid.UUID,
        operation_kind: OperationKind | str,
    ) -> PlantPermissionContext:
        return self.plant_permission_resolver.resolve(plant_id, operation_kind)


class ActorContextResolver:
    """Resolve a protected-request ActorContext through TASK-007 validation."""

    def __init__(
        self,
        *,
        session_validator: SessionValidator,
        snapshot_provider: PlantAccessSnapshotProvider,
    ) -> None:
        self._session_validator = session_validator
        self._snapshot_provider = snapshot_provider

    def resolve(
        self,
        *,
        request_id: object,
        raw_session_token: object,
        transport: AuthTransport | str,
    ) -> ActorContext:
        normalized_request_id = _normalize_request_id(request_id)
        auth_transport = _coerce_transport(transport)
        if normalized_request_id is None or auth_transport is None:
            raise ActorContextDenied

        validated = self._session_validator.validate_session(raw_session_token)
        if validated is None or not _validated_identity_is_consistent(validated):
            raise ActorContextDenied

        try:
            role_preset = RolePreset(validated.membership.role_preset)
            membership_status = MembershipStatus(
                validated.membership.membership_status
            )
        except (TypeError, ValueError):
            raise ActorContextDenied from None
        if (
            membership_status is not MembershipStatus.ACTIVE
            or role_policy_for(role_preset) is None
        ):
            raise ActorContextDenied

        plant_resolver = _BoundedPlantPermissionResolver(
            farm_id=validated.membership.farm_id,
            membership_id=validated.membership.membership_id,
            membership_status=membership_status,
            role_preset=role_preset,
            snapshot_provider=self._snapshot_provider,
        )
        return ActorContext._from_validated(
            request_id=normalized_request_id,
            validated_session=validated,
            role_preset=role_preset,
            membership_status=membership_status,
            transport=auth_transport,
            plant_permission_resolver=plant_resolver,
        )


def _validated_identity_is_consistent(validated: object) -> bool:
    return (
        isinstance(validated, ValidatedSession)
        and isinstance(validated.session, LocalSession)
        and isinstance(validated.account, Account)
        and isinstance(validated.membership, FarmMembership)
        and isinstance(validated.session.session_id, uuid.UUID)
        and isinstance(validated.account.account_id, uuid.UUID)
        and isinstance(validated.membership.membership_id, uuid.UUID)
        and isinstance(validated.membership.farm_id, uuid.UUID)
        and isinstance(validated.session.created_at, datetime)
        and isinstance(validated.session.expires_at, datetime)
        and validated.session.account_id == validated.account.account_id
        and validated.membership.account_id == validated.account.account_id
        and validated.account.account_status == "active"
        and validated.membership.membership_status == "active"
        and validated.session.auth_method == "local_password"
        and validated.session.revoked_at is None
    )


def _normalize_request_id(request_id: object) -> str | None:
    if not isinstance(request_id, str):
        return None
    normalized = request_id.strip()
    return normalized or None


def _coerce_transport(transport: AuthTransport | str) -> AuthTransport | None:
    try:
        return AuthTransport(transport)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ActorContext",
    "ActorContextDenied",
    "ActorContextResolver",
    "AuthProvenance",
    "AuthTransport",
    "SessionValidator",
]
