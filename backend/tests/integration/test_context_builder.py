"""Integration tests for PermissionAwareContextBuilder."""

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
from backend.app.api.errors import AppError, ErrorCode
from backend.app.context import (
    ActorContext,
    ActorContextState,
    PermissionAwareContextBuilder,
    PlantPermission,
)
from backend.app.context.resolver import resolve_actor_context
from backend.app.security import generate_session_secret

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


async def build_repo() -> FakeAccessRepository:
    repo = FakeAccessRepository()
    await repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=AccountStatus.ACTIVE,
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
            status=MembershipStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


async def build_resolved_boss_context(repo: FakeAccessRepository) -> ActorContext:
    _session, raw_secret = await create_local_session(
        repo, account_id="acct_boss", now=NOW, raw_session_secret=generate_session_secret(),
    )
    return await resolve_actor_context(repo, raw_secret, request_ref="req_test", now=NOW + timedelta(minutes=1))


class TestContextBuilder:
    async def test_build_context_resolved_returns_package(self):
        repo = await build_repo()
        ctx = await build_resolved_boss_context(repo)
        builder = PermissionAwareContextBuilder(repo)

        pkg = builder.build_context(ctx, request_ref="req_test")

        assert pkg.actor_context is ctx
        assert pkg.farm_id == "farm_local"
        assert pkg.role == "boss"
        assert pkg.plant_ids == []
        assert pkg.permissions["manage_accounts"] is True
        assert pkg.built_at is not None

    async def test_build_context_with_plant_permissions(self):
        repo = await build_repo()
        ctx = ActorContext(
            state=ActorContextState.RESOLVED,
            account_id="acct_boss",
            farm_id="farm_local",
            membership_id="mbr_boss",
            role="boss",
            membership_status="active",
            plant_permissions=(
                PlantPermission(
                    plant_id="plant_a",
                    grant_state="granted",
                    can_view=True,
                    can_work=True,
                    plant_approve_actions=True,
                ),
                PlantPermission(
                    plant_id="plant_b",
                    grant_state="granted",
                    can_view=True,
                    can_work=False,
                    plant_approve_actions=False,
                ),
            ),
            session_ref="sess_ref_abc",
            auth_provenance_ref="auth_ref_abc",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        pkg = builder.build_context(ctx, request_ref="req_test")

        assert "plant_a" in pkg.plant_ids
        assert "plant_b" in pkg.plant_ids
        assert pkg.permissions["plant_approve_actions"] is True

    async def test_build_context_without_grants_empty_plants(self):
        repo = await build_repo()
        ctx = ActorContext(
            state=ActorContextState.RESOLVED,
            account_id="acct_boss",
            farm_id="farm_local",
            membership_id="mbr_boss",
            role="boss",
            membership_status="active",
            session_ref="sess_ref_abc",
            auth_provenance_ref="auth_ref_abc",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        pkg = builder.build_context(ctx, request_ref="req_test")

        assert pkg.plant_ids == []
        assert pkg.permissions["plant_approve_actions"] is False

    async def test_build_context_denied_raises_permission_denied(self):
        repo = await build_repo()
        denied_ctx = ActorContext(
            state=ActorContextState.DENIED,
            session_ref="sess_ref_redacted",
            auth_provenance_ref="auth_ref_redacted",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        with pytest.raises(AppError) as excinfo:
            builder.build_context(denied_ctx, request_ref="req_test")

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    async def test_build_context_expired_raises_permission_denied(self):
        repo = await build_repo()
        expired_ctx = ActorContext(
            state=ActorContextState.EXPIRED,
            session_ref="sess_ref_redacted",
            auth_provenance_ref="auth_ref_redacted",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        with pytest.raises(AppError) as excinfo:
            builder.build_context(expired_ctx, request_ref="req_test")

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    async def test_authorize_plant_access_authorized_passes(self):
        repo = await build_repo()
        ctx = ActorContext(
            state=ActorContextState.RESOLVED,
            account_id="acct_boss",
            farm_id="farm_local",
            membership_id="mbr_boss",
            role="boss",
            membership_status="active",
            plant_permissions=(
                PlantPermission(
                    plant_id="plant_a",
                    grant_state="granted",
                    can_view=True,
                    can_work=True,
                    plant_approve_actions=True,
                ),
            ),
            session_ref="sess_ref_abc",
            auth_provenance_ref="auth_ref_abc",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        builder.authorize_plant_access(ctx, "plant_a")

    async def test_authorize_plant_access_unauthorized_raises(self):
        repo = await build_repo()
        ctx = ActorContext(
            state=ActorContextState.RESOLVED,
            account_id="acct_boss",
            farm_id="farm_local",
            membership_id="mbr_boss",
            role="boss",
            membership_status="active",
            plant_permissions=(
                PlantPermission(
                    plant_id="plant_a",
                    grant_state="granted",
                    can_view=True,
                    can_work=True,
                    plant_approve_actions=True,
                ),
            ),
            session_ref="sess_ref_abc",
            auth_provenance_ref="auth_ref_abc",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        with pytest.raises(AppError) as excinfo:
            builder.authorize_plant_access(ctx, "plant_unknown")

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    async def test_authorize_plant_access_revoked_raises(self):
        repo = await build_repo()
        ctx = ActorContext(
            state=ActorContextState.RESOLVED,
            account_id="acct_boss",
            farm_id="farm_local",
            membership_id="mbr_boss",
            role="boss",
            membership_status="active",
            plant_permissions=(
                PlantPermission(
                    plant_id="plant_a",
                    grant_state="revoked",
                    can_view=False,
                    can_work=False,
                    plant_approve_actions=False,
                ),
            ),
            session_ref="sess_ref_abc",
            auth_provenance_ref="auth_ref_abc",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        with pytest.raises(AppError) as excinfo:
            builder.authorize_plant_access(ctx, "plant_a")

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    async def test_authorize_plant_access_denied_context_raises(self):
        repo = await build_repo()
        denied_ctx = ActorContext(
            state=ActorContextState.DENIED,
            session_ref="sess_ref_redacted",
            auth_provenance_ref="auth_ref_redacted",
            request_ref="req_test",
            resolved_at=NOW,
        )
        builder = PermissionAwareContextBuilder(repo)

        with pytest.raises(AppError) as excinfo:
            builder.authorize_plant_access(denied_ctx, "plant_a")

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
