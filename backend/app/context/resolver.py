from __future__ import annotations

from backend.app.access import (
    DbAccessRepository,
    SessionValidationState,
    validate_local_session,
)
from backend.app.context.models import ActorContext, ActorContextState


async def resolve_actor_context(
    repo: DbAccessRepository,
    session_secret: str | None,
    *,
    request_ref: str | None = None,
    now=None,
) -> ActorContext:
    result = await validate_local_session(repo, session_secret, now=now, request_ref=request_ref)

    if result.state is SessionValidationState.DENIED:
        return ActorContext(
            state=ActorContextState.DENIED,
            session_ref=result.session_ref,
            auth_provenance_ref=result.auth_provenance_ref,
            request_ref=result.request_ref,
            resolved_at=result.resolved_at,
        )

    if result.state is SessionValidationState.EXPIRED:
        return ActorContext(
            state=ActorContextState.EXPIRED,
            session_ref=result.session_ref,
            auth_provenance_ref=result.auth_provenance_ref,
            request_ref=result.request_ref,
            resolved_at=result.resolved_at,
        )

    return ActorContext(
        state=ActorContextState.RESOLVED,
        account_id=result.account_id,
        farm_id=result.farm_id,
        membership_id=result.membership_id,
        role=result.role.value if result.role else None,
        membership_status=result.membership_status.value if result.membership_status else None,
        session_ref=result.session_ref,
        auth_provenance_ref=result.auth_provenance_ref,
        request_ref=result.request_ref,
        resolved_at=result.resolved_at,
    )


async def require_actor_context(
    repo: DbAccessRepository,
    session_secret: str | None,
    *,
    request_ref: str | None = None,
    now=None,
) -> ActorContext:
    from backend.app.api.errors import AppError, ErrorCode

    ctx = await resolve_actor_context(repo, session_secret, request_ref=request_ref, now=now)

    if ctx.state is ActorContextState.RESOLVED:
        return ctx

    if ctx.state is ActorContextState.DENIED:
        raise AppError(
            code=ErrorCode.INVALID_SESSION,
            message="Session is invalid or denied.",
            request_ref=ctx.request_ref,
            next_actions=["authenticate"],
        )

    raise AppError(
        code=ErrorCode.INVALID_SESSION,
        message="Session has expired.",
        request_ref=ctx.request_ref,
        next_actions=["authenticate"],
    )
