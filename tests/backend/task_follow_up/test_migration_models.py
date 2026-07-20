from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Uuid, inspect

from backend.app import AppSettings
from backend.app.task_follow_up import Approval, Outcome, Task
from backend.migrations import build_alembic_config


def test_ft012_is_exact_additive_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft012_task_approval_outcomes"
    assert head.down_revision == "ft011_safety_action_decisions"
    source = Path(head.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "ft011_safety_action_decisions" in source
    assert "downgrade refused" in source
    assert all(token not in source for token in (
        "device_command", "provider_payload", "target_value", "dosage", "schedule_at"
    ))


def test_models_have_native_uuid_restrictive_authority_shape():
    for model in (Approval, Task, Outcome):
        table = model.__table__
        uuid_columns = [
            column for column in table.c
            if column.name.endswith("_id") and column.name != "created_by_agent_id"
        ]
        assert uuid_columns
        assert all(isinstance(column.type, Uuid) and column.type.as_uuid for column in uuid_columns)
        assert all(fk.ondelete == "RESTRICT" for fk in table.foreign_keys)
        for column in table.c:
            if isinstance(column.type, DateTime):
                assert column.type.timezone
    assert set(Task.__table__.c).isdisjoint(set())
    assert {constraint.name for constraint in Approval.__table__.constraints if constraint.name} >= {
        "ck_approvals_state_matrix", "uq_approvals_safety_decision"
    }
    assert {constraint.name for constraint in Task.__table__.constraints if constraint.name} >= {
        "ck_tasks_source_matrix", "ck_tasks_completion_matrix",
        "uq_tasks_classification_message", "uq_tasks_approval", "uq_tasks_parent_action"
    }
    assert {constraint.name for constraint in Outcome.__table__.constraints if constraint.name} >= {
        "ck_outcomes_value", "uq_outcomes_follow_up_task", "uq_outcomes_request"
    }


def test_postgresql_migration_creates_exact_relations(ft012_database):
    inspector = inspect(ft012_database.engine())
    assert {"approvals", "tasks", "outcomes"} <= set(inspector.get_table_names())
    for model in (Approval, Task, Outcome):
        table = model.__table__
        assert {item["name"] for item in inspector.get_columns(table.name)} == {
            column.name for column in table.c
        }
        assert all(
            item["options"]["ondelete"] == "RESTRICT"
            for item in inspector.get_foreign_keys(table.name)
        )
