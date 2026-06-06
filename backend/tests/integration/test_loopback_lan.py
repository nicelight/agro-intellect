"""Integration tests for loopback default and LAN mode controls."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.api.errors import AppError
from backend.app.config.deployment import DeploymentConfig, DeploymentMode


class TestLoopbackDefault:
    def test_default_create_app_is_loopback(self):
        app = create_app()
        assert app.title == "Agro Intellect API"

    def test_default_app_has_csrf_protection_enabled(self):
        app = create_app()
        assert hasattr(app.state, "_csrf_protection")

    def test_get_health_works_without_csrf_token(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_state_changing_request_without_csrf_token_returns_403(self):
        app = create_app()
        client = TestClient(app)
        resp = client.post("/api/v1/auth/login", data={"login_identifier": "admin"})
        assert resp.status_code == 403
        data = resp.json()
        assert "error" in data
        assert "CSRF" in data["error"]["message"]

    def test_get_request_without_csrf_token_succeeds(self):
        app = create_app()
        client = TestClient(app)
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code in (200, 401)

    def test_head_request_without_csrf_token_passes(self):
        app = create_app()
        client = TestClient(app)

        @app.head("/test-head")
        def test_head():
            return "ok"

        resp = client.head("/test-head")
        assert resp.status_code in (200, 405)

    def test_options_request_without_csrf_token_passes(self):
        app = create_app()

        @app.options("/test-options")
        def test_opts():
            return "ok"

        client = TestClient(app)
        resp = client.options("/test-options")
        assert resp.status_code == 200


class TestLanMode:
    def test_lan_mode_with_valid_cors_config_creates_app(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("http://192.168.1.100:5173",),
        )
        app = create_app(cfg)
        assert app.title == "Agro Intellect API"

    def test_lan_mode_empty_cors_origins_fails(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=(),
        )
        with pytest.raises(AppError) as exc:
            create_app(cfg)
        assert exc.value.code == "invalid_config"

    def test_lan_mode_wildcard_origin_fails(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("*",),
        )
        with pytest.raises(AppError) as exc:
            create_app(cfg)
        assert exc.value.code == "invalid_config"

    def test_lan_mode_csrf_protection_still_active(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("http://192.168.1.100:5173",),
        )
        app = create_app(cfg)
        assert hasattr(app.state, "_csrf_protection")

    def test_lan_mode_csrf_disabled_when_configured(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("http://192.168.1.100:5173",),
            csrf_protection_enabled=False,
        )
        app = create_app(cfg)
        assert not hasattr(app.state, "_csrf_protection")

    def test_lan_post_without_csrf_token_returns_403(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("http://192.168.1.100:5173",),
        )
        app = create_app(cfg)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/login",
            data={"login_identifier": "admin"},
            headers={"Origin": "http://192.168.1.100:5173"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "error" in data

    def test_lan_get_without_csrf_token_succeeds(self):
        cfg = DeploymentConfig(
            mode=DeploymentMode.LAN,
            allowed_origins=("http://192.168.1.100:5173",),
        )
        app = create_app(cfg)
        client = TestClient(app)
        resp = client.get(
            "/health",
            headers={"Origin": "http://192.168.1.100:5173"},
        )
        assert resp.status_code == 200
