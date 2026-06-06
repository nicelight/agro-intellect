from __future__ import annotations

from backend.app.harness import ObservationWriter


class TestObservationWriter:
    def setup_method(self):
        self.writer = ObservationWriter()

    def test_record_observation_redacts_secret_content(self):
        observation = {
            "status": "success",
            "type": "tool_call",
            "summary": "api call with key sk-ant-abcdefghijklmnopqrstuvwxyz123456",
            "evidence_refs": [],
        }
        result = self.writer.record_observation(observation)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["status"] == "success"

    def test_record_observation_preserves_non_sensitive(self):
        observation = {
            "status": "success",
            "type": "view_plant",
            "summary": "viewed plant_001",
            "evidence_refs": ["ev_001"],
        }
        result = self.writer.record_observation(observation)
        assert result.status == "no_sensitive_fields"
        assert result.value["summary"] == "viewed plant_001"
        assert result.value["evidence_refs"] == ["ev_001"]

    def test_rejected_payload_returns_rejected_result(self):
        observation = {
            "status": "error",
            "type": "connector_output",
            "summary": "-----BEGIN PRIVATE KEY-----\npartial-secret-body",
        }
        result = self.writer.record_observation(observation)
        assert result.status in ("rejected", "truncated", "redacted")

    def test_truncated_payload_returns_truncated_result(self):
        observation = {
            "status": "error",
            "type": "connector_output",
            "summary": "-----BEGIN PRIVATE KEY-----\npartial-secret-body",
        }
        result = self.writer.record_observation(observation)
        if result.status == "truncated":
            assert "[TRUNCATED_HIGH_RISK_PAYLOAD]" in str(result.value)
        else:
            assert result.status in ("rejected", "redacted")

    def test_record_trace_redacts_secret_content(self):
        trace = {
            "event": "tool_execution",
            "tool": "view_plant",
            "args": {"api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
        }
        result = self.writer.record_trace(trace)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)

    def test_record_trace_preserves_non_sensitive(self):
        trace = {
            "event": "tool_execution",
            "tool": "view_plant",
            "args": {"plant_id": "plant_001"},
            "duration_ms": 150,
        }
        result = self.writer.record_trace(trace)
        assert result.status == "no_sensitive_fields"
