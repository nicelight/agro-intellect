from __future__ import annotations

import os
import subprocess
from pathlib import Path

from backend.app.config import AppSettings
from backend.app.core.redaction import (
    REDACTION,
    is_sensitive_key,
    redact_mapping,
    redact_text,
    redact_url_credentials,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_redact_text_masks_secret_assignments_urls_and_auth_material():
    text = (
        "DATABASE_URL=postgresql+psycopg://postgres:secret@localhost/app "
        "API_TOKEN=token-value Authorization: Bearer auth-token "
        "url=postgresql://worker:worker-secret@localhost/db"
    )

    redacted = redact_text(text)

    assert "secret" not in redacted
    assert "token-value" not in redacted
    assert "auth-token" not in redacted
    assert "worker-secret" not in redacted
    assert "DATABASE_URL=***" in redacted
    assert "API_TOKEN=***" in redacted
    assert "Authorization: ***" in redacted
    assert "postgresql://worker:***@localhost/db" in redacted


def test_redact_text_masks_sensitive_values_from_env_mapping():
    redacted = redact_text(
        "connection failed for password swordfish",
        environ={"APP_PASSWORD": "swordfish", "APP_ENV": "local"},
    )

    assert "swordfish" not in redacted
    assert REDACTION in redacted


def test_redact_mapping_preserves_safe_values_and_masks_secret_keys():
    mapping = {
        "APP_ENV": "local",
        "DATABASE_URL": "postgresql+psycopg://postgres:secret@localhost/app",
        "LOCAL_DATA_ROOT": "data",
    }

    redacted = redact_mapping(mapping)

    assert redacted["APP_ENV"] == "local"
    assert redacted["LOCAL_DATA_ROOT"] == "data"
    assert redacted["DATABASE_URL"] == REDACTION


def test_redact_url_credentials_keeps_username_and_masks_password():
    redacted = redact_url_credentials(
        "postgresql+psycopg://postgres:secret@localhost/agro_intellect"
    )

    assert redacted == "postgresql+psycopg://postgres:***@localhost/agro_intellect"
    assert "secret" not in redacted


def test_sensitive_key_classifier_covers_foundation_secret_terms():
    for key in [
        "DATABASE_URL",
        "API_TOKEN",
        "ACCESS_TOKEN",
        "APP_PASSWORD",
        "PRIVATE_KEY",
        "AUTHORIZATION",
    ]:
        assert is_sensitive_key(key)

    assert not is_sensitive_key("LOCAL_DATA_ROOT")
    assert not is_sensitive_key("APP_ENV")


def test_app_settings_redacted_for_log_hides_database_password():
    settings = AppSettings(
        database_url="postgresql+psycopg://postgres:secret@localhost/agro_intellect"
    )

    summary = settings.redacted_for_log()

    assert summary["database_url"] == (
        "postgresql+psycopg://postgres:***@localhost/agro_intellect"
    )
    assert "secret" not in " ".join(summary.values())
    assert summary["sync_status"] == "local_only"


def test_foundation_scripts_redact_secret_bearing_unsupported_arguments():
    for script in [
        "scripts/bootstrap-local.sh",
        "scripts/db-init-local.sh",
        "scripts/db-migrate-local.sh",
    ]:
        result = subprocess.run(
            ["bash", script, "--api-token=super-secret"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        output = result.stdout + result.stderr

        assert result.returncode == 2
        assert "super-secret" not in output
        assert "--api-token=***" in output


def test_database_dry_run_output_redacts_environment_database_url():
    env = os.environ.copy()
    env["DATABASE_URL"] = (
        "postgresql+psycopg://postgres:super-secret@localhost/agro_intellect"
    )

    result = subprocess.run(
        ["bash", "scripts/db-init-local.sh", "--dry-run"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "super-secret" not in output
    assert "postgres:***@" in output
    assert "DATABASE_URL=" not in output


def test_foundation_scripts_route_messages_through_redaction_helper():
    for script in [
        PROJECT_ROOT / "scripts" / "bootstrap-local.sh",
        PROJECT_ROOT / "scripts" / "db-init-local.sh",
        PROJECT_ROOT / "scripts" / "db-migrate-local.sh",
    ]:
        text = script.read_text(encoding="utf-8")

        assert "redact()" in text
        assert "$(redact" in text
        assert "set -x" not in text
        assert "cat .env" not in text
