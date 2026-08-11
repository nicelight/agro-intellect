from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from backend.app import AppSettings
from backend.app.database import DatabaseHandle, build_database
from backend.app.photo_intake import PhotoArtifactStore, PhotoCatalogItem
from backend.migrations import build_alembic_config


@pytest.fixture
def ft005_database():
    with _postgres_database() as database:
        yield database


@pytest.fixture
def photo_artifact_store(tmp_path):
    return PhotoArtifactStore(
        AppSettings(local_artifact_root=tmp_path / "artifacts")
    )


@pytest.fixture
def event_ref_factory():
    events = []

    def append(event):
        events.append(event)
        timeline_event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(timeline_event_id),
            "timeline_ref": f"timeline.jsonl#{timeline_event_id}",
            "event_type": event.event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    append.events = events
    return append


@contextmanager
def _postgres_database():
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task021_photo_{uuid.uuid4().hex}"
    scoped: DatabaseHandle | None = None
    try:
        assert base.engine().dialect.name == "postgresql"
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        scoped_settings = settings.model_copy(
            update={"database_url": url.render_as_string(hide_password=False)}
        )
        scoped = build_database(scoped_settings)
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        with scoped.engine().connect() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                script.get_revision("ft001_access_sessions").module.upgrade()
                script.get_revision("ft002_farm_plant_access").module.upgrade()
                script.get_revision("ft004_plant_operations").module.upgrade()
                script.get_revision("ft005_photo_intake").module.upgrade()
                script.get_revision("ft014_dataset_candidates").module.upgrade()
            connection.commit()
        yield scoped
    finally:
        if scoped is not None:
            scoped.dispose()
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            connection.commit()
        base.dispose()


def photo_count(database: DatabaseHandle) -> int:
    with database.session() as session:
        return session.scalar(select(func.count(PhotoCatalogItem.photo_id)))

