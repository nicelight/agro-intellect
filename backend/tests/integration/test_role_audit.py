"""Integration tests for role-based authorization and admin audit records."""

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
from backend.app.access.authorization import (
    BOSS,
    CONSULTANT,
    ENGINEER,
    require_boss,
    require_engineer_or_boss,
    require_role,
)
from backend.app.api.errors import AppError, ErrorCode
from backend.app.audit import AdminAuditAction, AdminAuditRecord
from backend.tests.doubles import FakeAccessRepository, FakeAuditRepository
from backend.app.context import ActorContext, ActorContextState
from backend.app.security import generate_session_secret

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


async def build_repo(
    *,
    account_status: AccountStatus = AccountStatus.ACTIVE,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
    role: MembershipRole = MembershipRole.BOSS,
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
    await repo.add_account(
        Account(
            account_id="acct_admin",
            display_name="Admin",
            login_identifier="admin.local",
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
            role=role,
            status=membership_status,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


def _resolved_ctx(
    role: str,
    account_id: str = "acct_boss",
    request_ref: str = "req_integration_test",
    session_ref: str = "sess_ref_integration",
    auth_ref: str = "auth_ref_integration",
) -> ActorContext:
    return ActorContext(
        state=ActorContextState.RESOLVED,
        account_id=account_id,
        farm_id="farm_local",
        membership_id="mbr_boss",
        role=role,
        membership_status="active",
        session_ref=session_ref,
        auth_provenance_ref=auth_ref,
        request_ref=request_ref,
        resolved_at=NOW,
    )


class TestAccountCreationAudit:
    async def test_account_creation_creates_admin_audit_record(self):
        audit = FakeAuditRepository()
        record = AdminAuditRecord(
            audit_id="audit_acct_create_001",
            action=AdminAuditAction.ACCOUNT_CREATED,
            actor_account_id="acct_boss",
            target_account_id="acct_new",
            farm_id="farm_local",
            details={"display_name": "New User"},
            auth_provenance_ref="auth_ref_create",
            request_ref="req_create_account",
            created_at=NOW,
        )
        await audit.add_record(record)

        records = await audit.list_records(account_id="acct_boss")
        assert len(records) == 1
        assert records[0].action is AdminAuditAction.ACCOUNT_CREATED
        assert records[0].target_account_id == "acct_new"

    async def test_audit_records_do_not_contain_raw_auth_material(self):
        audit = FakeAuditRepository()
        record = AdminAuditRecord(
            audit_id="audit_safe_001",
            action=AdminAuditAction.ACCOUNT_CREATED,
            actor_account_id="acct_boss",
            target_account_id="acct_new",
            details={},
            auth_provenance_ref="auth_ref_safe",
            request_ref="req_safe",
            created_at=NOW,
        )
        await audit.add_record(record)

        r = (await audit.list_records())[0]
        raw = repr(r)
        # No raw session/token/auth material
        assert "raw_secret" not in raw
        assert "Bearer" not in raw
        assert "token" not in raw.lower() or "auth_ref_" in raw

    async def test_audit_record_has_redacted_refs(self):
        audit = FakeAuditRepository()
        record = AdminAuditRecord(
            audit_id="audit_refs_001",
            action=AdminAuditAction.MEMBERSHIP_ROLE_CHANGED,
            actor_account_id="acct_boss",
            target_account_id="acct_target",
            details={"previous_role": "engineer", "new_role": "consultant"},
            auth_provenance_ref="auth_ref_abc123def456",
            request_ref="req_ref_xyz789",
            created_at=NOW,
        )
        await audit.add_record(record)

        r = (await audit.list_records())[0]
        assert r.auth_provenance_ref is not None
        assert r.auth_provenance_ref.startswith("auth_ref_")
        assert r.request_ref is not None
        assert r.request_ref.startswith("req_ref_")


class TestRoleChangeAudit:
    async def test_role_change_creates_admin_audit_record(self):
        audit = FakeAuditRepository()
        record = AdminAuditRecord(
            audit_id="audit_role_001",
            action=AdminAuditAction.MEMBERSHIP_ROLE_CHANGED,
            actor_account_id="acct_boss",
            target_account_id="acct_target",
            membership_id="mbr_target",
            farm_id="farm_local",
            details={"previous_role": "engineer", "new_role": "consultant"},
            auth_provenance_ref="auth_ref_role_change",
            request_ref="req_change_role",
            created_at=NOW,
        )
        await audit.add_record(record)

        records = await audit.list_records(action=AdminAuditAction.MEMBERSHIP_ROLE_CHANGED)
        assert len(records) == 1
        assert records[0].details["new_role"] == "consultant"


class TestAuditRepository:
    async def test_list_records_filters_by_account_id(self):
        audit = FakeAuditRepository()
        await audit.add_record(
            AdminAuditRecord(
                audit_id="a1", action=AdminAuditAction.ACCOUNT_CREATED,
                actor_account_id="acct_a", created_at=NOW,
            )
        )
        await audit.add_record(
            AdminAuditRecord(
                audit_id="a2", action=AdminAuditAction.ACCOUNT_DISABLED,
                actor_account_id="acct_b", created_at=NOW,
            )
        )
        assert len(await audit.list_records(account_id="acct_a")) == 1
        assert len(await audit.list_records(account_id="acct_b")) == 1
        assert len(await audit.list_records(account_id="acct_c")) == 0

    async def test_list_records_filters_by_action(self):
        audit = FakeAuditRepository()
        await audit.add_record(
            AdminAuditRecord(
                audit_id="a1", action=AdminAuditAction.ACCOUNT_CREATED,
                actor_account_id="acct_boss", created_at=NOW,
            )
        )
        await audit.add_record(
            AdminAuditRecord(
                audit_id="a2", action=AdminAuditAction.ACCOUNT_DISABLED,
                actor_account_id="acct_boss", created_at=NOW,
            )
        )
        assert len(await audit.list_records(action=AdminAuditAction.ACCOUNT_CREATED)) == 1

    async def test_list_records_respects_limit(self):
        audit = FakeAuditRepository()
        for i in range(10):
            await audit.add_record(
                AdminAuditRecord(
                    audit_id=f"a{i}", action=AdminAuditAction.ACCOUNT_CREATED,
                    actor_account_id="acct_boss", created_at=NOW,
                )
            )
        assert len(await audit.list_records(limit=3)) == 3
        assert len(await audit.list_records(limit=100)) == 10

    async def test_get_records_for_farm(self):
        audit = FakeAuditRepository()
        await audit.add_record(
            AdminAuditRecord(
                audit_id="f1", action=AdminAuditAction.ACCOUNT_CREATED,
                actor_account_id="acct_boss", farm_id="farm_a", created_at=NOW,
            )
        )
        await audit.add_record(
            AdminAuditRecord(
                audit_id="f2", action=AdminAuditAction.ACCOUNT_DISABLED,
                actor_account_id="acct_boss", farm_id="farm_b", created_at=NOW,
            )
        )
        assert len(await audit.get_records_for_farm("farm_a")) == 1
        assert len(await audit.get_records_for_farm("farm_c")) == 0


class TestAuthorizationWithActorContext:
    def test_boss_can_access_boss_only_operation(self):
        ctx = _resolved_ctx(role=BOSS)
        require_boss(ctx)

    def test_engineer_cannot_access_boss_only_operation(self):
        ctx = _resolved_ctx(role=ENGINEER)
        with pytest.raises(AppError) as excinfo:
            require_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_consultant_cannot_access_engineer_or_boss_operation(self):
        ctx = _resolved_ctx(role=CONSULTANT)
        with pytest.raises(AppError) as excinfo:
            require_engineer_or_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_engineer_can_access_engineer_or_boss_operation(self):
        ctx = _resolved_ctx(role=ENGINEER)
        require_engineer_or_boss(ctx)

    def test_boss_can_access_engineer_or_boss_operation(self):
        ctx = _resolved_ctx(role=BOSS)
        require_engineer_or_boss(ctx)

    def test_non_boss_admin_mutation_denied(self):
        ctx = _resolved_ctx(role=ENGINEER)
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_non_boss_admin_mutation_denied_for_consultant(self):
        ctx = _resolved_ctx(role=CONSULTANT)
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_require_role_carries_request_ref(self):
        ctx = _resolved_ctx(role=CONSULTANT, request_ref="req_custom_abc")
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})
        assert excinfo.value.request_ref == "req_custom_abc"
