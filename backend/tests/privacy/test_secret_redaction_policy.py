from __future__ import annotations

import re

from backend.app.privacy import RedactionPolicy, redact_payload, redact_text


def test_secret_redaction_policy_covers_known_secret_classes():
    secrets = {
        "session_id": "session_1234567890abcdef1234567890abcdef",
        "csrf_token": "csrf-token-1234567890abcdef",
        "refresh_token": "refresh-token-1234567890abcdef",
        "reset_token": "reset-token-1234567890abcdef",
        "api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz123456",
        "env_key": "sk-env-abcdefghijklmnopqrstuvwxyz123456",
        "db_password": "db-password-1234567890abcdef",
        "connector_secret": "connector-secret-1234567890abcdef",
        "webhook_secret": "whsec_1234567890abcdef1234567890abcdef",
        "cookie_sid": "sid-secret-1234567890abcdef",
        "bearer": "bearer-secret-1234567890abcdef",
        "private_key": "synthetic-private-key-body",
    }
    payload = {
        "safe_message": "connect to the local demo database during bootstrap",
        "session_id": secrets["session_id"],
        "csrf_token": secrets["csrf_token"],
        "refresh_token": secrets["refresh_token"],
        "reset_token": secrets["reset_token"],
        "connector_secret": secrets["connector_secret"],
        "database": (
            "DATABASE_URL=postgresql://agro:"
            f"{secrets['db_password']}@db.local:5432/agro"
        ),
        "headers": (
            f"Authorization: Bearer {secrets['bearer']}\n"
            f"Cookie: sid={secrets['cookie_sid']}; theme=light"
        ),
        "provider": f"model key is {secrets['api_key']}",
        "env": f"OPENAI_API_KEY={secrets['env_key']}",
        "webhook_url": f"https://hooks.local/run?webhook_secret={secrets['webhook_secret']}",
        "private_key": (
            "-----BEGIN PRIVATE KEY-----\n"
            f"{secrets['private_key']}\n"
            "-----END PRIVATE KEY-----"
        ),
        "safe_ref": "sess_ref_1234567890abcdef",
    }

    result = redact_payload(payload)
    serialized = str(result.value)

    assert result.status == "redacted"
    for raw_secret in secrets.values():
        assert raw_secret not in serialized
        assert raw_secret not in str(result.findings)
    assert "local demo database" in result.value["safe_message"]
    assert "postgresql://agro:" in result.value["database"]
    assert "@db.local:5432/agro" in result.value["database"]
    assert result.value["safe_ref"] == "sess_ref_1234567890abcdef"
    assert {finding.secret_type for finding in result.findings} >= {
        "api_key",
        "connector_secret",
        "cookie",
        "csrf_token",
        "database_credential",
        "private_key",
        "refresh_token",
        "reset_token",
        "session_id",
        "token",
        "webhook_secret",
    }


def test_secret_redaction_policy_handles_configured_secret_like_user_text():
    policy = RedactionPolicy(
        configured_secret_values=("grow-room-passphrase",),
        configured_secret_patterns=(re.compile(r"user secret (?P<secret>[A-Z0-9]{8})"),),
    )

    result = redact_text(
        "note says grow-room-passphrase and user secret ABCD1234; keep plant note",
        policy=policy,
    )

    assert result.status == "redacted"
    assert "grow-room-passphrase" not in result.value
    assert "ABCD1234" not in result.value
    assert "keep plant note" in result.value
    assert all("grow-room-passphrase" not in str(finding) for finding in result.findings)
    assert {finding.detector for finding in result.findings} == {
        "configured_pattern",
        "configured_value",
    }


def test_secret_redaction_policy_uses_stable_non_reversible_refs():
    raw_secret = "repeatable-secret-1234567890abcdef"
    first = redact_payload({"api_key": raw_secret})
    second = redact_payload({"api_key": raw_secret})

    assert first.value == second.value
    assert first.findings[0].ref == second.findings[0].ref
    assert raw_secret not in first.findings[0].ref
    assert raw_secret not in first.value["api_key"]


def test_secret_redaction_policy_rejects_uncertain_high_risk_payload():
    payload = "connector output:\n-----BEGIN PRIVATE KEY-----\npartial-secret-body"

    result = redact_text(payload, high_risk=True, uncertain_strategy="reject")

    assert result.status == "rejected"
    assert result.action == "reject"
    assert result.value is None
    assert result.reason == "incomplete_private_key_material"


def test_secret_redaction_policy_truncates_uncertain_high_risk_payload():
    payload = "connector output:\n-----BEGIN PRIVATE KEY-----\npartial-secret-body"

    result = redact_text(payload, high_risk=True, uncertain_strategy="truncate")

    assert result.status == "truncated"
    assert result.action == "truncate"
    assert result.value.startswith("[TRUNCATED_HIGH_RISK_PAYLOAD]:redacted_payload_")
    assert "partial-secret-body" not in result.value
