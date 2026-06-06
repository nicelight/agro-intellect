from __future__ import annotations

from backend.app.publication import redact_bus_event, redact_message_envelope, redact_ui_feed_event


class TestBusRedaction:
    def test_redacts_secret_like_content(self):
        event = {
            "event_type": "observation",
            "payload": {"api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
            "topic": "plant.update",
        }
        result = redact_bus_event(event)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["topic"] == "plant.update"

    def test_preserves_non_sensitive_fields(self):
        event = {
            "event_type": "plant_watered",
            "topic": "plant.update",
            "payload": {"plant_id": "plant_001", "amount_ml": 500},
        }
        result = redact_bus_event(event)
        assert result.status == "no_sensitive_fields"
        assert result.value["topic"] == "plant.update"


class TestMessageEnvelopeRedaction:
    def test_redacts_secret_like_content(self):
        envelope = {
            "message_id": "msg_001",
            "consumable_output": "the key is sk-ant-abcdefghijklmnopqrstuvwxyz123456",
            "agent_id": "companion",
        }
        result = redact_message_envelope(envelope)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["agent_id"] == "companion"

    def test_preserves_non_sensitive_fields(self):
        envelope = {
            "message_id": "msg_002",
            "consumable_output": "plant measurement is 6.5 pH",
            "agent_id": "companion",
        }
        result = redact_message_envelope(envelope)
        assert result.status == "no_sensitive_fields"


class TestUIFeedRedaction:
    def test_redacts_secret_like_content(self):
        event = {
            "ui_event_id": "ui_001",
            "display_payload": {"text": "token is sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
            "presentation_kind": "message",
        }
        result = redact_ui_feed_event(event)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)

    def test_preserves_non_sensitive_fields(self):
        event = {
            "ui_event_id": "ui_002",
            "display_payload": {"text": "plant watered successfully"},
            "presentation_kind": "message",
        }
        result = redact_ui_feed_event(event)
        assert result.status == "no_sensitive_fields"
