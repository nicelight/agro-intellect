from __future__ import annotations

from backend.app.privacy import redact_payload


class TestSecurityTracesRedaction:
    def test_trace_auth_provenance_ref_preserved(self):
        trace = {
            "event": "auth_check",
            "auth_provenance_ref": "auth_ref_abc123def456",
            "request_ref": "req_test_001",
        }
        result = redact_payload(trace)
        assert result.status == "no_sensitive_fields"
        assert result.value["auth_provenance_ref"] == "auth_ref_abc123def456"
        assert result.value["request_ref"] == "req_test_001"

    def test_trace_raw_session_secret_redacted(self):
        trace = {
            "event": "session_created",
            "session_secret": "raw-session-secret-value-1234567890abcdef",
        }
        result = redact_payload(trace)
        assert result.status == "redacted"
        serialized = str(result.value)
        assert "raw-session-secret-value-1234567890abcdef" not in serialized

    def test_trace_api_key_redacted(self):
        trace = {
            "event": "provider_call",
            "api_key": "sk-ant-trace-test-key-1234567890abcdefghij",
        }
        result = redact_payload(trace)
        assert result.status == "redacted"
        assert "sk-ant-trace-test-key-1234567890abcdefghij" not in str(result.value)

    def test_trace_mixed_safe_unsafe_fields(self):
        trace = {
            "event": "tool_execution",
            "tool": "view_plant",
            "plant_id": "tomato_001",
            "duration_ms": 42,
            "api_key": "sk-ant-mixed-key-1234567890abcdefghijklmnop",
            "session_secret": "mixed-session-secret-1234567890abcdef",
        }
        result = redact_payload(trace)
        serialized = str(result.value)
        assert result.status == "redacted"
        assert "sk-ant-mixed-key-1234567890abcdefghijklmnop" not in serialized
        assert "mixed-session-secret-1234567890abcdef" not in serialized
        assert "view_plant" in serialized
        assert "tomato_001" in serialized
        assert "duration_ms" in serialized
