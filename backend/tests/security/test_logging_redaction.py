from __future__ import annotations

from backend.app.logging import RedactLogger, get_logger
from backend.app.privacy import redact_text


class TestRedactLogger:
    def test_info_redacts_secret_text(self, capsys):
        logger = RedactLogger("test")
        secret = "sk-ant-abcdefghijklmnopqrstuvwxyz123456"
        logger.info(f"user key is {secret}")
        captured = capsys.readouterr()
        assert secret not in captured.out
        assert "[REDACTED_API_KEY" in captured.out
        assert "[test] INFO:" in captured.out

    def test_error_redacts_secret_text(self, capsys):
        logger = RedactLogger("test")
        secret = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        logger.error(f"token leaked: {secret}")
        captured = capsys.readouterr()
        assert secret not in captured.out
        assert "[REDACTED_CONNECTOR_SECRET" in captured.out
        assert "[test] ERROR:" in captured.out

    def test_high_risk_uncertain_payload_is_rejected(self, capsys):
        logger = RedactLogger("test")
        payload = "connector output:\n-----BEGIN PRIVATE KEY-----\npartial-secret-body"
        logger.info(payload)
        captured = capsys.readouterr()
        assert "partial-secret-body" not in captured.out

    def test_get_logger_returns_singleton(self):
        logger_a = get_logger("test")
        logger_b = get_logger("test")
        assert logger_a is logger_b

    def test_get_logger_default_name(self):
        logger = get_logger()
        assert logger._name == "agro"
