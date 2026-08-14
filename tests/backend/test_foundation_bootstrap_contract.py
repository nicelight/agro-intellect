from __future__ import annotations

import subprocess
from pathlib import Path

from backend.app import AppSettings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SCRIPT = PROJECT_ROOT / "scripts" / "bootstrap-local.sh"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
RUNBOOK = PROJECT_ROOT / ".memory-bank" / "runbooks" / "foundation-local-runtime.md"


def test_settings_expose_local_runtime_roots_by_default():
    settings = AppSettings()

    assert settings.local_data_root == Path("data")
    assert settings.local_artifact_root == Path("data/artifacts")
    assert settings.local_timeline_root == Path("data/timeline")
    assert settings.local_temp_root == Path("data/tmp")
    assert settings.local_smoke_root == Path("data/smoke")
    assert settings.sync_status == "local_only"


def test_settings_load_local_runtime_roots_from_env_mapping():
    settings = AppSettings.from_env(
        {
            "LOCAL_DATA_ROOT": "runtime/data",
            "LOCAL_ARTIFACT_ROOT": "runtime/artifacts",
            "LOCAL_TIMELINE_ROOT": "runtime/timeline",
            "LOCAL_TEMP_ROOT": "runtime/tmp",
            "LOCAL_SMOKE_ROOT": "runtime/smoke",
            "SYNC_STATUS": "local_only",
        }
    )

    assert settings.local_data_root == Path("runtime/data")
    assert settings.local_artifact_root == Path("runtime/artifacts")
    assert settings.local_timeline_root == Path("runtime/timeline")
    assert settings.local_temp_root == Path("runtime/tmp")
    assert settings.local_smoke_root == Path("runtime/smoke")
    assert settings.sync_status == "local_only"


def test_env_example_documents_linux_mint_runtime_roots():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")

    for key in [
        "LOCAL_DATA_ROOT=data",
        "LOCAL_ARTIFACT_ROOT=data/artifacts",
        "LOCAL_TIMELINE_ROOT=data/timeline",
        "LOCAL_TEMP_ROOT=data/tmp",
        "LOCAL_SMOKE_ROOT=data/smoke",
        "SYNC_STATUS=local_only",
    ]:
        assert key in text


def test_bootstrap_script_dry_run_is_safe_and_actionable():
    result = subprocess.run(
        ["bash", str(BOOTSTRAP_SCRIPT), "--dry-run"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "Linux Mint local bootstrap completed" in output
    assert "Dry run:" in output
    assert "postgresql-client" in output or "PostgreSQL client tools detected" in output
    assert "DATABASE_URL=" not in output
    assert "postgresql+psycopg://postgres:postgres" not in output


def test_bootstrap_script_does_not_trace_or_print_env_contents():
    text = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")

    forbidden_fragments = [
        "set -x",
        "cat .env",
        "cat .env.example",
        "echo $DATABASE_URL",
        "printf $DATABASE_URL",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in text


def test_runbook_launch_command_binds_loopback_only():
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "--host 127.0.0.1 --port 8000" in text
    assert "--host 0.0.0.0" not in text
    assert "0.0.0.0" not in text


def test_runbook_documents_loopback_only_exposure():
    text = RUNBOOK.read_text(encoding="utf-8").lower()

    assert "loopback-only" in text
    assert "no lan mode" in text


def test_bootstrap_script_configures_no_server_host():
    text = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")

    assert "--host" not in text
    assert "0.0.0.0" not in text
