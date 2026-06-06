"""Tests for the PermissionEngine."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.api.errors import AppError, ErrorCode
from backend.app.context import ActorContext, ActorContextState, PermissionAwareContextBuilder
from backend.app.harness.models import PermissionVerdict
from backend.app.harness.permission import PermissionEngine

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


class StubContextBuilder:
    def build_context(self, actor_context, request_ref=None):
        return None

    def authorize_plant_access(self, actor_context, plant_id):
        pass


def make_resolved_ctx(**kwargs) -> ActorContext:
    return ActorContext(
        state=ActorContextState.RESOLVED,
        account_id="acct_001",
        farm_id="farm_local",
        membership_id="mbr_001",
        role="boss",
        membership_status="active",
        session_ref="sess_ref_abc",
        auth_provenance_ref="auth_ref_abc",
        request_ref="req_test",
        resolved_at=NOW,
        **kwargs,
    )


def make_denied_ctx(**kwargs) -> ActorContext:
    return ActorContext(
        state=ActorContextState.DENIED,
        session_ref="sess_ref_denied",
        auth_provenance_ref="auth_ref_denied",
        request_ref="req_test",
        resolved_at=NOW,
        **kwargs,
    )


def make_expired_ctx(**kwargs) -> ActorContext:
    return ActorContext(
        state=ActorContextState.EXPIRED,
        session_ref="sess_ref_expired",
        auth_provenance_ref="auth_ref_expired",
        request_ref="req_test",
        resolved_at=NOW,
        **kwargs,
    )


class TestPermissionEngine:
    def setup_method(self):
        stub_builder = StubContextBuilder()
        self.engine = PermissionEngine(stub_builder)

    def test_authorize_run_resolved_returns_allow(self):
        ctx = make_resolved_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")

        assert decision.verdict is PermissionVerdict.ALLOW
        assert decision.reason
        assert decision.actor_context_ref == ctx.session_ref

    def test_authorize_run_denied_returns_deny(self):
        ctx = make_denied_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")

        assert decision.verdict is PermissionVerdict.DENY
        assert "denied" in decision.reason.lower()

    def test_authorize_run_expired_returns_deny(self):
        ctx = make_expired_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")

        assert decision.verdict is PermissionVerdict.DENY
        assert "expired" in decision.reason.lower()

    def test_authorize_tool_resolved_returns_allow(self):
        ctx = make_resolved_ctx()
        decision = self.engine.authorize_tool(ctx, "view_plant", {"plant_id": "plant_a"})

        assert decision.verdict is PermissionVerdict.ALLOW
        assert decision.reason

    def test_authorize_tool_denied_returns_deny(self):
        ctx = make_denied_ctx()
        decision = self.engine.authorize_tool(ctx, "view_plant", {"plant_id": "plant_a"})

        assert decision.verdict is PermissionVerdict.DENY

    def test_authorize_tool_expired_returns_deny(self):
        ctx = make_expired_ctx()
        decision = self.engine.authorize_tool(ctx, "view_plant", {"plant_id": "plant_a"})

        assert decision.verdict is PermissionVerdict.DENY

    def test_require_resolved_context_denied_raises(self):
        ctx = make_denied_ctx()

        with pytest.raises(AppError) as excinfo:
            self.engine.require_resolved_context(ctx)

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_require_resolved_context_expired_raises(self):
        ctx = make_expired_ctx()

        with pytest.raises(AppError) as excinfo:
            self.engine.require_resolved_context(ctx)

        assert excinfo.value.code is ErrorCode.PERMISSION_DENIED

    def test_require_resolved_context_resolved_passes(self):
        ctx = make_resolved_ctx()
        self.engine.require_resolved_context(ctx)

    def test_permission_decision_contains_safe_reason_no_secrets(self):
        ctx = make_denied_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")

        assert decision.reason
        assert "denied" in decision.reason.lower()
        assert "secret" not in decision.reason.lower()

    def test_decision_has_decided_at(self):
        ctx = make_resolved_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")

        assert decision.decided_at is not None
        assert isinstance(decision.decided_at, datetime)
