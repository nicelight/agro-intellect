from __future__ import annotations

from backend.app.export import redact_export_payload
from backend.app.harness import ObservationWriter
from backend.app.logging import RedactLogger
from backend.app.publication import redact_bus_event, redact_message_envelope, redact_ui_feed_event
from backend.app.timeline import redact_timeline_entry

SECRET_VALUE = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"


class TestForbiddenSurfaceRedactionChain:
    def setup_method(self):
        self.writer = ObservationWriter()

    def _assert_secret_redacted(self, result, surface_name: str):
        serialized = str(result.value) if result.value is not None else ""
        assert SECRET_VALUE not in serialized, f"{surface_name} leaked secret"
        assert result.status in ("redacted", "rejected", "truncated"), (
            f"{surface_name} did not redact/reject/truncate"
        )

    def test_logging_surface(self, capsys):
        logger = RedactLogger("test")
        logger.info(f"secret is {SECRET_VALUE}")
        captured = capsys.readouterr()
        assert SECRET_VALUE not in captured.out
        assert "[REDACTED_API_KEY" in captured.out

    def test_timeline_surface(self):
        entry = {"event": "test", "api_key": SECRET_VALUE}
        result = redact_timeline_entry(entry)
        self._assert_secret_redacted(result, "timeline")
        assert result.value["event"] == "test"

    def test_export_surface(self):
        payload = {"export_type": "test", "credentials": {"api_key": SECRET_VALUE}}
        result = redact_export_payload(payload)
        self._assert_secret_redacted(result, "export")

    def test_bus_event_surface(self):
        event = {"event_type": "test", "payload": {"api_key": SECRET_VALUE}}
        result = redact_bus_event(event)
        self._assert_secret_redacted(result, "bus_event")

    def test_message_envelope_surface(self):
        envelope = {"message_id": "m1", "consumable_output": f"key is {SECRET_VALUE}"}
        result = redact_message_envelope(envelope)
        self._assert_secret_redacted(result, "message_envelope")

    def test_ui_feed_surface(self):
        event = {"ui_event_id": "u1", "display_payload": {"text": f"key is {SECRET_VALUE}"}}
        result = redact_ui_feed_event(event)
        self._assert_secret_redacted(result, "ui_feed")

    def test_harness_observation_surface(self):
        observation = {
            "status": "success",
            "type": "tool_call",
            "summary": f"api call with {SECRET_VALUE}",
        }
        result = self.writer.record_observation(observation)
        self._assert_secret_redacted(result, "harness_observation")

    def test_harness_trace_surface(self):
        trace = {"event": "tool_execution", "args": {"api_key": SECRET_VALUE}}
        result = self.writer.record_trace(trace)
        self._assert_secret_redacted(result, "harness_trace")
