from __future__ import annotations

from backend.app.export import redact_export_payload


class TestExportRedaction:
    def test_redacts_secret_like_content(self):
        payload = {
            "export_type": "photo_manifest",
            "photo_id": "photo_001",
            "metadata": {"api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456"},
        }
        result = redact_export_payload(payload)
        assert result.status == "redacted"
        assert "sk-ant-abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert result.value["export_type"] == "photo_manifest"

    def test_preserves_non_sensitive_fields(self):
        payload = {
            "export_type": "plant_report",
            "plant_id": "plant_001",
            "measurements": {"ph": 6.5, "ec": 1.2},
        }
        result = redact_export_payload(payload)
        assert result.status == "no_sensitive_fields"
        assert result.value["export_type"] == "plant_report"

    def test_handles_high_risk_rejection(self):
        payload = {
            "export_type": "key_backup",
            "body": "-----BEGIN PRIVATE KEY-----\npartial-secret-body",
        }
        result = redact_export_payload(payload)
        assert result.status in ("rejected", "truncated", "redacted")

    def test_redacts_sensitive_keys_in_payload(self):
        payload = {
            "export_type": "config",
            "session_id": "session_abcdefghijklmnopqrstuvwxyz123456",
            "refresh_token": "refresh-token-1234567890abcdef",
        }
        result = redact_export_payload(payload)
        assert result.status == "redacted"
        assert "session_abcdefghijklmnopqrstuvwxyz123456" not in str(result.value)
        assert "refresh-token-1234567890abcdef" not in str(result.value)
