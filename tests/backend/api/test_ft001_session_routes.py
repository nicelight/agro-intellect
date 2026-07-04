from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select

from backend.app.access_admin.actor_context import (
    ActorContextResolver,
    AuthTransport,
)
from backend.app.access_admin.credential_service import AuthenticationFailed
from backend.app.access_admin.models import Account, Base, FarmMembership, LocalSession
from backend.app.access_admin.security import hash_password, hash_session_token
from backend.app.access_admin.session_service import IssuedSession, ValidatedSession
from backend.app.api.session import (
    ResolvedCurrentSession,
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_NAME,
    get_session_backend,
)
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.app.main import create_app


NOW = datetime(2026, 7, 4, 4, 0, tzinfo=timezone.utc)
RAW_TOKEN = "synthetic-browser-session-token"


class StaticSessionValidator:
    def __init__(self, validated: ValidatedSession) -> None:
        self.validated = validated

    def validate_session(self, _raw_token: object) -> ValidatedSession:
        return self.validated


@dataclass
class FakeSessionBackend:
    issued: IssuedSession
    resolved: ResolvedCurrentSession | None
    login_fails: bool = False
    revoked_result: bool = True
    login_calls: list[tuple[object, object, str | None]] = field(default_factory=list)
    revoked_tokens: list[object] = field(default_factory=list)
    resolve_calls: list[tuple[object, str, AuthTransport]] = field(
        default_factory=list
    )

    def login(
        self,
        login_name: object,
        password: object,
        *,
        client_label: str | None = None,
    ) -> IssuedSession:
        self.login_calls.append((login_name, password, client_label))
        if self.login_fails:
            raise AuthenticationFailed
        return self.issued

    def revoke_session(self, raw_token: object) -> bool:
        self.revoked_tokens.append(raw_token)
        return self.revoked_result

    def resolve_current_session(
        self,
        raw_token: object,
        *,
        request_id: str,
        transport: AuthTransport,
    ) -> ResolvedCurrentSession | None:
        self.resolve_calls.append((raw_token, request_id, transport))
        return self.resolved


def _validated_session() -> ValidatedSession:
    account_id = uuid.uuid4()
    account = Account(
        account_id=account_id,
        login_name="boss",
        display_name="Local Boss",
        account_status="active",
        password_hash="test-only-password-hash",
    )
    membership = FarmMembership(
        membership_id=uuid.uuid4(),
        account_id=account_id,
        farm_id=uuid.uuid4(),
        role_preset="boss",
        membership_status="active",
    )
    session = LocalSession(
        session_id=uuid.uuid4(),
        account_id=account_id,
        token_hash="a" * 64,
        created_at=NOW,
        expires_at=NOW + timedelta(days=7),
        auth_method="local_password",
    )
    return ValidatedSession(
        session=session,
        account=account,
        membership=membership,
    )


def _backend(*, login_fails: bool = False) -> FakeSessionBackend:
    validated = _validated_session()
    actor = ActorContextResolver(
        session_validator=StaticSessionValidator(validated),
        snapshot_provider=lambda **_kwargs: None,
    ).resolve(
        request_id="req-current",
        raw_session_token=RAW_TOKEN,
        transport=AuthTransport.COOKIE,
    )
    return FakeSessionBackend(
        issued=IssuedSession(
            session=validated.session,
            account=validated.account,
            membership=validated.membership,
            raw_token=RAW_TOKEN,
        ),
        resolved=ResolvedCurrentSession(
            actor=actor,
            display_name=validated.account.display_name,
        ),
        login_fails=login_fails,
    )


def _client(
    backend: FakeSessionBackend,
    *,
    base_url: str = "http://127.0.0.1",
    client_host: str = "127.0.0.1",
) -> TestClient:
    app = create_app(
        settings=AppSettings(database_url="sqlite+pysqlite:///:memory:"),
    )
    app.dependency_overrides[get_session_backend] = lambda: backend
    return TestClient(app, base_url=base_url, client=(client_host, 50000))


def _cookie(header: str):
    parsed = SimpleCookie()
    parsed.load(header)
    return parsed[SESSION_COOKIE_NAME]


