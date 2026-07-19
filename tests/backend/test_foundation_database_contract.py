from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import httpx
from alembic import command
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from backend.app import AppSettings, create_app
from backend.app.database import build_database, redacted_database_url
from backend.migrations import build_alembic_config


def _request_json(app, path: str) -> httpx.Response:
    async def _call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(_call())


class _PingDatabase:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = 0

    def ping(self) -> None:
        self.calls += 1
        if self.failure is not None:
            raise self.failure


def test_ready_route_can_prove_database_connectivity_when_enabled():
    database = _PingDatabase()
    app = create_app(
        AppSettings(app_name="ready-db-test", environment="test"),
        database=database,
        readiness_check_database=True,
    )

    response = _request_json(app, "/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}
    assert database.calls == 1


def test_ready_route_failure_is_redacted_when_database_check_enabled():
    database = _PingDatabase(
        RuntimeError("postgresql+psycopg://postgres:secret@localhost/agro_intellect")
    )
    app = create_app(
        AppSettings(app_name="ready-db-test", environment="test"),
        database=database,
        readiness_check_database=True,
    )

    response = _request_json(app, "/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"database": "failed"}}
    assert "secret" not in response.text


def test_redacted_database_url_hides_password():
    redacted = redacted_database_url(
        "postgresql+psycopg://postgres:secret@localhost/agro_intellect"
    )

    assert "secret" not in redacted
    assert "postgresql+psycopg://postgres:***@localhost/agro_intellect" == redacted


def test_alembic_baseline_discovers_product_head_without_running_it_on_sqlite(
    tmp_path: Path,
):
    settings = AppSettings(
        app_name="migration-test",
        environment="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'migration-test.sqlite3'}",
    )
    database = build_database(settings)
    try:
        config = build_alembic_config(settings)
        command.ensure_version(config)
        script = ScriptDirectory.from_config(config)

        with database.engine().connect() as connection:
            migration_context = MigrationContext.configure(connection)
            current_revision = migration_context.get_current_revision()

        tables = set(inspect(database.engine()).get_table_names())
        assert "alembic_version" in tables
        assert {"accounts", "farms", "plants"}.isdisjoint(tables)
        assert current_revision is None
        assert script.get_heads() == ["ft011_safety_classifications"]

        ft011 = script.get_revision("ft011_safety_classifications")
        assert ft011 is not None
        assert ft011.down_revision == "ft009_plant_state"

        ft009 = script.get_revision("ft009_plant_state")
        assert ft009 is not None
        assert ft009.down_revision == "ft008_agent_chat_ui_feed"

        ft008 = script.get_revision("ft008_agent_chat_ui_feed")
        assert ft008 is not None
        assert ft008.down_revision == "ft005_photo_intake"

        ft005 = script.get_revision("ft005_photo_intake")
        assert ft005 is not None
        assert ft005.down_revision == "ft004_plant_operations"
        ft004 = script.get_revision("ft004_plant_operations")
        assert ft004 is not None
        assert ft004.down_revision == "ft002_farm_plant_access"
        ft002 = script.get_revision("ft002_farm_plant_access")
        assert ft002 is not None
        assert ft002.down_revision == "ft001_access_sessions"
    finally:
        database.dispose()


def test_database_scripts_support_safe_dry_run_output():
    for script in ["scripts/db-init-local.sh", "scripts/db-migrate-local.sh"]:
        result = subprocess.run(
            ["bash", script, "--dry-run"],
            check=True,
            capture_output=True,
            text=True,
        )
        combined_output = result.stdout + result.stderr

        assert "DATABASE_URL=" not in combined_output
        assert "postgres:postgres@" not in combined_output
        assert "Dry run:" in combined_output


def test_database_scripts_do_not_trace_or_print_env_contents():
    for script in ["scripts/db-init-local.sh", "scripts/db-migrate-local.sh"]:
        content = Path(script).read_text()

        assert "set -x" not in content
        assert "cat .env" not in content
        assert "echo \"$DATABASE_URL\"" not in content
