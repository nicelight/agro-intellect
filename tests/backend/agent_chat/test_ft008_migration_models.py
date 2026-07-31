from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Boolean, Uuid, inspect, select, text
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.agent_chat import AgentBusEvent, UIFeedEvent
from backend.app.database import build_database
from backend.migrations import build_alembic_config


def test_ft008_models_preserve_native_uuid_restricted_relations_and_flags():
    models = (UIFeedEvent, AgentBusEvent)
    uuid_columns = [
        column
        for model in models
        for column in model.__table__.columns
        if column.name.endswith("_id")
        and column.name not in {"source_id", "agent_id"}
    ]
    assert uuid_columns
    assert all(
        isinstance(column.type, Uuid) and column.type.as_uuid
        for column in uuid_columns
    )
    assert all(
        foreign_key.ondelete == "RESTRICT"
        for model in models
        for foreign_key in model.__table__.foreign_keys
    )
    assert isinstance(UIFeedEvent.__table__.c.visible_to_agents.type, Boolean)
    assert isinstance(UIFeedEvent.__table__.c.consumable_by_agents.type, Boolean)
    assert isinstance(AgentBusEvent.__table__.c.consumable_by_agents.type, Boolean)

    database = build_database(AppSettings())
    try:
        dialect = database.engine().dialect
        json_columns = (
            UIFeedEvent.__table__.c.source_refs,
            UIFeedEvent.__table__.c.display_payload,
            UIFeedEvent.__table__.c.visible_to_roles,
            AgentBusEvent.__table__.c.actor_ref,
            AgentBusEvent.__table__.c.payload,
            AgentBusEvent.__table__.c.source_refs,
            AgentBusEvent.__table__.c.authorization_scope,
        )
        assert all(
            isinstance(column.type.dialect_impl(dialect), JSONB)
            for column in json_columns
        )
    finally:
        database.dispose()

    names = {
        constraint.name
        for model in models
        for constraint in model.__table__.constraints
        if constraint.name
    }
    assert {
        "uq_ui_feed_events_plant_agent_roster",
        "ck_ui_feed_events_visible_to_agents_false",
        "ck_ui_feed_events_consumable_by_agents_false",
        "ck_agent_bus_events_consumable_by_agents_true",
    } <= names


def test_decision_effect_revision_is_the_single_forward_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    assert script.get_heads() == ["ft013_decision_effects"]
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft013_decision_effects"
    assert head.down_revision == "ft008_lazy_introductions"

    source = Path(head.path).read_text(encoding="utf-8")
    assert "decision_record_id" in source
    assert "ck_agent_bus_events_authority_matrix" in source


def test_current_ft008_schema_has_feed_and_bus_but_no_batch_table(ft008_database):
    inspector = inspect(ft008_database.engine())
    tables = set(inspector.get_table_names())
    assert "agent_introduction_batches" not in tables
    assert {"ui_feed_events", "agent_bus_events"} <= tables
    for table in ("ui_feed_events", "agent_bus_events"):
        assert all(
            foreign_key["options"]["ondelete"] == "RESTRICT"
            for foreign_key in inspector.get_foreign_keys(table)
        )


def test_forward_migration_preserves_existing_ui_row_and_constraints(
    ft008_database,
    ft008_seed,
):
    farm, _boss, plant = ft008_seed
    event_id = uuid.uuid4()
    created_at = datetime(2025, 2, 3, 4, 5, tzinfo=timezone.utc)
    payload = {
        "payload_kind": "agent_introduction",
        "agent_id": "companion",
        "display_name": "Companion Agent",
        "competence_summary": "retained",
        "introduction_text": "retained byte-for-byte",
        "roster_version": 1,
    }
    with ft008_database.session() as session, session.begin():
        session.add(
            UIFeedEvent(
                ui_event_id=event_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                created_at=created_at,
                source_type="system",
                source_id=str(event_id),
                source_refs=[
                    "agent_roster:1",
                    f"agent_introduction:{event_id}",
                ],
                display_kind="agent_introduction",
                display_payload=payload,
                visible_to_roles=["boss", "engineer", "consultant"],
                visible_to_agents=False,
                consumable_by_agents=False,
                agent_id="companion",
                roster_version=1,
            )
        )

    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    migration = script.get_revision("ft008_lazy_introductions").module
    with ft008_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.downgrade()
        connection.execute(
            text(
                """
INSERT INTO agent_introduction_batches
    (batch_id, farm_id, plant_id, roster_version, content_sha256)
VALUES
    (:batch_id, :farm_id, :plant_id, 1, :digest)
"""
            ),
            {
                "batch_id": uuid.uuid4(),
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "digest": "a" * 64,
            },
        )
        connection.commit()

    before_inspector = inspect(ft008_database.engine())
    before_constraints = {
        item["name"]
        for item in before_inspector.get_unique_constraints("ui_feed_events")
    } | {
        item["name"]
        for item in before_inspector.get_check_constraints("ui_feed_events")
    }
    before_indexes = {
        item["name"] for item in before_inspector.get_indexes("ui_feed_events")
    }
    before_fks = before_inspector.get_foreign_keys("ui_feed_events")
    with ft008_database.session() as session:
        row = session.get(UIFeedEvent, event_id)
        before = (
            row.ui_event_id,
            row.farm_id,
            row.plant_id,
            row.created_at,
            row.source_id,
            row.source_refs,
            row.display_payload,
            row.visible_to_agents,
            row.consumable_by_agents,
            row.agent_id,
            row.roster_version,
        )

    with ft008_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
        connection.commit()

    after_inspector = inspect(ft008_database.engine())
    assert "agent_introduction_batches" not in after_inspector.get_table_names()
    assert before_constraints == {
        item["name"]
        for item in after_inspector.get_unique_constraints("ui_feed_events")
    } | {
        item["name"]
        for item in after_inspector.get_check_constraints("ui_feed_events")
    }
    assert before_indexes == {
        item["name"] for item in after_inspector.get_indexes("ui_feed_events")
    }
    assert before_fks == after_inspector.get_foreign_keys("ui_feed_events")
    with ft008_database.session() as session:
        row = session.scalar(
            select(UIFeedEvent).where(UIFeedEvent.ui_event_id == event_id)
        )
        after = (
            row.ui_event_id,
            row.farm_id,
            row.plant_id,
            row.created_at,
            row.source_id,
            row.source_refs,
            row.display_payload,
            row.visible_to_agents,
            row.consumable_by_agents,
            row.agent_id,
            row.roster_version,
        )
    assert after == before