def test_loopback_login_sets_exact_cookie_and_returns_only_safe_summary():
    backend = _backend()
    with _client(backend) as client:
        response = client.post(
            "/api/session/login",
            json={"login_name": "boss", "password": "valid-password"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "account_id": str(backend.issued.account.account_id),
        "farm_id": str(backend.issued.membership.farm_id),
        "membership_id": str(backend.issued.membership.membership_id),
        "role_preset": "boss",
        "session_expires_at": "2026-07-11T04:00:00Z",
    }
    assert backend.login_calls == [("boss", "valid-password", "browser")]
    assert RAW_TOKEN not in response.text
    assert "token_hash" not in response.text
    assert response.headers["cache-control"] == "no-store"

    cookie = _cookie(response.headers["set-cookie"])
    assert cookie.value == RAW_TOKEN
    assert cookie["path"] == "/"
    assert cookie["max-age"] == str(SESSION_COOKIE_MAX_AGE)
    assert cookie["httponly"] is True
    assert cookie["samesite"].lower() == "lax"
    assert cookie["secure"] == ""
    assert parsedate_to_datetime(cookie["expires"]) == backend.issued.session.expires_at


def test_https_login_sets_secure_cookie_and_plain_lan_http_is_rejected():
    https_backend = _backend()
    with _client(https_backend, base_url="https://localhost") as client:
        secure_response = client.post(
            "/api/session/login",
            json={"login_name": "boss", "password": "valid-password"},
        )

    assert secure_response.status_code == 200
    assert _cookie(secure_response.headers["set-cookie"])["secure"] is True

    with _client(https_backend, base_url="https://localhost") as client:
        secure_logout = client.post("/api/session/logout")
    assert secure_logout.status_code == 204
    assert _cookie(secure_logout.headers["set-cookie"])["secure"] is True

    lan_backend = _backend()
    with _client(lan_backend, base_url="http://192.0.2.10") as client:
        denied = client.post(
            "/api/session/login",
            headers={"x-request-id": "req-lan-http"},
            json={"login_name": "boss", "password": "valid-password"},
        )

    assert denied.status_code == 403
    assert denied.json() == {
        "error": {
            "code": "AUTH_FORBIDDEN",
            "message": "Request is not allowed.",
            "request_id": "req-lan-http",
        }
    }
    assert lan_backend.login_calls == []


def test_spoofed_loopback_host_from_remote_peer_is_rejected():
    backend = _backend()
    with _client(
        backend,
        base_url="http://localhost",
        client_host="192.0.2.20",
    ) as client:
        denied = client.post(
            "/api/session/login",
            headers={"x-request-id": "req-spoofed-loopback"},
            json={"login_name": "boss", "password": "valid-password"},
        )

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "AUTH_FORBIDDEN"
    assert backend.login_calls == []


def test_invalid_login_and_validation_failure_are_generic_and_redacted():
    invalid_backend = _backend(login_fails=True)
    with _client(invalid_backend) as client:
        invalid = client.post(
            "/api/session/login",
            headers={"x-request-id": "req-invalid-login"},
            json={"login_name": "unknown", "password": "do-not-echo"},
        )
        validation = client.post(
            "/api/session/login",
            headers={"x-request-id": "req-invalid-shape"},
            json={"password": "validation-secret", "token_hash": "forbidden"},
        )

    assert invalid.status_code == 401
    assert invalid.json() == {
        "error": {
            "code": "AUTH_CREDENTIAL_INVALID",
            "message": "Invalid login or password.",
            "request_id": "req-invalid-login",
        }
    }
    assert "unknown" not in invalid.text
    assert "do-not-echo" not in invalid.text

    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "VALIDATION_FAILED"
    assert validation.json()["error"]["request_id"] == "req-invalid-shape"
    assert "validation-secret" not in validation.text
    assert "token_hash" not in validation.text


def test_login_preserves_password_whitespace_as_credential_data():
    backend = _backend()
    with _client(backend) as client:
        response = client.post(
            "/api/session/login",
            json={"login_name": "boss", "password": " spaced-password "},
        )

    assert response.status_code == 200
    assert backend.login_calls == [("boss", " spaced-password ", "browser")]


@pytest.mark.parametrize("has_cookie", [False, True])
def test_logout_is_idempotent_and_clears_matching_cookie(has_cookie: bool):
    backend = _backend()
    backend.revoked_result = False
    headers = (
        {"cookie": f"{SESSION_COOKIE_NAME}={RAW_TOKEN}"}
        if has_cookie
        else None
    )
    with _client(backend) as client:
        response = client.post("/api/session/logout", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert backend.revoked_tokens == ([RAW_TOKEN] if has_cookie else [])
    cookie = _cookie(response.headers["set-cookie"])
    assert cookie.value == ""
    assert cookie["path"] == "/"
    assert cookie["max-age"] == "0"
    assert cookie["httponly"] is True
    assert cookie["samesite"].lower() == "lax"
    assert parsedate_to_datetime(cookie["expires"]) < NOW


def test_multiple_credentials_fail_closed_without_revocation():
    backend = _backend()
    with _client(backend) as client:
        response = client.post(
            "/api/session/logout",
            headers={
                "cookie": f"{SESSION_COOKIE_NAME}={RAW_TOKEN}",
                "authorization": "Bearer synthetic-other-token",
            },
        )

    assert response.status_code == 204
    assert backend.revoked_tokens == []


@pytest.mark.parametrize(
    "headers",
    [
        {"authorization": "Bearer synthetic-other-token"},
        {"cookie": f"{SESSION_COOKIE_NAME}=existing-session-token"},
    ],
)
def test_login_rejects_multiple_credential_sources(headers: dict[str, str]):
    backend = _backend()
    with _client(backend) as client:
        response = client.post(
            "/api/session/login",
            headers=headers,
            json={"login_name": "boss", "password": "valid-password"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_FORBIDDEN"
    assert backend.login_calls == []


def test_me_resolves_actor_context_and_returns_safe_summary():
    backend = _backend()
    with _client(backend) as client:
        response = client.get(
            "/api/session/me",
            headers={
                "cookie": f"{SESSION_COOKIE_NAME}={RAW_TOKEN}",
                "x-request-id": "req-me",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "account_id": str(backend.resolved.actor.account_id),
        "display_name": "Local Boss",
        "farm_id": str(backend.resolved.actor.farm_id),
        "membership_id": str(backend.resolved.actor.membership_id),
        "role_preset": "boss",
        "membership_status": "active",
        "session_expires_at": "2026-07-11T04:00:00Z",
        "plant_scope_summary": {"status": "deferred"},
    }
    assert backend.resolve_calls == [
        (RAW_TOKEN, "req-me", AuthTransport.COOKIE)
    ]
    assert response.headers["cache-control"] == "no-store"
    assert RAW_TOKEN not in response.text
    assert all(
        forbidden not in response.text
        for forbidden in ("password_hash", "token_hash", "session_id")
    )


def test_me_missing_invalid_and_bearer_credentials_use_stable_safe_errors():
    backend = _backend()
    with _client(backend) as client:
        missing = client.get(
            "/api/session/me",
            headers={"x-request-id": "req-missing"},
        )

        backend.resolved = None
        invalid = client.get(
            "/api/session/me",
            headers={
                "cookie": f"{SESSION_COOKIE_NAME}=invalid-token",
                "x-request-id": "req-invalid",
            },
        )
        bearer = client.get(
            "/api/session/me",
            headers={
                "authorization": "Bearer bearer-secret",
                "x-request-id": "req-bearer",
            },
        )

    assert missing.status_code == 401
    assert missing.json()["error"] == {
        "code": "AUTH_SESSION_REQUIRED",
        "message": "Authentication required.",
        "request_id": "req-missing",
    }
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "AUTH_SESSION_INVALID"
    assert bearer.status_code == 401
    assert bearer.json()["error"]["code"] == "AUTH_SESSION_INVALID"
    assert "invalid-token" not in invalid.text
    assert "bearer-secret" not in bearer.text


def test_session_router_preserves_foundation_smoke_routes():
    backend = _backend()
    with _client(backend) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_production_backend_commits_digest_only_session_and_revokes_it():
    settings = AppSettings(database_url="sqlite+pysqlite:///:memory:")
    database = build_database(settings)
    engine = database.engine()

    def install_sqlite_contract_functions(dbapi_connection, _record):
        dbapi_connection.create_function(
            "btrim",
            1,
            lambda value: value.strip() if isinstance(value, str) else value,
        )

    event.listen(engine, "connect", install_sqlite_contract_functions)
    Base.metadata.create_all(engine)

    account_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    with database.session() as database_session:
        database_session.add_all(
            [
                Account(
                    account_id=account_id,
                    login_name="boss",
                    display_name="Production Adapter Boss",
                    account_status="active",
                    password_hash=hash_password("valid-password"),
                ),
                FarmMembership(
                    membership_id=uuid.uuid4(),
                    account_id=account_id,
                    farm_id=farm_id,
                    role_preset="boss",
                    membership_status="active",
                ),
            ]
        )
        database_session.commit()

    app = create_app(settings=settings, database=database)
    try:
        with TestClient(
            app,
            base_url="http://127.0.0.1",
            client=("127.0.0.1", 50000),
        ) as client:
            login_response = client.post(
                "/api/session/login",
                json={"login_name": "boss", "password": "valid-password"},
            )
            assert login_response.status_code == 200
            raw_token = login_response.cookies[SESSION_COOKIE_NAME]

            me_response = client.get("/api/session/me")
            assert me_response.status_code == 200
            assert me_response.json()["farm_id"] == str(farm_id)

            logout_response = client.post("/api/session/logout")
            assert logout_response.status_code == 204

            revoked_response = client.get(
                "/api/session/me",
                headers={"cookie": f"{SESSION_COOKIE_NAME}={raw_token}"},
            )
            assert revoked_response.status_code == 401
            assert revoked_response.json()["error"]["code"] == "AUTH_SESSION_INVALID"

        with database.session() as database_session:
            persisted = list(database_session.scalars(select(LocalSession)))
            assert len(persisted) == 1
            assert persisted[0].token_hash == hash_session_token(raw_token)
            assert persisted[0].token_hash != raw_token
            assert persisted[0].revoked_at is not None
    finally:
        database.dispose()
