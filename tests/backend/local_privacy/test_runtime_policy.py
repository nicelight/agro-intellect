from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from backend.app import AppSettings, create_app


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"

REJECTED_SYNC_STATUSES = [
    "server_verified",
    "upload_pending",
    "upload_complete",
    "synced",
]

FORBIDDEN_EXPOSURE_TOKENS = [
    "HOST",
    "PORT",
    "CORS",
    "BEARER",
    "LAN",
    "TLS",
]

FORBIDDEN_PUBLIC_SMOKE_MATERIAL = [
    "token",
    "session",
    "account",
    "farm",
    "plant",
    "authorization",
    "password",
    "secret",
    "credential",
]


def test_default_sync_status_is_local_only():
    assert AppSettings().sync_status == "local_only"


def test_explicit_local_only_accepted_from_kwargs():
    assert AppSettings(sync_status="local_only").sync_status == "local_only"


def test_explicit_local_only_accepted_from_env():
    settings = AppSettings.from_env({"SYNC_STATUS": "local_only"})
    assert settings.sync_status == "local_only"


@pytest.mark.parametrize("status", REJECTED_SYNC_STATUSES)
def test_non_local_only_statuses_rejected_from_kwargs(status):
    with pytest.raises(RuntimeError, match="local_only"):
        AppSettings(sync_status=status)


@pytest.mark.parametrize("status", REJECTED_SYNC_STATUSES)
def test_non_local_only_statuses_rejected_from_env(status):
    with pytest.raises(RuntimeError, match="local_only"):
        AppSettings.from_env({"SYNC_STATUS": status})


def test_rejected_status_fails_before_app_startup():
    with pytest.raises(RuntimeError, match="local_only"):
        AppSettings.from_env({"SYNC_STATUS": "server_verified"})


@pytest.mark.parametrize("status", REJECTED_SYNC_STATUSES)
def test_rejection_error_does_not_leak_rejected_value(status):
    with pytest.raises(RuntimeError) as excinfo:
        AppSettings(sync_status=status)
    assert status not in str(excinfo.value)


def test_app_settings_are_frozen_without_sync_mutation_surface():
    settings = AppSettings()
    with pytest.raises(ValidationError):
        settings.sync_status = "server_verified"


def test_kwargs_test_injection_preserved(backend_settings):
    assert backend_settings.sync_status == "local_only"
    assert backend_settings.database_url.startswith("sqlite+pysqlite:///")


def test_create_app_keeps_supported_settings_injection_path(backend_settings):
    app = create_app(backend_settings)
    assert app.state.settings is backend_settings
    assert app.state.settings.sync_status == "local_only"


def test_redacted_for_log_remains_compatible():
    summary = AppSettings().redacted_for_log()
    assert summary["sync_status"] == "local_only"


def test_env_example_exposes_no_lan_cors_bearer_or_host_override():
    keys = [
        line.split("=", 1)[0].strip()
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip() and "=" in line
    ]
    assert keys
    for key in keys:
        for token in FORBIDDEN_EXPOSURE_TOKENS:
            assert token not in key, f"{key} introduces exposure surface {token}"


def test_settings_expose_no_host_bind_cors_or_bearer_surface():
    for name in AppSettings.model_fields:
        lower = name.lower()
        for token in ("host", "bind", "cors", "bearer"):
            assert token not in lower, f"{name} introduces exposure surface {token}"


def test_create_app_registers_no_cors_middleware(backend_settings):
    app = create_app(backend_settings)
    for middleware in app.user_middleware:
        assert "CORS" not in middleware.cls.__name__


def test_public_smoke_contains_no_product_or_auth_material(backend_settings):
    async def _collect() -> dict[str, str]:
        transport = httpx.ASGITransport(app=create_app(backend_settings))
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            health = await client.get("/health")
            ready = await client.get("/ready")
        return {
            "health_status": health.status_code,
            "health_body": health.text,
            "ready_status": ready.status_code,
            "ready_body": ready.text,
        }

    result = asyncio.run(_collect())

    assert result["health_status"] == 200
    assert result["ready_status"] == 200
    for body in (result["health_body"], result["ready_body"]):
        lowered = body.lower()
        for material in FORBIDDEN_PUBLIC_SMOKE_MATERIAL:
            assert material not in lowered
