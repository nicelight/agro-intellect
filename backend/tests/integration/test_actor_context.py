"""Integration tests for ActorContext resolution and API boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    MembershipRole,
    MembershipStatus,
    create_local_session,
)
from backend.tests.doubles import FakeAccessRepository
from backend.app.api.errors import AppError, ErrorCode, error_response
from backend.app.context import ActorContext, ActorContextState, resolve_actor_context
from backend.app.context.resolver import require_actor_context
from backend.app.security import generate_session_secret

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


async def build_repo(
    *,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
) -> FakeAccessRepository:
    repo = FakeAccessRepository()
    await repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=account_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    await repo.add_farm(
        Farm(
            farm_id="farm_local",
            display_name="Local Farm",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    await repo.add_membership(
        FarmMembership(
            membership_id="mbr_boss",
            account_id="acct_boss",
            farm_id="farm_local",
            role=MembershipRole.BOSS,
            status=membership_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


class TestResolveActorContext:
    async def test_missing_session_returns_denied(self):
        repo = await build_repo()
        ctx = await resolve_actor_context(repo, None, request_ref="req_test", now=NOW)

        assert ctx.state is ActorContextState.DENIED
        assert ctx.account_id is None
        assert ctx.farm_id is None
        assert ctx.membership_id is None
        assert ctx.role is None
        assert ctx.membership_status is None

    async def test_invalid_long_enough_session_returns_denied(self):
        repo = await build_repo()
        ctx = await resolve_actor_context(repo, "fake-long-enough-secret-for-testing-1234567890", request_ref="req_test", now=NOW)

        assert ctx.state is ActorContextState.DENIED
        assert ctx.account_id is None

    async def test_valid_session_returns_resolved(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, raw_session_secret=generate_session_secret(),
        )

        ctx = await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=1))

        assert ctx.state is ActorContextState.RESOLVED
        assert ctx.account_id == "acct_boss"
        assert ctx.farm_id == "farm_local"
        assert ctx.membership_id == "mbr_boss"
        assert ctx.role == "boss"
        assert ctx.membership_status == "active"
        assert ctx.resolved_at is not None

    async def test_expired_session_returns_expired(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, ttl=timedelta(minutes=5),
            raw_session_secret=generate_session_secret(),
        )

        ctx = await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=10))

        assert ctx.state is ActorContextState.EXPIRED

    async def test_expired_session_carries_safe_refs_only(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, ttl=timedelta(minutes=5),
            raw_session_secret=generate_session_secret(),
        )

        ctx = await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=10))

        assert ctx.account_id is None
        assert ctx.farm_id is None
        assert ctx.membership_id is None
        assert ctx.role is None

    async def test_denied_context_carries_safe_refs_only(self):
        repo = await build_repo()
        ctx = await resolve_actor_context(repo, None, request_ref="req_test", now=NOW)

        assert ctx.account_id is None
        assert ctx.farm_id is None
        assert ctx.membership_id is None
        assert ctx.role is None
        assert ctx.membership_status is None
        assert ctx.plant_permissions == ()

    async def test_resolved_context_includes_empty_plant_permissions(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, raw_session_secret=generate_session_secret(),
        )

        ctx = await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=1))

        assert ctx.state is ActorContextState.RESOLVED
        assert ctx.plant_permissions == ()

    async def test_resolved_context_has_redacted_refs(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, raw_session_secret=generate_session_secret(),
        )

        ctx = await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=1))

        assert ctx.session_ref is not None
        assert ctx.session_ref.startswith("sess_ref_")
        assert ctx.auth_provenance_ref is not None
        assert ctx.auth_provenance_ref.startswith("auth_ref_")

    async def test_empty_session_string_returns_denied(self):
        repo = await build_repo()
        ctx = await resolve_actor_context(repo, "", request_ref="req_test", now=NOW)

        assert ctx.state is ActorContextState.DENIED
        assert ctx.account_id is None


class TestRequireActorContext:
    async def test_denied_session_raises_app_error(self):
        repo = await build_repo()

        with pytest.raises(AppError) as excinfo:
            await require_actor_context(repo, None, request_ref="req_test", now=NOW)

        assert excinfo.value.code is ErrorCode.INVALID_SESSION

    async def test_resolved_session_returns_context(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, raw_session_secret=generate_session_secret(),
        )

        ctx = await require_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=1))

        assert ctx.state is ActorContextState.RESOLVED
        assert ctx.account_id == "acct_boss"

    async def test_expired_session_raises_app_error(self):
        repo = await build_repo()
        _session, raw_secret = await create_local_session(
            repo, account_id="acct_boss", now=NOW, ttl=timedelta(minutes=5),
            raw_session_secret=generate_session_secret(),
        )

        with pytest.raises(AppError) as excinfo:
            await require_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=10))

        assert excinfo.value.code is ErrorCode.INVALID_SESSION


class TestApiErrorEnvelope:
    def test_error_response_format(self):
        error = AppError(
            code=ErrorCode.INVALID_SESSION,
            message="Session is invalid.",
            request_ref="req_abc123",
            next_actions=["authenticate"],
        )

        resp = error_response(error)

        assert "error" in resp
        assert resp["error"]["code"] == "invalid_session"
        assert resp["error"]["message"] == "Session is invalid."
        assert resp["error"]["request_ref"] == "req_abc123"
        assert resp["error"]["next_valid_actions"] == ["authenticate"]
        assert isinstance(resp["error"]["details"], dict)

    def test_error_response_minimal_has_defaults(self):
        error = AppError(code=ErrorCode.NOT_FOUND, message="Not found")

        resp = error_response(error)

        assert resp["error"]["code"] == "not_found"
        assert resp["error"]["request_ref"] is not None

    def test_error_response_all_enum_values(self):
        for code in ErrorCode:
            error = AppError(code=code, message="test")
            resp = error_response(error)
            assert resp["error"]["code"] == code.value
