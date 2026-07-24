from __future__ import annotations

from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, Uuid, inspect
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.agent_chat import UIFeedEvent
from backend.app.companion_governance import (
    CompanionHumanAttention,
    CompanionIssue,
    CompanionProposal,
    DecisionRecord,
)
from backend.app.database import build_database
from backend.migrations import build_alembic_config


_MODELS = (
    CompanionIssue,
    CompanionHumanAttention,
    CompanionProposal,
    DecisionRecord,
)
_TABLES = {
    "companion_issues",
    "companion_human_attention",
    "companion_proposals",
    "decision_records",
}


def test_governance_models_have_native_uuid_restrictive_aggregate_shape():
    assert {model.__table__.name for model in _MODELS} == _TABLES
    uuid_columns = [
        column
        for model in _MODELS
        for column in model.__table__.c
        if column.name.endswith("_id")
    ]
    assert uuid_columns
    assert all(
        isinstance(column.type, Uuid) and column.type.as_uuid
        for column in uuid_columns
    )
    assert all(
        foreign_key.ondelete == "RESTRICT"
        for model in _MODELS
        for foreign_key in model.__table__.foreign_keys
    )
    deferrable_names = {
        foreign_key.constraint.name
        for model in _MODELS
        for foreign_key in model.__table__.foreign_keys
        if foreign_key.constraint.deferrable
        and foreign_key.constraint.initially == "DEFERRED"
    }
    assert {
        "fk_companion_attention_current_proposal",
        "fk_companion_attention_satisfied_decision",
        "fk_companion_proposals_attention",
        "fk_companion_proposals_decision",
    } <= deferrable_names
    check_names = {
        constraint.name
        for model in _MODELS
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert {
        "ck_companion_issues_state_matrix",
        "ck_companion_attention_state_matrix",
        "ck_companion_proposals_state_matrix",
        "ck_decision_records_effect_matrix",
        "ck_decision_records_workflow_effect_ref",
        "ck_decision_records_no_safety_authority",
    } <= check_names
    assert {
        index.name
        for model in _MODELS
        for index in model.__table__.indexes
        if index.unique
    } == {
        "uq_companion_issues_one_focused_per_plant",
        "uq_companion_attention_one_active_per_issue",
        "uq_companion_proposals_one_pending_per_issue",
    }


def test_governance_json_columns_and_ui_model_are_postgresql_native():
    database = build_database(AppSettings())
    try:
        dialect = database.engine().dialect
        json_columns = (
            CompanionIssue.__table__.c.opened_event_ref,
            CompanionHumanAttention.__table__.c.current_proposal_id,
            CompanionProposal.__table__.c.source_refs,
            CompanionProposal.__table__.c.created_event_ref,
            DecisionRecord.__table__.c.source_refs,
            DecisionRecord.__table__.c.decision_event_ref,
            UIFeedEvent.__table__.c.display_payload,
        )
        assert all(
            isinstance(column.type.dialect_impl(dialect), JSONB)
            for column in json_columns
            if column.name
            not in {"current_proposal_id"}
        )
    finally:
        database.dispose()
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in UIFeedEvent.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "companion_governance" in constraints["ck_ui_feed_events_source_type"]
    assert "companion_governance" in constraints["ck_ui_feed_events_display_kind"]
    assert "companion_governance" in constraints["ck_ui_feed_events_source_display"]


def test_ft013_aggregate_is_exact_guarded_product_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft013_governance_aggregate"
    assert head.down_revision == "ft012_runtime_dispositions"
    source = Path(head.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "downgrade refused" in source
    assert all(table in source for table in _TABLES)
    assert all(
        name in source
        for name in (
            "uq_companion_issues_one_focused_per_plant",
            "uq_companion_attention_one_active_per_issue",
            "uq_companion_proposals_one_pending_per_issue",
            "fk_companion_attention_current_proposal",
            "fk_companion_attention_satisfied_decision",
            "fk_companion_proposals_decision",
            "companion_governance",
        )
    )
    assert all(
        forbidden not in source
        for forbidden in (
            "provider_payload",
            "raw_chat",
            "device_command",
            "action_task",
            "ON DELETE CASCADE",
        )
    )


def test_ft013_migration_creates_complete_empty_aggregate(ft013_database):
    inspector = inspect(ft013_database.engine())
    assert _TABLES <= set(inspector.get_table_names())
    for model in _MODELS:
        table_name = model.__table__.name
        assert {column["name"] for column in inspector.get_columns(table_name)} == {
            column.name for column in model.__table__.c
        }
        assert all(
            foreign_key["options"]["ondelete"] == "RESTRICT"
            for foreign_key in inspector.get_foreign_keys(table_name)
        )
    with ft013_database.engine().connect() as connection:
        assert all(
            connection.execute(model.__table__.select().limit(1)).first() is None
            for model in _MODELS
        )
    deferrable = {
        foreign_key["name"]: foreign_key["options"]
        for table_name in (
            "companion_human_attention",
            "companion_proposals",
        )
        for foreign_key in inspector.get_foreign_keys(table_name)
        if foreign_key["options"].get("deferrable")
    }
    for name in (
        "fk_companion_attention_current_proposal",
        "fk_companion_attention_satisfied_decision",
        "fk_companion_proposals_attention",
        "fk_companion_proposals_decision",
    ):
        assert deferrable[name]["initially"] == "DEFERRED"
    ui_checks = {
        item["name"]: item["sqltext"]
        for item in inspector.get_check_constraints("ui_feed_events")
    }
    assert "companion_governance" in ui_checks["ck_ui_feed_events_source_type"]
    assert "companion_governance" in ui_checks["ck_ui_feed_events_display_kind"]
    assert "companion_governance" in ui_checks["ck_ui_feed_events_source_display"]
