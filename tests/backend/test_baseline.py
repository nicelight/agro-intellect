from __future__ import annotations

import asyncio

import httpx

from backend.app import AppSettings, app, create_app


def _request_json(path: str) -> httpx.Response:
    async def _call() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app(AppSettings()))
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(_call())


def test_backend_package_imports():
    assert create_app is not None
    assert app.title == app.state.settings.app_name
    assert isinstance(app.state.settings, AppSettings)


def test_app_settings_load_from_env_mapping():
    settings = AppSettings.from_env(
        {
            "APP_NAME": "from-env",
            "APP_ENV": "staging",
        }
    )

    assert settings.app_name == "from-env"
    assert settings.environment == "staging"


def test_create_app_uses_env_when_settings_missing(monkeypatch):
    monkeypatch.setenv("APP_NAME", "env-title")
    monkeypatch.setenv("APP_ENV", "production")

    resolved_app = create_app()

    assert resolved_app.title == "env-title"
    assert resolved_app.state.settings.app_name == "env-title"
    assert resolved_app.state.settings.environment == "production"


def test_create_app_respects_explicit_settings():
    explicit_settings = AppSettings(app_name="explicit-title", environment="test")

    resolved_app = create_app(explicit_settings)

    assert resolved_app.title == "explicit-title"
    assert resolved_app.state.settings == explicit_settings


def test_health_route_returns_ok():
    response = _request_json("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_route_returns_ready():
    response = _request_json("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
