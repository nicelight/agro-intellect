from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from backend.app import AppSettings
from backend.app.database import DatabaseHandle, build_database
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)


@pytest.fixture
def ft009_database():
    with _postgres_database() as database:
        yield database


@pytest.fixture
def ft009_seed(ft009_database):
    farm = seed_farm(ft009_database)
    boss, _membership = create_actor(ft009_database, farm, "boss")
    plant = create_active_plant(
        ft009_database,
        boss,
        plant_key=f"ft009_{uuid.uuid4().hex[:10]}",
    )
    return farm, boss, plant


@pytest.fixture
def event_ref_factory():
    events = []

    def append(event):
        events.append(event)
        event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(event_id),
            "timeline_ref": f"timeline.jsonl#{event_id}",
            "event_type": event.event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    append.events = events
    return append


@contextmanager
def _postgres_database():
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task035_plant_state_{uuid.uuid4().hex}"
    scoped: DatabaseHandle | None = None
    try:
        assert base.engine().dialect.name == "postgresql"
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        scoped = build_database(
            settings.model_copy(
                update={"database_url": url.render_as_string(hide_password=False)}
            )
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        revision_ids = (
            "ft001_access_sessions",
            "ft002_farm_plant_access",
            "ft004_plant_operations",
            "ft005_photo_intake",
            "ft008_agent_chat_ui_feed",
            "ft009_plant_state",
        )
        with scoped.engine().connect() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                for revision_id in revision_ids:
                    script.get_revision(revision_id).module.upgrade()
            connection.commit()
        yield scoped
    finally:
        if scoped is not None:
            scoped.dispose()
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            connection.commit()
        base.dispose()


__all__ = ["event_ref_factory", "ft009_database", "ft009_seed"]
