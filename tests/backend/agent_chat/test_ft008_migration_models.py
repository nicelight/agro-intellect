from __future__ import annotations

from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Boolean, Uuid
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.agent_chat import AgentBusEvent, AgentIntroductionBatch, UIFeedEvent
from backend.app.database import build_database
from backend.migrations import build_alembic_config


def test_ft008_models_use_native_uuid_restricted_relations_and_strict_flags():
    models = (AgentIntroductionBatch, UIFeedEvent, AgentBusEvent)
    uuid_columns = [
        column
        for model in models
        for column in model.__table__.columns
        if column.name.endswith("_id") and column.name not in {"source_id", "agent_id"}
    ]
    assert uuid_columns
    assert all(isinstance(column.type, Uuid) and column.type.as_uuid for column in uuid_columns)
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
        assert all(isinstance(column.type.dialect_impl(dialect), JSONB) for column in json_columns)
    finally:
        database.dispose()

    names = {
        constraint.name
        for model in models
        for constraint in model.__table__.constraints
        if constraint.name
    }
    assert {
        "uq_agent_introduction_batches_plant_roster",
        "uq_ui_feed_events_plant_agent_roster",
        "ck_ui_feed_events_visible_to_agents_false",
        "ck_ui_feed_events_consumable_by_agents_false",
        "ck_agent_bus_events_consumable_by_agents_true",
    } <= names


def test_ft008_revision_is_ordered_head_and_guarded():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft013_governance_aggregate"
    assert head.down_revision == "ft012_runtime_dispositions"
    runtime_dispositions = script.get_revision("ft012_runtime_dispositions")
    assert runtime_dispositions is not None
    assert runtime_dispositions.down_revision == "ft012_task_approval_outcomes"
    ft012 = script.get_revision("ft012_task_approval_outcomes")
    assert ft012 is not None
    assert ft012.down_revision == "ft011_safety_action_decisions"

    ft011_decisions = script.get_revision("ft011_safety_action_decisions")
    assert ft011_decisions is not None
    assert ft011_decisions.down_revision == "ft011_safety_classifications"

    ft011 = script.get_revision("ft011_safety_classifications")
    assert ft011 is not None
    assert ft011.down_revision == "ft009_plant_state"

    ft009 = script.get_revision("ft009_plant_state")
    assert ft009 is not None
    assert ft009.down_revision == "ft008_agent_chat_ui_feed"

    revision = script.get_revision("ft008_agent_chat_ui_feed")
    assert revision is not None
    assert revision.down_revision == "ft005_photo_intake"
    source = Path(revision.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "downgrade refused" in source
    assert all(
        table in source
        for table in (
            "agent_introduction_batches",
            "ui_feed_events",
            "agent_bus_events",
        )
    )


def test_ft008_migration_created_all_tables(ft008_database):
    inspector = __import__("sqlalchemy").inspect(ft008_database.engine())
    assert {
        "agent_introduction_batches",
        "ui_feed_events",
        "agent_bus_events",
    } <= set(inspector.get_table_names())
    for table in (
        "agent_introduction_batches",
        "ui_feed_events",
        "agent_bus_events",
    ):
        assert all(
            foreign_key["options"]["ondelete"] == "RESTRICT"
            for foreign_key in inspector.get_foreign_keys(table)
        )
