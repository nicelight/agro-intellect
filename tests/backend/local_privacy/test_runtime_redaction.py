from __future__ import annotations

import asyncio
import tempfile
from typing import Any

import httpx
import pytest
from sqlalchemy import event

from backend.app import AppSettings, create_app, build_database
from backend.app.access_admin.errors import (
    AuthErrorCode,
    ERROR_DEFINITIONS,
    auth_error_response,
)
from backend.app.access_admin.models import Base
from backend.app.core.security import generate_session_token

CORPUS_DB_PASSWORD = "corpus-db-pw-2k9x"
CORPUS_ENV_SECRET = "corpus-env-secret-7f3a91"
CORPUS_BEARER = "corpus-bearer-q8w2e4"
CORPUS_API_KEY = "corpus-api-key-m5n7p9"
CORPUS_COOKIE = "agro-corpus-cookie-v1-abcdef1234567890"
CORPUS_SESSION_TOKEN = generate_session_token()

HOSTILE_DB_PASSWORDS = [
    "corpus-slash/a-b-pw",
    "corpus-space a-b-pw",
    "corpus-at@b-pw",
    "corpus-multi@a@b@c-pw",
    "corpus-tail@tail-pw",
    "corpus-pw://x-scheme",
    "corpus-pa://ss-scheme",
    "corpus-pwhttp://x-scheme",
    "corpus-x://y-scheme",
    "corpus-pw://x://y-scheme",
    "//pw:rv4p",
    "//rv4u:rv4p",
    "//u:pw?tail",
    "//u:pw#frag",
]

HOSTILE_DB_URLS = [
    "postgresql:// nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://\tnzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://\r\nnzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://.nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://+nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://-nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql://~nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql:// Nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql:// nzx://mt9user:qb8pw1@dbhost:5432/agro_intellect",
    "postgresql:// nzx://mt9user:qb8pw1@127.0.0.1/agro_intellect",
    "postgresql:// nzx://mt9user:qb8pw1@[::1]:5432/agro_intellect",
    "postgresql:// nzx://mt9user:qb8pw1@dbhost?tail",
    "postgresql:// nzx://mt9user:qb8pw1@dbhost#frag",
    "postgresql:// nzx://mt9user:qb8pw1://z@dbhost/agro_intellect",
    "postgres:// nzx://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql+psycopg:// nzx://mt9user:qb8pw1@dbhost/agro_intellect",
]

DIGIT_UNDERSCORE_SCHEME_URLS = [
    "9x://mt9user:qb8pw1@dbhost/agro_intellect",
    "_dhz://mt9user:qb8pw1@dbhost/agro_intellect",
    "dhz_2://mt9user:qb8pw1@dbhost/agro_intellect",
    "d_hz://mt9user:qb8pw1@dbhost/agro_intellect",
    "sqlite_driver://mt9user:qb8pw1@dbhost/agro_intellect",
    "2dhz://mt9user:qb8pw1@dbhost/agro_intellect",
    "PW://mt9user:qb8pw1@dbhost/agro_intellect",
    "2dh+z://mt9user:qb8pw1@dbhost/agro_intellect",
    "dhz2+x://mt9user:qb8pw1@dbhost/agro_intellect",
    "9x_y://mt9user:qb8pw1@dbhost/agro_intellect",
    "_2dh://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql 2dhz://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql\t_dhz://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql dhz_2://mt9user:qb8pw1@dbhost/agro_intellect",
    "postgresql d_hz://mt9user:qb8pw1@dbhost/agro_intellect",
    "text 2mysql://mt9user:qb8pw1@dbhost/agro_intellect tail",
]

CORPUS = [
    CORPUS_DB_PASSWORD,
    CORPUS_ENV_SECRET,
    CORPUS_BEARER,
    CORPUS_API_KEY,
    CORPUS_COOKIE,
    CORPUS_SESSION_TOKEN,
]


class _Http:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._client.post(url, **kwargs))

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return asyncio.run(self._client.get(url, **kwargs))

    def close(self) -> None:
        asyncio.run(self._client.aclose())


@pytest.fixture
def corpus_settings() -> AppSettings:
    return AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=(
            "postgresql+psycopg://postgres:"
            f"{CORPUS_DB_PASSWORD}@localhost/agro_intellect"
        ),
        database_echo=False,
        database_pool_pre_ping=True,
    )


@pytest.fixture
def http() -> _Http:
    database_path = tempfile.mkdtemp() + "/runtime-redaction.sqlite3"
    settings = AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=f"sqlite+pysqlite:///{database_path}",
        database_echo=False,
        database_pool_pre_ping=True,
    )
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
    app = create_app(settings, database=database)
    transport = httpx.ASGITransport(app=app)
    try:
        client = asyncio.run(
            _open_client(transport)
        )
        try:
            yield client
        finally:
            client.close()
    finally:
        database.dispose()


