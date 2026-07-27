from __future__ import annotations

from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Numeric, Uuid

from backend.app import AppSettings
from backend.app.plant_state import PlantStateRecord
from backend.migrations import build_alembic_config


def test_plant_state_model_has_exact_authority_shape():
    table = PlantStateRecord.__table__
    assert isinstance(table.c.state_record_id.type, Uuid)
    assert isinstance(table.c.farm_id.type, Uuid)
    assert isinstance(table.c.plant_id.type, Uuid)
    assert isinstance(table.c.run_id.type, Uuid)
    assert isinstance(table.c.message_id.type, Uuid)
    assert isinstance(table.c.confidence.type, Numeric)
    assert table.c.confidence.type.precision == 6
    assert table.c.confidence.type.scale == 5
    assert all(
        isinstance(table.c[name].type, DateTime) and table.c[name].type.timezone
        for name in ("observed_at", "recorded_at", "confirmed_at", "created_at", "updated_at")
    )
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in table.foreign_keys)
    assert {item.name for item in table.indexes} == {
        "ix_plant_state_records_plant_recorded_desc",
        "ix_plant_state_records_plant_key_recorded_desc",
    }
    assert {item.name for item in table.constraints if item.name} >= {
        "uq_plant_state_records_message_id",
        "ck_plant_state_records_kind_fields",
        "ck_plant_state_records_vision_shape",
        "ck_plant_state_records_assessment_shape",
        "ck_plant_state_records_confidence",
        "ck_plant_state_records_version",
        "ck_plant_state_records_confirmation_shape",
    }


def test_ft009_revision_is_direct_guarded_ancestor_of_current_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft012_simplify_follow_up_runtime"
    assert head.down_revision == "ft013_governance_aggregate"
    companion_governance = script.get_revision("ft013_governance_aggregate")
    assert companion_governance is not None
    assert companion_governance.down_revision == "ft012_runtime_dispositions"
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
    source = Path(ft009.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "downgrade refused" in source
    assert "SELECT EXISTS (SELECT 1 FROM plant_state_records LIMIT 1)" in source


def test_ft009_postgresql_constraints_and_guarded_downgrade(ft009_database):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    inspector = inspect(ft009_database.engine())
    assert "plant_state_records" in inspector.get_table_names()
    columns = {
        item["name"]: item
        for item in inspector.get_columns("plant_state_records")
    }
    assert all(
        isinstance(columns[name]["type"], Uuid)
        for name in (
            "state_record_id",
            "farm_id",
            "plant_id",
            "run_id",
            "message_id",
            "confirmed_by_account_id",
            "confirmed_by_membership_id",
        )
    )
    assert {item["name"] for item in inspector.get_indexes("plant_state_records")} >= {
        "ix_plant_state_records_plant_recorded_desc",
        "ix_plant_state_records_plant_key_recorded_desc",
    }
    assert all(
        item["options"]["ondelete"] == "RESTRICT"
        for item in inspector.get_foreign_keys("plant_state_records")
    )
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings.from_env()))
    with ft009_database.engine().connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("DELETE FROM plant_state_records"))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                script.get_revision("ft009_plant_state").module.downgrade()
            assert "plant_state_records" not in inspect(connection).get_table_names()
        finally:
            transaction.rollback()
