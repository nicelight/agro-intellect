from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.config.deployment import DeploymentConfig, DeploymentMode
from backend.app.privacy import redact_payload, redact_text
from backend.app.privacy.storage_prompt import validate_storage_prompt
from backend.app.security.cors_origin import validate_cors_origin


class TestFullFlowNoSecretsLeak:
    def test_create_app_session_flow_no_secrets(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/auth/me")
        data = resp.json()
        serialized = str(data)
        assert "sk-ant-" not in serialized
        assert "bearer" not in serialized.lower()
        assert "secret" not in serialized.lower()

    def test_loopback_app_no_cors_middleware(self):
        app = create_app()
        has_cors = any(
            type(m).__name__ == "CORSMiddleware"
            for m in app.user_middleware
        )
        assert not has_cors

    def test_loopback_with_lan_config_does_not_add_cors(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LOOPBACK,
            allowed_origins=("http://192.168.1.100:5173",),
        )
        app = create_app(cfg)
        has_cors = any(
            type(m).__name__ == "CORSMiddleware"
            for m in app.user_middleware
        )
        assert not has_cors

    def test_validate_cors_origin_loopback_origin_not_accepted(self):
        assert not validate_cors_origin(
            "http://192.168.1.100:5173",
            ("http://localhost:5173",),
        )


class TestStoragePromptValidation:
    def test_storage_prompt_rejects_upload_language(self):
        result = validate_storage_prompt(
            "Your data is stored locally. Upload to cloud for backup."
        )
        assert result.verdict == "fail"

    def test_storage_prompt_allows_local_only_language(self):
        result = validate_storage_prompt(
            "Your data is stored locally on this device."
        )
        assert result.verdict == "pass"

    def test_storage_prompt_rejects_server_sync_reference(self):
        result = validate_storage_prompt(
            "Sync your data to the remote server."
        )
        assert result.verdict == "fail"


class TestRedactPayloadRegression:
    def test_redact_payload_removes_secrets_keeps_safe(self):
        payload = {
            "message": "Plant moisture level is 42%",
            "api_key": "sk-ant-test-key-1234567890abcdefghijklmn",
            "plant_id": "tomato_001",
            "credentials": {"password": "supersecret123"},
        }
        result = redact_payload(payload)
        serialized = str(result.value)
        assert result.status == "redacted"
        assert "sk-ant-test-key-1234567890abcdefghijklmn" not in serialized
        assert "supersecret123" not in serialized
        assert "Plant moisture level is 42%" in serialized
        assert "tomato_001" in serialized

    def test_redact_text_removes_tokens(self):
        log_line = (
            "Request received with "
            "Authorization: Bearer tok_abcdefghijklmnopqrstuvwxyz1234567890 "
            "and session_secret=abcdefghijklmnopqrstuvwxyz1234567890abcdef"
        )
        result = redact_text(log_line)
        assert result.status == "redacted"
        serialized = str(result.value)
        assert "tok_abcdefghijklmnopqrstuvwxyz1234567890" not in serialized
        assert "abcdefghijklmnopqrstuvwxyz1234567890abcdef" not in serialized
        assert "Request received" in serialized