async def _open_client(transport: httpx.ASGITransport) -> _Http:
    client = httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1",
    )
    return _Http(client)


def test_settings_summary_masks_corpus_and_preserves_source(
    corpus_settings: AppSettings,
):
    source_url = corpus_settings.database_url

    summary = corpus_settings.redacted_for_log()
    summary_text = " ".join(summary.values())

    for raw in CORPUS:
        assert raw not in summary_text
    assert "postgres:***@localhost" in summary["database_url"]
    assert corpus_settings.database_url == source_url


@pytest.mark.parametrize("hostile_pw", HOSTILE_DB_PASSWORDS)
def test_settings_summary_masks_hostile_database_passwords(hostile_pw):
    settings = AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=(
            "postgresql+psycopg://postgres:" f"{hostile_pw}@dbhost/agro_intellect"
        ),
        database_echo=False,
        database_pool_pre_ping=True,
    )
    source_url = settings.database_url

    summary = settings.redacted_for_log()
    summary_text = " ".join(summary.values())

    assert hostile_pw not in summary_text
    assert "***@dbhost/agro_intellect" in summary["database_url"]
    assert settings.database_url == source_url


@pytest.mark.parametrize("hostile_url", HOSTILE_DB_URLS)
def test_settings_summary_masks_non_empty_prefix_pseudo_scheme_database_urls(
    hostile_url,
):
    settings = AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=hostile_url,
        database_echo=False,
        database_pool_pre_ping=True,
    )
    source_url = settings.database_url

    summary = settings.redacted_for_log()
    summary_text = " ".join(summary.values())

    assert "qb8pw1" not in summary_text
    assert "***@" in summary["database_url"]
    assert settings.database_url == source_url


@pytest.mark.parametrize("hostile_url", DIGIT_UNDERSCORE_SCHEME_URLS)
def test_settings_summary_masks_digit_underscore_scheme_database_urls(hostile_url):
    settings = AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=hostile_url,
        database_echo=False,
        database_pool_pre_ping=True,
    )
    source_url = settings.database_url

    summary = settings.redacted_for_log()
    summary_text = " ".join(summary.values())

    assert "qb8pw1" not in summary_text
    assert "mt9user:***@" in summary["database_url"]
    assert "qb8pw1@" not in summary_text
    assert settings.database_url == source_url


def test_auth_error_envelope_contains_only_stable_catalog_values():
    class _Request:
        state = type("State", (), {"request_id": None})()
        headers = {}

    for code in AuthErrorCode:
        response = auth_error_response(_Request(), code)
        body = response.body.decode("utf-8")

        assert code.value in body
        assert ERROR_DEFINITIONS[code].message in body
        assert '"request_id"' in body
        for raw in CORPUS:
            assert raw not in body


def test_validation_error_does_not_echo_rejected_corpus_values(http: _Http):
    response = http.post(
        "/api/session/login",
        json={
            "login_name": "corpus-admin",
            "password": CORPUS_ENV_SECRET,
            "token_hash": CORPUS_SESSION_TOKEN,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == AuthErrorCode.VALIDATION_FAILED.value
    assert payload["error"]["message"] == ERROR_DEFINITIONS[
        AuthErrorCode.VALIDATION_FAILED
    ].message
    for raw in CORPUS:
        assert raw not in response.text


def test_login_failure_is_generic_and_redacted(http: _Http):
    response = http.post(
        "/api/session/login",
        json={"login_name": "corpus-admin", "password": CORPUS_DB_PASSWORD},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == AuthErrorCode.CREDENTIAL_INVALID.value
    assert "corpus-admin" not in response.text
    for raw in CORPUS:
        assert raw not in response.text


def test_protected_route_denial_hides_corpus_credentials(http: _Http):
    outputs: list[str] = []

    response = http.get(
        "/api/plants/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {CORPUS_BEARER}"},
    )
    outputs.append(response.text)
    assert response.status_code == 401

    response = http.get(
        "/api/plants/00000000-0000-0000-0000-000000000001",
        headers={"cookie": f"agro_intellect_session={CORPUS_SESSION_TOKEN}"},
    )
    outputs.append(response.text)
    assert response.status_code == 401

    response = http.get(
        "/api/plants/00000000-0000-0000-0000-000000000001",
        headers={"cookie": f"agro_intellect_session={CORPUS_API_KEY}"},
    )
    outputs.append(response.text)
    assert response.status_code == 401

    combined = " ".join(outputs)
    for raw in CORPUS:
        assert raw not in combined


def test_unhandled_exception_returns_generic_body_without_corpus():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    def explode():
        raise RuntimeError(f"boom with {CORPUS_ENV_SECRET}")

    app = FastAPI()
    app.get("/explode")(lambda: explode())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/explode")

    assert response.status_code == 500
    for raw in CORPUS:
        assert raw not in response.text
