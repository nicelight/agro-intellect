from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import ipaddress
from typing import Literal, Protocol
import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from ..access_admin.actor_context import (
    ActorContext,
    ActorContextDenied,
    ActorContextResolver,
    AuthTransport,
)
from ..access_admin.credential_service import (
    AuthenticationFailed,
    AuthenticationFailureReason,
)
from ..access_admin.errors import (
    AuthErrorCode,
    auth_error_response,
    request_id_for,
)
from ..access_admin.repository import AccessSessionRepository
from ..access_admin.session_service import (
    IssuedSession,
    SessionService,
    SessionValidationFailed,
    SessionValidationFailureReason,
    ValidatedSession,
)
from ..database import DatabaseHandle


SESSION_COOKIE_NAME = "agro_intellect_session"
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60

router = APIRouter(prefix="/api/session", tags=["session"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_name: str = Field(min_length=1, max_length=256)
    password: SecretStr = Field(min_length=1, max_length=4096)


class LoginResponse(BaseModel):
    account_id: uuid.UUID
    farm_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: str
    session_expires_at: datetime


class PlantScopeSummary(BaseModel):
    status: Literal["deferred"] = "deferred"


class CurrentSessionResponse(BaseModel):
    account_id: uuid.UUID
    display_name: str
    farm_id: uuid.UUID
    membership_id: uuid.UUID
    role_preset: str
    membership_status: str
    session_expires_at: datetime
    plant_scope_summary: PlantScopeSummary


@dataclass(frozen=True, slots=True)
class ResolvedCurrentSession:
    actor: ActorContext
    display_name: str


class SessionApiBackend(Protocol):
    def login(
        self,
        login_name: object,
        password: object,
        *,
        client_label: str | None = None,
    ) -> IssuedSession: ...

    def revoke_session(self, raw_token: object) -> bool: ...

    def resolve_current_session(
        self,
        raw_token: object,
        *,
        request_id: str,
        transport: AuthTransport,
    ) -> ResolvedCurrentSession | None: ...


@dataclass(frozen=True, slots=True)
class DatabaseSessionApiBackend:
    database: DatabaseHandle = field(repr=False)

    def login(
        self,
        login_name: object,
        password: object,
        *,
        client_label: str | None = None,
    ) -> IssuedSession:
        with self.database.session() as database_session:
            service = SessionService(AccessSessionRepository(database_session))
            try:
                issued = service.login(
                    login_name,
                    password,
                    client_label=client_label,
                )
                database_session.commit()
            except Exception:
                database_session.rollback()
                raise
            return issued

    def revoke_session(self, raw_token: object) -> bool:
        with self.database.session() as database_session:
            service = SessionService(AccessSessionRepository(database_session))
            try:
                revoked = service.revoke_session(raw_token)
                database_session.commit()
            except Exception:
                database_session.rollback()
                raise
            return revoked

    def resolve_current_session(
        self,
        raw_token: object,
        *,
        request_id: str,
        transport: AuthTransport,
    ) -> ResolvedCurrentSession | None:
        with self.database.session() as database_session:
            service = SessionService(AccessSessionRepository(database_session))
            validated = service.require_valid_session(raw_token)
            try:
                actor = ActorContextResolver(
                    session_validator=_PrevalidatedSessionSource(validated),
                    snapshot_provider=_no_plant_snapshot,
                ).resolve(
                    request_id=request_id,
                    raw_session_token=raw_token,
                    transport=transport,
                )
            except ActorContextDenied:
                return None
            return ResolvedCurrentSession(
                actor=actor,
                display_name=validated.account.display_name,
            )


@dataclass(frozen=True, slots=True)
class _PrevalidatedSessionSource:
    validated: ValidatedSession

    def validate_session(self, _raw_token: object) -> ValidatedSession:
        return self.validated


class _PlainHttpBrowserDenied(Exception):
    pass


def _no_plant_snapshot(**_kwargs):
    return None


def get_session_backend(request: Request) -> SessionApiBackend:
    return DatabaseSessionApiBackend(request.app.state.database)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    backend: SessionApiBackend = Depends(get_session_backend),
):
    if request.headers.get("authorization") or request.cookies.get(
        SESSION_COOKIE_NAME
    ):
        return auth_error_response(request, AuthErrorCode.FORBIDDEN)

    try:
        secure_cookie = _browser_cookie_secure(request)
    except _PlainHttpBrowserDenied:
        return auth_error_response(request, AuthErrorCode.FORBIDDEN)

    try:
        issued = backend.login(
            payload.login_name,
            payload.password.get_secret_value(),
            client_label="browser",
        )
    except AuthenticationFailed as error:
        return auth_error_response(request, _login_error_code(error.reason))

    expires_at = _as_utc(issued.session.expires_at)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=issued.raw_token,
        max_age=_cookie_max_age(issued),
        expires=expires_at,
        path=SESSION_COOKIE_PATH,
        secure=secure_cookie,
        httponly=True,
        samesite="lax",
    )
    _set_no_store(response)
    return LoginResponse(
        account_id=issued.account.account_id,
        farm_id=issued.membership.farm_id,
        membership_id=issued.membership.membership_id,
        role_preset=issued.membership.role_preset,
        session_expires_at=expires_at,
    )


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    request: Request,
    backend: SessionApiBackend = Depends(get_session_backend),
) -> Response:
    raw_token = _single_cookie_credential(request)
    if raw_token is not None:
        backend.revoke_session(raw_token)

    response = Response(status_code=204)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value="",
        max_age=0,
        expires=datetime(1970, 1, 1, tzinfo=timezone.utc),
        path=SESSION_COOKIE_PATH,
        secure=_clear_cookie_secure(request),
        httponly=True,
        samesite="lax",
    )
    _set_no_store(response)
    return response


