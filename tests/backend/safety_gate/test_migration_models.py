from __future__ import annotations

from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import Boolean, DateTime, Text, UniqueConstraint, Uuid, inspect
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.agent_chat import UIFeedEvent
from backend.app.database import build_database
from backend.app.safety_gate import SafetyActionDecision
from backend.migrations import build_alembic_config


def test_safety_decision_model_has_exact_native_restrictive_shape():
    table = SafetyActionDecision.__table__
    assert set(table.c) == {
        table.c.decision_id,
        table.c.classification_message_id,
        table.c.farm_id,
        table.c.plant_id,
        table.c.actor_account_id,
        table.c.actor_membership_id,
        table.c.actor_role_preset,
        table.c.permission_source,
        table.c.grant_id,
        table.c.action_kind,
        table.c.safety_status,
        table.c.reason_code,
        table.c.ph_measurement_id,
        table.c.ec_measurement_id,
        table.c.ph_status,
        table.c.ec_status,
        table.c.ph_measured_at,
        table.c.ec_measured_at,
        table.c.expires_at,
        table.c.evaluated_at,
        table.c.created_at,
        table.c.summary_text,
    }
    uuid_columns = [column for column in table.c if column.name.endswith("_id")]
    assert uuid_columns and all(
        isinstance(column.type, Uuid) and column.type.as_uuid
        for column in uuid_columns
    )
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in table.foreign_keys)
    assert all(
        isinstance(table.c[name].type, DateTime) and table.c[name].type.timezone
        for name in (
            "ph_measured_at",
            "ec_measured_at",
            "expires_at",
            "evaluated_at",
            "created_at",
        )
    )
    assert isinstance(table.c.summary_text.type, Text)
    assert any(
        isinstance(constraint, UniqueConstraint)
        and constraint.name == "uq_safety_action_decisions_classification"
        for constraint in table.constraints
    )
    names = {constraint.name for constraint in table.constraints if constraint.name}
    assert {
        "ck_safety_action_decisions_permission_shape",
        "ck_safety_action_decisions_route_matrix",
        "ck_safety_action_decisions_ph_evidence_shape",
        "ck_safety_action_decisions_ec_evidence_shape",
        "ck_safety_action_decisions_evidence_matrix",
        "ck_safety_action_decisions_evaluation_timestamp",
        "ck_safety_action_decisions_summary",
    } <= names
    assert not any(
        token in column.name
        for column in table.c
        for token in (
            "candidate",
            "provider",
            "approval_id",
            "task_id",
            "command",
            "quantity",
            "dosage",
            "target",
            "metadata",
        )
    )


def test_ui_model_adds_only_inert_safety_status_variant():
    names = {
        constraint.name
        for constraint in UIFeedEvent.__table__.constraints
        if constraint.name
    }
    assert "ck_ui_feed_events_source_display" in names
    assert isinstance(UIFeedEvent.__table__.c.visible_to_agents.type, Boolean)
    assert isinstance(UIFeedEvent.__table__.c.consumable_by_agents.type, Boolean)
    database = build_database(AppSettings())
    try:
        dialect = database.engine().dialect
        assert isinstance(
            UIFeedEvent.__table__.c.display_payload.type.dialect_impl(dialect),
            JSONB,
        )
    finally:
        database.dispose()


def test_action_decision_revision_is_exact_product_head_and_guarded():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("head")
    assert revision is not None
    assert revision.revision == "ft013_simplify_companion"
    assert revision.down_revision == "ft012_simplify_follow_up_runtime"
    companion_governance = script.get_revision("ft013_governance_aggregate")
    assert companion_governance is not None
    assert companion_governance.down_revision == "ft012_runtime_dispositions"
    runtime_dispositions = script.get_revision("ft012_runtime_dispositions")
    assert runtime_dispositions is not None
    assert runtime_dispositions.down_revision == "ft012_task_approval_outcomes"
    ft012 = script.get_revision("ft012_task_approval_outcomes")
    assert ft012 is not None
    assert ft012.down_revision == "ft011_safety_action_decisions"
    decisions = script.get_revision("ft011_safety_action_decisions")
    assert decisions is not None
    assert decisions.down_revision == "ft011_safety_classifications"
    classification = script.get_revision("ft011_safety_classifications")
    assert classification is not None
    assert classification.down_revision == "ft009_plant_state"
    source = Path(decisions.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "downgrade refused" in source
    assert "safety_action_decisions" in source
    assert "safety_status" in source
    assert all(
        forbidden not in source
        for forbidden in (
            "candidate_output",
            "provider_payload",
            "action_task",
            "timeline_event",
            "device_command",
        )
    )


def test_action_decision_migration_created_exact_relations_and_constraints(
    ft011_database,
):
    inspector = inspect(ft011_database.engine())
    assert "safety_action_decisions" in inspector.get_table_names()
    columns = {item["name"]: item for item in inspector.get_columns("safety_action_decisions")}
    assert set(columns) == {column.name for column in SafetyActionDecision.__table__.c}
    assert all(
        foreign_key["options"]["ondelete"] == "RESTRICT"
        for foreign_key in inspector.get_foreign_keys("safety_action_decisions")
    )
    unique_names = {
        item["name"] for item in inspector.get_unique_constraints("safety_action_decisions")
    }
    assert "uq_safety_action_decisions_classification" in unique_names
    check_names = {
        item["name"] for item in inspector.get_check_constraints("safety_action_decisions")
    }
    assert {
        "ck_safety_action_decisions_permission_shape",
        "ck_safety_action_decisions_route_matrix",
        "ck_safety_action_decisions_evidence_matrix",
        "ck_safety_action_decisions_summary",
    } <= check_names
    ui_checks = {
        item["name"] for item in inspector.get_check_constraints("ui_feed_events")
    }
    assert "ck_ui_feed_events_source_display" in ui_checks
