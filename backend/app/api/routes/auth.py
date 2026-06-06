"""Authentication routes: login, logout, me."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header

from backend.app.access import (
    InMemoryAccessRepository,
    create_local_session,
    revoke_local_session,
)
from backend.app.api.errors import AppError, ErrorCode
from backend.app.api.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, MeResponse
from backend.app.context import ActorContext, resolve_actor_context
from backend.app.context.resolver import require_actor_context

router = APIRouter(prefix="/api/v1/auth")

# Testability hook: set to override repo creation (used by integration tests)
_TEST_REPO: InMemoryAccessRepository | None = None


def _get_repo() -> InMemoryAccessRepository:
    if _TEST_REPO is not None:
        return _TEST_REPO
    from backend.app.access.repository import InMemoryAccessRepository

    return InMemoryAccessRepository()


def _resolve_session(
    authorization: str = Header(None, alias="Authorization"),
) -> ActorContext:
    repo = _get_repo()
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    return require_actor_context(repo, session_secret, request_ref=f"req_{uuid4().hex}")


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    repo: InMemoryAccessRepository = Depends(_get_repo),
):
    account_id = _resolve_account_id(repo, body.login_identifier)
    if account_id is None:
        raise AppError(
            code=ErrorCode.INVALID_REQUEST,
            message="Invalid credentials.",
            next_actions=["check_credentials"],
        )
    try:
        session, raw_secret = create_local_session(
            repo,
            account_id=account_id,
            request_ref=f"req_{uuid4().hex}",
        )
    except PermissionError:
        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="Account cannot create session.",
            next_actions=["contact_admin"],
        )
    return LoginResponse(
        session_token=raw_secret,
        session_ref=session.session_ref,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    ctx: ActorContext = Depends(_resolve_session),
    authorization: str = Header(None, alias="Authorization"),
):
    repo = _get_repo()
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    if ctx.session_ref:
        for sid, sess in repo.sessions_by_id.items():
            if sess.session_ref == ctx.session_ref:
                revoke_local_session(repo, sid, request_ref=f"req_{uuid4().hex}")
                return LogoutResponse(status="logged_out")
    return LogoutResponse(status="logged_out")


@router.get("/me", response_model=MeResponse)
def me(ctx: ActorContext = Depends(_resolve_session)):
    return MeResponse(
        state=ctx.state.value,
        account_id=ctx.account_id,
        farm_id=ctx.farm_id,
        membership_id=ctx.membership_id,
        role=ctx.role,
        membership_status=ctx.membership_status,
        resolved_at=ctx.resolved_at.isoformat() if ctx.resolved_at else None,
    )


def _resolve_account_id(repo: InMemoryAccessRepository, login_identifier: str) -> str | None:
    for account in repo.accounts.values():
        if account.login_identifier == login_identifier:
            return account.account_id
    return None
