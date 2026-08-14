from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("raw", "forbidden"),
    [
        ("postgresql+psycopg://postgres:ab/cd@dbhost/agro_intellect", ["ab/cd"]),
        ("postgresql+psycopg://postgres:ab cd@dbhost/agro_intellect", ["ab cd"]),
        ("postgresql+psycopg://postgres:ab@cd@dbhost/agro_intellect", ["cd"]),
        ("postgresql+psycopg://postgres:a@b@c@dbhost/agro_intellect", ["b@c"]),
        ("postgresql+psycopg://postgres:pw@tail@dbhost/agro_intellect", ["tail"]),
        ("postgresql+psycopg://postgres:pw@tail@dbhost/agro_intellect", ["pw@tail"]),
        ("postgresql+psycopg://postgres:pw://x@dbhost/agro_intellect", ["pw://x"]),
        ("postgresql+psycopg://postgres:Pa://ss@dbhost/agro_intellect", ["Pa://ss"]),
        ("postgresql+psycopg://postgres:pwhttp://x@dbhost/agro_intellect", ["pwhttp://x"]),
        ("postgresql+psycopg://postgres:x://y@dbhost/agro_intellect", ["x://y"]),
        ("postgresql+psycopg://postgres:pw://x://y@dbhost/agro_intellect", ["pw://x", "pw://x://y"]),
        ("postgresql+psycopg://postgres:pw://x@a@dbhost/agro_intellect", ["pw://x", "pw://x@a"]),
        ("postgresql+psycopg://postgres:pwhttp://x@tail@dbhost/agro_intellect", ["pwhttp://x"]),
    ],
)
def test_redact_url_credentials_masks_hostile_userinfo(raw, forbidden):
    redacted = redact_url_credentials(raw)

    for value in forbidden:
        assert value not in redacted
    assert "***@" in redacted
    assert redacted.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://pw://x:y@db/agro", "postgresql://***@db/agro"),
        ("postgresql://pw://rv4u:rv4p@db/agro", "postgresql://***@db/agro"),
        ("postgresql://http://user:pass@db/agro", "postgresql://***@db/agro"),
        ("postgresql://u://rv4u:rv4p@db/agro", "postgresql://***@db/agro"),
        ("postgresql://pw://rv4u:rv4p:extra@db/agro", "postgresql://***@db/agro"),
        ("postgresql://PW://rv4u:rv4p@db/agro", "postgresql://***@db/agro"),
        (
            "postgresql+psycopg://pw://rv4u:rv4p@db:5432/agro",
            "postgresql+psycopg://***@db:5432/agro",
        ),
        (
            "postgresql+psycopg://pw://rv4u:rv4p@127.0.0.1/agro",
            "postgresql+psycopg://***@127.0.0.1/agro",
        ),
        (
            "postgresql+psycopg://pw://rv4u:rv4p@[::1]:5432/agro",
            "postgresql+psycopg://***@[::1]:5432/agro",
        ),
        ("postgresql://pw://rv4u:rv4p?tail@db/agro", "postgresql://***@db/agro"),
        ("postgresql://pw://rv4u:rv4p#frag@db/agro", "postgresql://***@db/agro"),
        (
            "postgresql+psycopg://pw://rv4u:rv4p%40x@db/agro",
            "postgresql+psycopg://***@db/agro",
        ),
    ],
)
def test_redact_url_credentials_masks_pseudo_scheme_without_colon_entirely(raw, expected):
    redacted = redact_url_credentials(raw)

    assert redacted == expected


def test_redact_url_credentials_pseudo_scheme_first_url_masks_full_span_then_second_url():
    redacted = redact_url_credentials(
        "postgresql://pw://rv4u:rv4p@db/agro and https://rd4user:rv4-pw@example.com/path"
    )

    assert redacted == (
        "postgresql://***@db/agro and https://rd4user:***@example.com/path"
    )
    assert "rv4u" not in redacted


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "postgresql:// nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://\tnzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://\r\nnzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://.nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://+nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://-nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql://~nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql:// Nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1@dbhost:5432/agro",
            "postgresql://***@dbhost:5432/agro",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1@127.0.0.1/agro",
            "postgresql://***@127.0.0.1/agro",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1@[::1]:5432/agro",
            "postgresql://***@[::1]:5432/agro",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1@dbhost?tail",
            "postgresql://***@dbhost?tail",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1@dbhost#frag",
            "postgresql://***@dbhost#frag",
        ),
        (
            "postgresql:// nzx://mt9user:qb8pw1://z@dbhost/agro",
            "postgresql://***@dbhost/agro",
        ),
        (
            "postgres:// nzx://mt9user:qb8pw1@dbhost/agro",
            "postgres://***@dbhost/agro",
        ),
        (
            "postgresql+psycopg:// nzx://mt9user:qb8pw1@dbhost/agro",
            "postgresql+psycopg://***@dbhost/agro",
        ),
    ],
)
def test_redact_url_credentials_masks_non_empty_prefix_pseudo_scheme_entirely(
    raw, expected
):
    redacted = redact_url_credentials(raw)

    assert redacted == expected


