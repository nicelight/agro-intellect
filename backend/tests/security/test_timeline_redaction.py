from __future__ import annotations

from backend.app.timeline import redact_timeline_entry


class TestTimelineRedaction:
    def test_redacts_secret_like_dict_content(self):
        entry = {
            "event": "login",
            "session_id": "session_abcdefghijklmnopqrstuvwxyz123456",
            "safe_field": "user logged in",
        }
        result = redact_timeline_entry(entry)
        assert result.status == "redacted"
        serialized = str(result.value)
        assert "session_abcdefghijklmnopqrstuvwxyz123456" not in serialized
        assert result.value["safe_field"] == "user logged in"

    def test_preserves_non_sensitive_fields(self):
        entry = {
            "event": "plant_watered",
            "plant_id": "plant_001",
            "amount_ml": 500,
        }
        result = redact_timeline_entry(entry)
        assert result.status == "no_sensitive_fields"
        assert result.value["event"] == "plant_watered"
        assert result.value["plant_id"] == "plant_001"
        assert result.value["amount_ml"] == 500

    def test_redacts_nested_secret_like_content(self):
        entry = {
            "event": "provider_call",
            "metadata": {"api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
            "tags": ["important"],
        }
        result = redact_timeline_entry(entry)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["tags"] == ["important"]

    def test_high_risk_uncertain_rejected(self):
        entry = {
            "event": "incomplete_key",
            "detail": "-----BEGIN PRIVATE KEY-----\npartial-secret-body",
        }
        result = redact_timeline_entry(entry)
        assert result.status in ("rejected", "truncated", "redacted")
