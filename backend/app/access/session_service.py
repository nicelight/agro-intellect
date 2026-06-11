from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from backend.app.access.db_repository import DbAccessRepository
from backend.app.access.models import (
    LocalSession,
    SessionStatus,
    SessionValidationResult,
    SessionValidationState,
    denied_session_result,
    utc_now,
)
from backend.app.access.db_repository import OneFarmViolation
from backend.app.security.session_refs import (
    auth_provenance_ref_from_hash,
    generate_session_secret,
    hash_session_secret,
    is_well_formed_session_secret,
    redacted_request_ref,
    session_ref_from_hash,
)

DEFAULT_SESSION_TTL = timedelta(hours=12)


async def create_local_session(
    repo: DbAccessRepository,
    *,
    account_id: str,
    now=None,
    ttl: timedelta = DEFAULT_SESSION_TTL,
    raw_session_secret: str | None = None,
    request_ref: str | None = None,
) -> tuple[LocalSession, str]:
    issued_at = now or utc_now()
    account = await repo.get_account(account_id)
    if account is None or not account.is_active:
        raise PermissionError("active account is required to create a session")
    membership = await repo.get_membership_for_account(account_id)
    if membership is None or not membership.is_active:
        raise PermissionError("active FarmMembership is required to create a session")
    farm = await repo.get_farm(membership.farm_id)
    if farm is None or not farm.is_active:
        raise PermissionError("active Farm is required to create a session")

    raw_secret = raw_session_secret or generate_session_secret()
    if not is_well_formed_session_secret(raw_secret):
        raise ValueError("session secret is malformed")
    session_hash = hash_session_secret(raw_secret)
    session = LocalSession(
        session_id=f"session_{uuid4().hex}",
        account_id=account.account_id,
        farm_id=farm.farm_id,
        membership_id=membership.membership_id,
        session_hash=session_hash,
        session_ref=session_ref_from_hash(session_hash),
        auth_provenance_ref=auth_provenance_ref_from_hash(session_hash),
        status=SessionStatus.ACTIVE,
        created_at=issued_at,
        expires_at=issued_at + ttl,
        created_request_ref=redacted_request_ref(request_ref or session_hash),
    )
    return await repo.add_session(session), raw_secret


async def revoke_local_session(
    repo: DbAccessRepository,
    session_id: str,
    *,
    now=None,
    request_ref: str | None = None,
) -> LocalSession:
    revoked_at = now or utc_now()
    return await repo.revoke_session(
        session_id,
        revoked_at=revoked_at,
        request_ref=redacted_request_ref(request_ref or session_id),
    )


async def validate_local_session(
    repo: DbAccessRepository,
    raw_session_secret: str | None,
    *,
    now=None,
    request_ref: str | None = None,
) -> SessionValidationResult:
    checked_at = now or utc_now()
    safe_request_ref = redacted_request_ref(request_ref or "missing_request")

    if raw_session_secret is None or raw_session_secret == "":
        return denied_session_result(
            "missing_session",
            request_ref=safe_request_ref,
            now=checked_at,
        )
    if not is_well_formed_session_secret(raw_session_secret):
        return denied_session_result(
            "malformed_session",
            request_ref=safe_request_ref,
            now=checked_at,
        )

    session_hash = hash_session_secret(raw_session_secret)
    session = await repo.get_session_by_hash(session_hash)
    if session is None:
        return denied_session_result(
            "invalid_session",
            session_ref=session_ref_from_hash(session_hash),
            auth_provenance_ref=auth_provenance_ref_from_hash(session_hash),
            request_ref=safe_request_ref,
            now=checked_at,
        )

    if session.is_revoked:
        return denied_session_result(
            "revoked_session",
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )
    if session.is_expired(checked_at):
        return denied_session_result(
            "expired_session",
            state=SessionValidationState.EXPIRED,
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )

    try:
        farm = await repo.get_single_farm()
    except OneFarmViolation:
        return denied_session_result(
            "farm_scope_invalid",
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )

    account = await repo.get_account(session.account_id)
    membership = await repo.get_membership(session.membership_id)
    if farm is None or farm.farm_id != session.farm_id:
        return denied_session_result(
            "farm_scope_invalid",
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )
    if account is None or not account.is_active:
        return denied_session_result(
            "inactive_account",
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )
    if (
        membership is None
        or membership.account_id != account.account_id
        or membership.farm_id != farm.farm_id
        or not membership.is_active
    ):
        return denied_session_result(
            "inactive_membership",
            session_ref=session.session_ref,
            auth_provenance_ref=session.auth_provenance_ref,
            request_ref=safe_request_ref,
            now=checked_at,
        )

    return SessionValidationResult(
        state=SessionValidationState.RESOLVED,
        account_id=account.account_id,
        farm_id=farm.farm_id,
        membership_id=membership.membership_id,
        role=membership.role,
        membership_status=membership.status,
        session_ref=session.session_ref,
        auth_provenance_ref=session.auth_provenance_ref,
        request_ref=safe_request_ref,
        resolved_at=checked_at,
    )