@router.get("/me", response_model=CurrentSessionResponse)
def current_session(
    request: Request,
    response: Response,
    backend: SessionApiBackend = Depends(get_session_backend),
):
    try:
        _browser_cookie_secure(request)
    except _PlainHttpBrowserDenied:
        return auth_error_response(request, AuthErrorCode.FORBIDDEN)

    raw_token = _single_cookie_credential(request)
    if raw_token is None:
        code = (
            AuthErrorCode.SESSION_INVALID
            if request.headers.get("authorization")
            else AuthErrorCode.SESSION_REQUIRED
        )
        return auth_error_response(request, code)

    request_id = request_id_for(request)
    try:
        resolved = backend.resolve_current_session(
            raw_token,
            request_id=request_id,
            transport=AuthTransport.COOKIE,
        )
    except SessionValidationFailed as error:
        return auth_error_response(request, _session_error_code(error.reason))
    if resolved is None:
        return auth_error_response(request, AuthErrorCode.SESSION_INVALID)

    actor = resolved.actor
    _set_no_store(response)
    return CurrentSessionResponse(
        account_id=actor.account_id,
        display_name=resolved.display_name,
        farm_id=actor.farm_id,
        membership_id=actor.membership_id,
        role_preset=actor.role_preset.value,
        membership_status=actor.membership_status.value,
        session_expires_at=_as_utc(actor.auth_provenance.session_expires_at),
        plant_scope_summary=PlantScopeSummary(),
    )


def _single_cookie_credential(request: Request) -> str | None:
    if request.headers.get("authorization"):
        return None
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not isinstance(raw_token, str) or not raw_token:
        return None
    return raw_token


def _login_error_code(reason: AuthenticationFailureReason) -> AuthErrorCode:
    return {
        AuthenticationFailureReason.CREDENTIAL_INVALID: (
            AuthErrorCode.CREDENTIAL_INVALID
        ),
        AuthenticationFailureReason.ACCOUNT_DISABLED: (
            AuthErrorCode.ACCOUNT_DISABLED
        ),
        AuthenticationFailureReason.MEMBERSHIP_REQUIRED: (
            AuthErrorCode.MEMBERSHIP_REQUIRED
        ),
        AuthenticationFailureReason.MEMBERSHIP_DISABLED: (
            AuthErrorCode.MEMBERSHIP_DISABLED
        ),
    }.get(reason, AuthErrorCode.CREDENTIAL_INVALID)


def _session_error_code(reason: SessionValidationFailureReason) -> AuthErrorCode:
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


def _browser_cookie_secure(request: Request) -> bool:
    scheme = request.url.scheme.lower()
    if scheme == "https" and _request_is_loopback(request):
        return True
    if scheme == "http" and _request_is_loopback(request):
        return False
    raise _PlainHttpBrowserDenied


def _clear_cookie_secure(request: Request) -> bool:
    return not (
        request.url.scheme.lower() == "http"
        and _request_is_loopback(request)
    )


def _request_is_loopback(request: Request) -> bool:
    return _is_loopback_host(request.url.hostname) and _is_loopback_host(
        request.client.host if request.client is not None else None
    )


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    normalized = hostname.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _cookie_max_age(issued: IssuedSession) -> int:
    ttl_seconds = int(
        (_as_utc(issued.session.expires_at) - _as_utc(issued.session.created_at))
        .total_seconds()
    )
    return max(0, min(SESSION_COOKIE_MAX_AGE, ttl_seconds))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _set_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


__all__ = [
    "CurrentSessionResponse",
    "DatabaseSessionApiBackend",
    "LoginRequest",
    "LoginResponse",
    "ResolvedCurrentSession",
    "SESSION_COOKIE_MAX_AGE",
    "SESSION_COOKIE_NAME",
    "SessionApiBackend",
    "get_session_backend",
    "router",
]
