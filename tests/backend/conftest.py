from __future__ import annotations

from pathlib import Path

import pytest

from backend.app import AppSettings, create_app, build_database


@pytest.fixture
def backend_settings(tmp_path: Path) -> AppSettings:
    database_path = tmp_path / "backend-test.sqlite3"
    return AppSettings(
        app_name="agro-intellect-test",
        environment="test",
        database_url=f"sqlite+pysqlite:///{database_path}",
        database_echo=False,
        database_pool_pre_ping=True,
    )


@pytest.fixture
def backend_database(backend_settings: AppSettings):
    database = build_database(backend_settings)
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture
def backend_app(backend_settings: AppSettings, backend_database):
    return create_app(backend_settings, database=backend_database)


@pytest.fixture
def backend_test_session(backend_database):
    with backend_database.test_session() as session:
        yield session
