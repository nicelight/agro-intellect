from __future__ import annotations

from sqlalchemy import text

from backend.migrations import build_alembic_config, build_migration_database


def test_backend_app_uses_explicit_database_state(backend_app, backend_settings, backend_database):
    assert backend_app.title == "agro-intellect-test"
    assert backend_app.state.settings == backend_settings
    assert backend_app.state.database is backend_database


def test_backend_test_session_opens_clean_boundary(backend_test_session):
    assert backend_test_session.execute(text("SELECT 1")).scalar_one() == 1


def test_migration_entrypoint_builds_alembic_config(backend_settings):
    config = build_alembic_config(backend_settings)

    assert config.get_main_option("script_location").endswith("backend/migrations")
    assert config.get_main_option("sqlalchemy.url") == backend_settings.database_url
    assert config.get_main_option("sqlalchemy.echo") == "false"


def test_migration_entrypoint_builds_database_handle(backend_settings):
    database = build_migration_database(backend_settings)
    try:
        assert database.settings == backend_settings
    finally:
        database.dispose()
