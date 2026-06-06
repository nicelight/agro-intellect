"""Unit tests for role-based authorization helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.access.authorization import (
    BOSS,
    CONSULTANT,
    ENGINEER,
    get_role_permissions,
    has_admin_authority,
    require_boss,
    require_engineer_or_boss,
    require_role,
)
from backend.app.api.errors import AppError, ErrorCode
from backend.app.context.models import ActorContext, ActorContextState

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


def _ctx(role: str | None = None, request_ref: str | None = "req_test") -> ActorContext:
    return ActorContext(
        state=ActorContextState.RESOLVED,
        account_id="acct_test",
        farm_id="farm_local",
        membership_id="mbr_test",
        role=role,
        membership_status="active",
        session_ref="sess_ref_abc123",
        auth_provenance_ref="auth_ref_def456",
        request_ref=request_ref,
        resolved_at=NOW,
    )


class TestRequireBoss:
    def test_boss_role_passes(self):
        ctx = _ctx(role=BOSS)
        require_boss(ctx)

    def test_engineer_role_fails(self):
        ctx = _ctx(role=ENGINEER)
        with pytest.raises(AppError) as excinfo:
            require_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_consultant_role_fails(self):
        ctx = _ctx(role=CONSULTANT)
        with pytest.raises(AppError) as excinfo:
            require_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_none_role_fails(self):
        ctx = _ctx(role=None)
        with pytest.raises(AppError) as excinfo:
            require_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED


class TestRequireEngineerOrBoss:
    def test_boss_role_passes(self):
        ctx = _ctx(role=BOSS)
        require_engineer_or_boss(ctx)

    def test_engineer_role_passes(self):
        ctx = _ctx(role=ENGINEER)
        require_engineer_or_boss(ctx)

    def test_consultant_role_fails(self):
        ctx = _ctx(role=CONSULTANT)
        with pytest.raises(AppError) as excinfo:
            require_engineer_or_boss(ctx)
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED


class TestRequireRole:
    def test_role_in_allowed_set_passes(self):
        ctx = _ctx(role=BOSS)
        require_role(ctx, {BOSS, ENGINEER})

    def test_role_not_in_allowed_set_fails(self):
        ctx = _ctx(role=CONSULTANT)
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})
        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_error_has_safe_envelope_no_secrets(self):
        ctx = _ctx(role=CONSULTANT, request_ref="req_ref_safe_test")
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
        assert excinfo.value.message is not None
        assert excinfo.value.request_ref == "req_ref_safe_test"
        assert excinfo.value.next_actions is not None

        # No raw session/token/auth material in the error envelope
        assert "raw_secret" not in str(excinfo.value.details)
        assert "Bearer" not in str(excinfo.value.details)
        assert "authorization" not in str(excinfo.value.details).lower()

    def test_error_does_not_leak_existence_hints(self):
        ctx = _ctx(role=ENGINEER, request_ref="req_ref_exist")
        with pytest.raises(AppError) as excinfo:
            require_role(ctx, {BOSS})

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED
        message = excinfo.value.message.lower()
        assert "engineer" not in message
        assert "consultant" not in message
        assert "boss" not in message  # Generic message, no specific role name


class TestHasAdminAuthority:
    def test_boss_returns_true(self):
        assert has_admin_authority(BOSS) is True

    def test_engineer_returns_false(self):
        assert has_admin_authority(ENGINEER) is False

    def test_consultant_returns_false(self):
        assert has_admin_authority(CONSULTANT) is False

    def test_unknown_role_returns_false(self):
        assert has_admin_authority("unknown_role") is False

    def test_none_returns_false(self):
        assert has_admin_authority(None) is False  # type: ignore[arg-type]


class TestGetRolePermissions:
    def test_boss_has_manage_accounts(self):
        perms = get_role_permissions(BOSS)
        assert perms.get("manage_accounts") is True
        assert perms.get("manage_memberships") is True
        assert perms.get("manage_roles") is True
        assert perms.get("manage_plants") is True
        assert perms.get("manage_plant_access") is True
        assert perms.get("view_admin_audit") is True

    def test_engineer_has_no_admin_permissions(self):
        perms = get_role_permissions(ENGINEER)
        assert perms.get("manage_accounts") is False
        assert perms.get("manage_memberships") is False
        assert perms.get("manage_roles") is False
        assert perms.get("manage_plants") is False
        assert perms.get("manage_plant_access") is False
        assert perms.get("view_admin_audit") is False

    def test_consultant_has_no_admin_permissions(self):
        perms = get_role_permissions(CONSULTANT)
        assert perms.get("manage_accounts") is False
        assert perms.get("manage_memberships") is False
        assert perms.get("manage_roles") is False
        assert perms.get("manage_plants") is False
        assert perms.get("manage_plant_access") is False
        assert perms.get("view_admin_audit") is False

    def test_unknown_role_returns_empty_dict(self):
        perms = get_role_permissions("nonexistent")
        assert perms == {}

    def test_permissions_return_copy_not_reference(self):
        perms = get_role_permissions(BOSS)
        perms["manage_accounts"] = False
        assert get_role_permissions(BOSS)["manage_accounts"] is True
