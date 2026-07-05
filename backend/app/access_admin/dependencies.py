from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from ..core.security import SESSION_COOKIE_NAME
from .actor_context import (
    ActorContext,
    ActorContextDenied,
    ActorContextResolver,
    AuthTransport,
)
from .context_builders import plant_permission_allows
from .errors import AuthErrorCode, auth_error_response, request_id_for
from .permissions import (
    OperationKind,
    PlantAccessSnapshot,
    PlantAccessSnapshotProvider,
    PlantPermissionContext,
)
from .repository import AccessSessionRepository
from .session_service import (
    SessionService,
    SessionValidationFailed,
    SessionValidationFailureReason,
    ValidatedSession,
)


class ProtectedRouteDenied(Exception):
    """Stop a protected request with one stable, redacted auth error."""

    def __init__(self, code: AuthErrorCode) -> None:
        self.code = code
        super().__init__("Protected request denied.")


@dataclass(frozen=True, slots=True)
class AuthorizedPlantRequest:
    """Internal route-only result; never serialize this object directly."""

    actor: ActorContext
    permission: PlantPermissionContext


@dataclass(frozen=True, slots=True)
class _PrevalidatedSessionValidator:
    validated: ValidatedSession

    def validate_session(self, _raw_token: object) -> ValidatedSession:
        return self.validated


async def protected_route_denied_handler(
    request: Request,
    error: ProtectedRouteDenied,
) -> JSONResponse:
    return auth_error_response(request, error.code)


def install_protected_route_error_handler(app: FastAPI) -> None:
    app.add_exception_handler(ProtectedRouteDenied, protected_route_denied_handler)


def get_plant_access_snapshot_provider(
    request: Request,
) -> PlantAccessSnapshotProvider:
    provider = getattr(request.app.state, "plant_access_snapshot_provider", None)
    if callable(provider):
        return provider
    return _deny_all_plant_snapshots


def require_actor_context(
    request: Request,
    snapshot_provider=Depends(get_plant_access_snapshot_provider),
) -> ActorContext:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_token is None and not request.headers.get("authorization"):
        raise ProtectedRouteDenied(AuthErrorCode.SESSION_REQUIRED)
    if request.headers.get("authorization") or not isinstance(raw_token, str):
        raise ProtectedRouteDenied(AuthErrorCode.SESSION_INVALID)
    if not raw_token:
        raise ProtectedRouteDenied(AuthErrorCode.SESSION_INVALID)

    request_id = request_id_for(request)
    with request.app.state.database.session() as database_session:
        service = SessionService(AccessSessionRepository(database_session))
        try:
            validated = service.require_valid_session(raw_token)
        except SessionValidationFailed as error:
            raise ProtectedRouteDenied(
                _session_error_code(error.reason)
            ) from None

        try:
            return ActorContextResolver(
                session_validator=_PrevalidatedSessionValidator(validated),
                snapshot_provider=snapshot_provider,
            ).resolve(
                request_id=request_id,
                raw_session_token=raw_token,
                transport=AuthTransport.COOKIE,
            )
        except ActorContextDenied:
            raise ProtectedRouteDenied(AuthErrorCode.SESSION_INVALID) from None


def require_plant_permission(
    operation_kind: OperationKind | str,
) -> Callable[..., AuthorizedPlantRequest]:
    try:
        operation = OperationKind(operation_kind)
    except (TypeError, ValueError) as error:
        raise ValueError("Unsupported protected Plant operation.") from error

    def dependency(
        plant_id: uuid.UUID,
        actor: ActorContext = Depends(require_actor_context),
    ) -> AuthorizedPlantRequest:
        permission = actor.resolve_plant_permission(plant_id, operation)
        if not plant_permission_allows(permission, operation):
            raise ProtectedRouteDenied(AuthErrorCode.PLANT_FORBIDDEN)
        return AuthorizedPlantRequest(actor=actor, permission=permission)

    dependency.__name__ = f"require_plant_{operation.value}"
    return dependency


def _session_error_code(
    reason: SessionValidationFailureReason,
) -> AuthErrorCode:
    return {
        SessionValidationFailureReason.SESSION_INVALID: (
            AuthErrorCode.SESSION_INVALID
        ),
        SessionValidationFailureReason.SESSION_EXPIRED: (
            AuthErrorCode.SESSION_EXPIRED
        ),
        SessionValidationFailureReason.ACCOUNT_DISABLED: (
            AuthErrorCode.ACCOUNT_DISABLED
        ),
        SessionValidationFailureReason.MEMBERSHIP_REQUIRED: (
            AuthErrorCode.MEMBERSHIP_REQUIRED
        ),
        SessionValidationFailureReason.MEMBERSHIP_DISABLED: (
            AuthErrorCode.MEMBERSHIP_DISABLED
        ),
    }.get(reason, AuthErrorCode.SESSION_INVALID)


def _deny_all_plant_snapshots(
    **_kwargs,
) -> PlantAccessSnapshot | None:
    return None


__all__ = [
    "AuthorizedPlantRequest",
    "ProtectedRouteDenied",
    "get_plant_access_snapshot_provider",
    "install_protected_route_error_handler",
    "require_actor_context",
    "require_plant_permission",
]
