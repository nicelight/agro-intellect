"""Integration tests for auth API endpoints via TestClient."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    InMemoryAccessRepository,
    MembershipRole,
    MembershipStatus,
)
from backend.app.api import create_app
from backend.app.config.deployment import DeploymentConfig, DeploymentMode

NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


def build_repo() -> InMemoryAccessRepository:
    repo = InMemoryAccessRepository()
    repo.add_account(
        Account(
            account_id="acct_boss",
            display_name="Boss",
            login_identifier="boss.local",
            status=AccountStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    repo.add_farm(
        Farm(
            farm_id="farm_local",
            display_name="Local Farm",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    repo.add_membership(
        FarmMembership(
            membership_id="mbr_boss",
            account_id="acct_boss",
            farm_id="farm_local",
            role=MembershipRole.BOSS,
            status=MembershipStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return repo


@pytest.fixture
def client():
    cfg = DeploymentConfig(mode=DeploymentMode.LOOPBACK, csrf_protection_enabled=False)
    app = create_app(cfg)
    return TestClient(app)


class TestLogin:
    def test_login_success(self, client):
        repo = build_repo()

        import backend.app.api.routes.auth as auth_routes
        original = auth_routes._TEST_REPO

        try:
            auth_routes._TEST_REPO = repo
            resp = client.post("/api/v1/auth/login", json={"login_identifier": "boss.local"})
        finally:
            auth_routes._TEST_REPO = original

        assert resp.status_code == 200
        data = resp.json()
        assert "session_token" in data
        assert "session_ref" in data
        assert "expires_at" in data
        assert isinstance(data["session_token"], str)
        assert isinstance(data["session_ref"], str)
        assert isinstance(data["expires_at"], str)

    def test_login_invalid_credentials(self, client):
        repo = build_repo()

        import backend.app.api.routes.auth as auth_routes
        original = auth_routes._TEST_REPO

        try:
            auth_routes._TEST_REPO = repo
            resp = client.post("/api/v1/auth/login", json={"login_identifier": "nonexistent"})
        finally:
            auth_routes._TEST_REPO = original

        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "invalid_request"

    def test_login_missing_body(self, client):
        resp = client.post("/api/v1/auth/login")
        assert resp.status_code in (400, 422)


class TestMe:
    def test_me_with_valid_session(self, client):
        repo = build_repo()

        import backend.app.api.routes.auth as auth_routes
        original = auth_routes._TEST_REPO

        try:
            auth_routes._TEST_REPO = repo
            login_resp = client.post(
                "/api/v1/auth/login", json={"login_identifier": "boss.local"}
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["session_token"]

            resp = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            auth_routes._TEST_REPO = original

        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "resolved"
        assert data["account_id"] == "acct_boss"
        assert data["farm_id"] == "farm_local"
        assert data["membership_id"] == "mbr_boss"
        assert data["role"] == "boss"
        assert data["membership_status"] == "active"
        assert data["resolved_at"] is not None

    def test_me_without_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "invalid_session"

    def test_me_with_invalid_token(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_1234567890abcdef"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data


class TestLogout:
    def test_logout_with_valid_session(self, client):
        repo = build_repo()

        import backend.app.api.routes.auth as auth_routes
        original = auth_routes._TEST_REPO

        try:
            auth_routes._TEST_REPO = repo
            login_resp = client.post(
                "/api/v1/auth/login", json={"login_identifier": "boss.local"}
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["session_token"]

            resp = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
        finally:
            auth_routes._TEST_REPO = original

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "logged_out"

    def test_logout_without_token(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data

    def test_error_response_format(self, client):
        resp = client.get("/api/v1/auth/me")
        data = resp.json()
        assert "error" in data
        err = data["error"]
        assert "code" in err
        assert "message" in err
        assert "details" in err
        assert "request_ref" in err
        assert "next_valid_actions" in err
        assert isinstance(err["details"], dict)
        assert isinstance(err["next_valid_actions"], list)