def test_redact_url_credentials_leaves_hostless_or_uncredentialed_urls_alone():
    for raw in [
        "postgresql://dbhost/db",
        "postgresql://dbhost/db@name",
        "sqlite+pysqlite:///data/tmp/x.sqlite3",
    ]:
        assert redact_url_credentials(raw) == raw


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9x://u:pw@dbhost/agro", "9x://u:***@dbhost/agro"),
        ("_dhz://u:pw@dbhost/agro", "_dhz://u:***@dbhost/agro"),
        ("dhz_2://u:pw@dbhost/agro", "dhz_2://u:***@dbhost/agro"),
        ("d_hz://u:pw@dbhost/agro", "d_hz://u:***@dbhost/agro"),
        ("sqlite_driver://u:pw@dbhost/agro", "sqlite_driver://u:***@dbhost/agro"),
        ("2dhz://u:pw@dbhost/agro", "2dhz://u:***@dbhost/agro"),
        ("PW://u:pw@dbhost/agro", "PW://u:***@dbhost/agro"),
        ("2dh+z://u:pw@dbhost/agro", "2dh+z://u:***@dbhost/agro"),
        ("dhz2+x://u:pw@dbhost/agro", "dhz2+x://u:***@dbhost/agro"),
        ("9x_y://u:pw@dbhost/agro", "9x_y://u:***@dbhost/agro"),
        ("_2dh://u:pw@dbhost/agro", "_2dh://u:***@dbhost/agro"),
        (
            "postgresql 2dhz://u:pw@dbhost/agro",
            "postgresql 2dhz://u:***@dbhost/agro",
        ),
        (
            "postgresql\t_dhz://u:pw@dbhost/agro",
            "postgresql\t_dhz://u:***@dbhost/agro",
        ),
        (
            "postgresql dhz_2://u:pw@dbhost/agro",
            "postgresql dhz_2://u:***@dbhost/agro",
        ),
        (
            "postgresql d_hz://u:pw@dbhost/agro",
            "postgresql d_hz://u:***@dbhost/agro",
        ),
        (
            "text 2mysql://u:pw@dbhost/agro tail",
            "text 2mysql://u:***@dbhost/agro tail",
        ),
    ],
)
def test_redact_url_credentials_masks_digit_underscore_scheme_names(raw, expected):
    redacted = redact_url_credentials(raw)

    assert redacted == expected
    assert "pw@" not in redacted


def test_redact_url_credentials_digit_underscore_multi_url_does_not_bleed():
    redacted = redact_url_credentials(
        "9x://u:pw@dbhost/agro and _dhz://u:pw@dbhost/agro"
    )

    assert redacted == "9x://u:***@dbhost/agro and _dhz://u:***@dbhost/agro"
    assert "pw@" not in redacted


def test_redact_url_credentials_digit_underscore_scheme_after_clean_first_url():
    redacted = redact_url_credentials(
        "postgresql://db/agro and 9x://u:pw@dbhost/agro"
    )

    assert redacted == "postgresql://db/agro and 9x://u:***@dbhost/agro"
    assert "pw@" not in redacted


@pytest.mark.parametrize(
    "raw",
    [
        "9x://u:pw@dbhost/agro",
        "_dhz://u:pw@dbhost/agro",
        "dhz_2://u:pw@dbhost/agro",
        "d_hz://u:pw@dbhost/agro",
        "sqlite_driver://u:pw@dbhost/agro",
        "2dhz://u:pw@dbhost/agro",
        "PW://u:pw@dbhost/agro",
        "postgresql 2dhz://u:pw@dbhost/agro",
        "postgresql\td_hz://u:pw@dbhost/agro",
    ],
)
def test_redact_text_and_mapping_mask_digit_underscore_scheme_names(raw):
    redacted_text = redact_text(f"target {raw} now")

    assert "u:pw" not in redacted_text
    assert "pw@" not in redacted_text
    assert REDACTION in redacted_text

    redacted_mapping = redact_mapping({"note": f"target {raw} now"})

    assert "u:pw" not in str(redacted_mapping)
    assert "pw@" not in str(redacted_mapping)
    assert REDACTION in str(redacted_mapping)


def test_redact_url_credentials_multi_url_does_not_bleed_userinfo():
    redacted = redact_url_credentials(
        "postgresql://db/agro and https://user:pw@example.com/path"
    )

    assert redacted == "postgresql://db/agro and https://user:***@example.com/path"
    assert "pw@" not in redacted


def test_redact_url_credentials_failure_is_stable_and_safe():
    class _BadStr:
        def __str__(self):
            raise ValueError("boom-in-str swordfish")

    with pytest.raises(ValueError) as excinfo:
        redact_url_credentials(_BadStr())

    assert "swordfish" not in str(excinfo.value)
    assert str(excinfo.value) == "redaction failed: value cannot be rendered as text"


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
