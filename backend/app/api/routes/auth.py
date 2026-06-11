from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.access import create_local_session, revoke_local_session
from backend.app.access.db_repository import DbAccessRepository
from backend.app.api.deps import get_db
from backend.app.api.errors import AppError, ErrorCode
from backend.app.api.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, MeResponse
from backend.app.context.models import ActorContext
from backend.app.context.resolver import require_actor_context

router = APIRouter(prefix="/api/v1/auth")

_TEST_REPO = None


def _get_repo(session: AsyncSession) -> Any:
    if _TEST_REPO is not None:
        return _TEST_REPO
    return DbAccessRepository(session)


async def _resolve_session(
    authorization: str = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> ActorContext:
    repo = _get_repo(session)
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    return await require_actor_context(repo, session_secret, request_ref=f"req_{uuid4().hex}")


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    repo = _get_repo(session)
    account_id = await _resolve_account_id(repo, body.login_identifier)
    if account_id is None:
        raise AppError(
            code=ErrorCode.INVALID_REQUEST,
            message="Invalid credentials.",
            next_actions=["check_credentials"],
        )
    try:
        sess, raw_secret = await create_local_session(
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
        session_ref=sess.session_ref,
        expires_at=sess.expires_at.isoformat(),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    ctx: ActorContext = Depends(_resolve_session),
    authorization: str = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
):
    repo = _get_repo(session)
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    if ctx.session_ref:
        sessions = await repo.get_sessions_iter()
        for sess in sessions:
            if sess.session_ref == ctx.session_ref:
                await revoke_local_session(repo, sess.session_id, request_ref=f"req_{uuid4().hex}")
                return LogoutResponse(status="logged_out")
    return LogoutResponse(status="logged_out")


@router.get("/me", response_model=MeResponse)
async def me(ctx: ActorContext = Depends(_resolve_session)):
    return MeResponse(
        state=ctx.state.value,
        account_id=ctx.account_id,
        farm_id=ctx.farm_id,
        membership_id=ctx.membership_id,
        role=ctx.role,
        membership_status=ctx.membership_status,
        resolved_at=ctx.resolved_at.isoformat() if ctx.resolved_at else None,
    )


async def _resolve_account_id(repo, login_identifier: str) -> str | None:
    accounts = await repo.get_accounts_iter()
    for account in accounts:
        if account.login_identifier == login_identifier:
            return account.account_id
    return None
