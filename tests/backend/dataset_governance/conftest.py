"""Isolated PostgreSQL substrate and creation-seam helpers for FT-014 tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy.engine import make_url

from backend.app import AppSettings
from backend.app.database import DatabaseHandle, build_database
from backend.migrations import build_alembic_config
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)

FT014_NOW = datetime(2026, 8, 10, 7, 0, tzinfo=timezone.utc)

_REVISION_IDS = (
    "ft001_access_sessions",
    "ft002_farm_plant_access",
    "ft004_plant_operations",
    "ft005_photo_intake",
    "ft008_agent_chat_ui_feed",
    "ft009_plant_state",
    "ft011_safety_classifications",
    "ft011_safety_action_decisions",
    "ft012_task_approval_outcomes",
    "ft012_runtime_dispositions",
    "ft013_governance_aggregate",
    "ft012_simplify_follow_up_runtime",
    "ft013_simplify_companion",
    "ft008_lazy_introductions",
    "ft013_decision_effects",
)


class TimelineRecorder:
    """In-memory timeline appender that can fail on a selected event type."""

    def __init__(self, *, fail_on: str | None = None) -> None:
        self.events = []
        self.fail_on = fail_on

    def __call__(self, event):
        if event.event_type == self.fail_on:
            from backend.app.timeline import TimelineAppendError

            raise TimelineAppendError()
        self.events.append(event)
        event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(event_id),
            "timeline_ref": f"timeline.jsonl#{event_id}",
            "event_type": event.event_type,
            "created_at": FT014_NOW.isoformat(),
        }


@pytest.fixture
def ft014_database():
    with _postgres_database(include_ft014=True) as database:
        yield database


@pytest.fixture
def ft014_pre_migration_database():
    with _postgres_database(include_ft014=False) as database:
        yield database


@pytest.fixture
def ft014_seed(ft014_database):
    farm = seed_farm(ft014_database)
    boss, membership = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(
        ft014_database,
        boss,
        plant_key=f"ft014_{uuid.uuid4().hex[:10]}",
    )
    return farm, boss, membership, plant


def make_creation_command(
    actor,
    *,
    plant_id: uuid.UUID,
    source_kind: str = "photo_catalog_item",
    source_ref: uuid.UUID | None = None,
) -> object:
    from backend.app.dataset_governance import RecordDatasetEvidenceCommandV1

    return RecordDatasetEvidenceCommandV1(
        actor_context=actor,
        plant_id=plant_id,
        source_kind=source_kind,
        source_ref=source_ref or uuid.uuid4(),
    )


@contextmanager
def _postgres_database(*, include_ft014: bool):
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task047_ft014_{uuid.uuid4().hex}"
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
        revision_ids = [*_REVISION_IDS]
        if include_ft014:
            revision_ids.append("ft014_dataset_candidates")
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


__all__ = [
    "FT014_NOW",
    "TimelineRecorder",
    "ft014_database",
    "ft014_pre_migration_database",
    "ft014_seed",
    "make_creation_command",
]
