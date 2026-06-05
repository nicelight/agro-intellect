from __future__ import annotations

from backend.app.security import (
    AUTH_MATERIAL_REDACTION_MARKER,
    redact_auth_payload,
    redact_secret_payload,
    redact_secret_text,
)


def test_security_redaction_exports_route_full_policy_through_privacy_foundation():
    raw_provider_key = "sk-abcdefghijklmnopqrstuvwxyz1234567890"

    result = redact_secret_payload(
        {
            "message": f"provider configured with {raw_provider_key}",
            "request_ref": "req_ref_1234567890abcdef",
        }
    )

    assert result.status == "redacted"
    assert raw_provider_key not in str(result.value)
    assert result.value["request_ref"] == "req_ref_1234567890abcdef"
    assert result.findings[0].secret_type == "api_key"


def test_security_text_redaction_export_supports_high_risk_fail_closed():
    raw_payload = "-----BEGIN PRIVATE KEY-----\nnot-enough-key-material"

    result = redact_secret_text(raw_payload, high_risk=True)

    assert result.status == "rejected"
    assert result.action == "reject"
    assert result.value is None


def test_narrow_auth_redaction_helper_remains_task001_compatible():
    raw_session_secret = "session-secret-with-enough-entropy-abcdef123456"
    payload = {
        "message": f"login used {raw_session_secret}",
        "session_token": raw_session_secret,
        "safe_ref": "sess_ref_1234567890abcdef",
    }

    redacted = redact_auth_payload(payload, sensitive_values=(raw_session_secret,))

    assert redacted["session_token"] == AUTH_MATERIAL_REDACTION_MARKER
    assert raw_session_secret not in str(redacted)
    assert redacted["safe_ref"] == "sess_ref_1234567890abcdef"
