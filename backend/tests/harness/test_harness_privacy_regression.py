from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.api.errors import AppError, ErrorCode
from backend.app.context import (
    ActorContext,
    ActorContextState,
    ContextPackage,
    PermissionAwareContextBuilder,
)
from backend.app.harness import ObservationWriter, PermissionEngine
from backend.app.harness.models import PermissionVerdict


NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


class StubRepo:
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


class TestPermissionEnginePrivacy:
    def setup_method(self):
        stub_builder = object()
        self.engine = PermissionEngine(stub_builder)

    def test_authorize_run_resolved_allow_no_secrets_in_reason(self):
        ctx = make_resolved_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")
        assert decision.verdict is PermissionVerdict.ALLOW
        assert "secret" not in decision.reason.lower()
        assert "sk-ant" not in decision.reason

    def test_authorize_run_denied_safe_reason(self):
        ctx = make_denied_ctx()
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")
        assert decision.verdict is PermissionVerdict.DENY
        assert decision.reason
        assert "secret" not in decision.reason.lower()
        assert "sk-ant" not in decision.reason

    def test_authorize_run_expired_safe_reason(self):
        ctx = ActorContext(
            state=ActorContextState.EXPIRED,
            session_ref="sess_ref_expired",
            auth_provenance_ref="auth_ref_expired",
            request_ref="req_test",
            resolved_at=NOW,
        )
        decision = self.engine.authorize_run(ctx, "agent_companion", "req_001")
        assert decision.verdict is PermissionVerdict.DENY
        assert "expired" in decision.reason.lower()
        assert "secret" not in decision.reason.lower()


class TestObservationWriterPrivacy:
    def setup_method(self):
        self.writer = ObservationWriter()

    def test_record_observation_with_secret_redacted(self):
        obs = {
            "status": "success",
            "type": "tool_call",
            "summary": "called api with key sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        }
        result = self.writer.record_observation(obs)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["status"] == "success"

    def test_record_observation_no_secrets_preserved(self):
        obs = {
            "status": "success",
            "type": "view_plant",
            "summary": "viewed plant_001",
        }
        result = self.writer.record_observation(obs)
        assert result.status == "no_sensitive_fields"
        assert result.value["summary"] == "viewed plant_001"

    def test_record_trace_with_secret_redacted(self):
        trace = {
            "event": "tool_execution",
            "tool": "view_plant",
            "args": {"api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
        }
        result = self.writer.record_trace(trace)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)

    def test_record_trace_no_secrets_preserved(self):
        trace = {
            "event": "tool_execution",
            "tool": "view_plant",
            "args": {"plant_id": "plant_001"},
            "duration_ms": 150,
        }
        result = self.writer.record_trace(trace)
        assert result.status == "no_sensitive_fields"

    def test_high_risk_uncertain_payload_rejected_or_truncated(self):
        obs = {
            "status": "error",
            "type": "connector_output",
            "summary": "-----BEGIN PRIVATE KEY-----\npartial-secret-body",
        }
        result = self.writer.record_observation(obs)
        assert result.status in ("rejected", "truncated")


class TestPermissionAwareContextBuilderPrivacy:
    def setup_method(self):
        self.builder = PermissionAwareContextBuilder(StubRepo())

    def test_build_context_resolved_returns_package_no_secrets(self):
        ctx = make_resolved_ctx()
        package = self.builder.build_context(ctx, request_ref="req_test")
        assert isinstance(package, ContextPackage)
        assert package.farm_id == "farm_local"
        assert package.role == "boss"
        serialized = str(package)
        assert "sk-ant" not in serialized
        assert "secret" not in serialized.lower()

    def test_build_context_denied_raises_app_error(self):
        ctx = make_denied_ctx()
        with pytest.raises(AppError) as exc:
            self.builder.build_context(ctx, request_ref="req_test")
        assert exc.value.code is ErrorCode.PERMISSION_DENIED
        safe_msg = exc.value.message
        assert "secret" not in safe_msg.lower()
        assert "sk-ant" not in safe_msg
