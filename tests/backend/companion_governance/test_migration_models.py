from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, Uuid, inspect, text
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
from tests.backend.companion_governance.conftest import (
    seed_companion_classification,
)
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)


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
            CompanionProposal.__table__.c.source_refs,
            CompanionProposal.__table__.c.created_event_ref,
            DecisionRecord.__table__.c.source_refs,
            DecisionRecord.__table__.c.decision_event_ref,
            UIFeedEvent.__table__.c.display_payload,
        )
        assert all(
            isinstance(column.type.dialect_impl(dialect), JSONB)
            for column in json_columns
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


def test_ft013_decision_effects_is_exact_guarded_product_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft013_decision_effects"
    assert head.down_revision == "ft008_lazy_introductions"
    simplification = script.get_revision("ft013_simplify_companion")
    assert simplification is not None
    source = Path(simplification.path).read_text(encoding="utf-8")
    assert "fk_companion_attention_current_proposal" in source
    assert "current_proposal_id" in source
    assert "create_index" not in source
    assert "DROP TABLE" not in source.upper()
    governance = script.get_revision("ft013_governance_aggregate")
    assert governance is not None
    assert governance.down_revision == "ft012_runtime_dispositions"
    aggregate_source = Path(governance.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in aggregate_source.upper()
    assert "downgrade refused" in aggregate_source
    assert all(table in aggregate_source for table in _TABLES)
    assert all(
        name in aggregate_source
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
        forbidden not in aggregate_source
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
        "fk_companion_attention_satisfied_decision",
        "fk_companion_proposals_attention",
        "fk_companion_proposals_decision",
    ):
        assert deferrable[name]["initially"] == "DEFERRED"
    attention_columns = {
        column["name"]
        for column in inspector.get_columns("companion_human_attention")
    }
    attention_fks = {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys(
            "companion_human_attention"
        )
    }
    assert "current_proposal_id" not in attention_columns
    assert "fk_companion_attention_current_proposal" not in attention_fks
    ui_checks = {
        item["name"]: item["sqltext"]
        for item in inspector.get_check_constraints("ui_feed_events")
    }
    assert "companion_governance" in ui_checks["ck_ui_feed_events_source_type"]
    assert "companion_governance" in ui_checks["ck_ui_feed_events_display_kind"]
    assert "companion_governance" in ui_checks["ck_ui_feed_events_source_display"]


def test_forward_simplification_preserves_existing_w1_authority_and_projection_rows(
    ft013_pre_simplification_database,
):
    database = ft013_pre_simplification_database
    farm = seed_farm(database)
    boss, _membership = create_actor(database, farm, "boss")
    plant = create_active_plant(
        database,
        boss,
        plant_key=f"ft013_migration_{uuid.uuid4().hex[:10]}",
    )
    issue_id = uuid.uuid4()
    attention_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    run_id = uuid.uuid4()
    message_id = seed_companion_classification(
        database,
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
    )
    now = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)
    opened_event_id = uuid.uuid4()
    created_event_id = uuid.uuid4()
    opened_ref = {
        "timeline_event_id": str(opened_event_id),
        "timeline_ref": f"timeline.jsonl#{opened_event_id}",
        "event_type": "companion_issue_opened",
        "created_at": now.isoformat(),
    }
    created_ref = {
        "timeline_event_id": str(created_event_id),
        "timeline_ref": f"timeline.jsonl#{created_event_id}",
        "event_type": "companion_proposal_created",
        "created_at": now.isoformat(),
    }
    proposal_refs = [
        f"plant:{plant.plant_id}",
        f"message_envelope:{message_id}",
        f"safety_classification:{message_id}",
    ]
    attention_refs = [
        f"companion_issue:{issue_id}",
        f"companion_attention:{attention_id}",
        f"companion_proposal:{proposal_id}",
    ]
    with database.engine().begin() as connection:
        connection.execute(
            text(
                """
INSERT INTO companion_issues (
    issue_id, farm_id, plant_id, status, is_focused, summary_text,
    record_version, created_by_run_id, created_at, opened_event_ref
) VALUES (
    :issue_id, :farm_id, :plant_id, 'open', true, :summary_text,
    1, :run_id, :created_at, CAST(:opened_event_ref AS jsonb)
)
"""
            ),
            {
                "issue_id": issue_id,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "summary_text": "Сохранённая проблема.",
                "run_id": run_id,
                "created_at": now,
                "opened_event_ref": json.dumps(opened_ref),
            },
        )
        connection.execute(
            text(
                """
INSERT INTO companion_human_attention (
    attention_id, farm_id, plant_id, issue_id, attention_sequence,
    status, summary_text, current_proposal_id, record_version, created_at
) VALUES (
    :attention_id, :farm_id, :plant_id, :issue_id, 1,
    'active', :summary_text, :proposal_id, 1, :created_at
)
"""
            ),
            {
                "attention_id": attention_id,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "issue_id": issue_id,
                "summary_text": "Требуется внимание.",
                "proposal_id": proposal_id,
                "created_at": now,
            },
        )
        connection.execute(
            text(
                """
INSERT INTO companion_proposals (
    proposal_id, farm_id, plant_id, issue_id, attention_id,
    proposal_sequence, state, record_version, proposal_summary,
    proposal_text, rationale_text, proposed_effect, task_display_text,
    suggested_resolution, source_run_id, source_message_id,
    source_classification_message_id, source_refs,
    run_request_fingerprint, created_at, created_event_ref
) VALUES (
    :proposal_id, :farm_id, :plant_id, :issue_id, :attention_id,
    1, 'pending', 1, :proposal_summary,
    :proposal_text, NULL, 'discussion_only', NULL,
    'keep_open', :run_id, :message_id,
    :message_id, CAST(:source_refs AS jsonb),
    :fingerprint, :created_at, CAST(:created_event_ref AS jsonb)
)
"""
            ),
            {
                "proposal_id": proposal_id,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "issue_id": issue_id,
                "attention_id": attention_id,
                "proposal_summary": "Сохранённое предложение.",
                "proposal_text": "Проверить состояние вручную.",
                "run_id": run_id,
                "message_id": message_id,
                "source_refs": json.dumps(proposal_refs),
                "fingerprint": "a" * 64,
                "created_at": now,
                "created_event_ref": json.dumps(created_ref),
            },
        )
        for ui_event_id, source_refs, payload in (
            (
                attention_id,
                attention_refs,
                {
                    "payload_kind": "companion_attention",
                    "attention_ref": f"companion_attention:{attention_id}",
                    "issue_ref": f"companion_issue:{issue_id}",
                    "summary_text": "Требуется внимание.",
                },
            ),
            (
                proposal_id,
                [
                    *attention_refs,
                    f"safety_classification:{message_id}",
                ],
                {
                    "payload_kind": "companion_proposal",
                    "proposal_ref": f"companion_proposal:{proposal_id}",
                    "issue_ref": f"companion_issue:{issue_id}",
                    "proposal_state": "pending",
                    "summary_text": "Сохранённое предложение.",
                },
            ),
        ):
            connection.execute(
                text(
                    """
INSERT INTO ui_feed_events (
    ui_event_id, created_at, farm_id, plant_id, source_type, source_id,
    source_refs, display_kind, display_payload, visible_to_roles,
    visible_to_agents, consumable_by_agents, agent_id, roster_version
) VALUES (
    :ui_event_id, :created_at, :farm_id, :plant_id,
    'companion_governance', :source_id,
    CAST(:source_refs AS jsonb), 'companion_governance',
    CAST(:display_payload AS jsonb),
    CAST(:visible_to_roles AS jsonb), false, false, NULL, NULL
)
"""
                ),
                {
                    "ui_event_id": ui_event_id,
                    "created_at": now,
                    "farm_id": farm.farm_id,
                    "plant_id": plant.plant_id,
                    "source_id": str(ui_event_id),
                    "source_refs": json.dumps(source_refs),
                    "display_payload": json.dumps(payload),
                    "visible_to_roles": json.dumps(
                        ["boss", "engineer", "consultant"]
                    ),
                },
            )

    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft013_simplify_companion")
    with database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
        connection.commit()

    inspector = inspect(database.engine())
    assert "current_proposal_id" not in {
        column["name"]
        for column in inspector.get_columns("companion_human_attention")
    }
    with database.engine().connect() as connection:
        assert connection.execute(
            text("SELECT issue_id FROM companion_issues")
        ).scalar_one() == issue_id
        assert connection.execute(
            text("SELECT attention_id FROM companion_human_attention")
        ).scalar_one() == attention_id
        assert connection.execute(
            text("SELECT proposal_id FROM companion_proposals")
        ).scalar_one() == proposal_id
        assert set(
            connection.execute(
                text("SELECT ui_event_id FROM ui_feed_events")
            ).scalars()
        ) == {attention_id, proposal_id}
        assert connection.execute(
            text("SELECT count(*) FROM decision_records")
        ).scalar_one() == 0
        assert connection.execute(
            text(
                "SELECT opened_event_ref FROM companion_issues "
                "WHERE issue_id = :issue_id"
            ),
            {"issue_id": issue_id},
        ).scalar_one() == opened_ref
