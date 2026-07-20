from __future__ import annotations

from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Numeric, Text, Uuid, inspect
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.database import build_database
from backend.app.plant_operations import DailyCheckIn, ManualMeasurement
from backend.migrations import build_alembic_config


TASK_TABLES = {
    "accounts",
    "farm_memberships",
    "local_sessions",
    "farms",
    "plants",
    "plant_access_grants",
    "admin_audit_records",
    "daily_checkins",
    "manual_measurements",
}


def test_ft004_models_match_native_uuid_and_validation_contract():
    uuid_columns = [
        DailyCheckIn.__table__.c.check_in_id,
        DailyCheckIn.__table__.c.farm_id,
        DailyCheckIn.__table__.c.plant_id,
        DailyCheckIn.__table__.c.actor_account_id,
        DailyCheckIn.__table__.c.actor_membership_id,
        ManualMeasurement.__table__.c.measurement_id,
        ManualMeasurement.__table__.c.farm_id,
        ManualMeasurement.__table__.c.plant_id,
        ManualMeasurement.__table__.c.check_in_id,
        ManualMeasurement.__table__.c.actor_account_id,
        ManualMeasurement.__table__.c.actor_membership_id,
    ]
    assert all(isinstance(column.type, Uuid) and column.type.as_uuid for column in uuid_columns)
    assert all(
        column.default is not None and column.default.arg.__name__ == "uuid4"
        for column in (
            DailyCheckIn.__table__.c.check_in_id,
            ManualMeasurement.__table__.c.measurement_id,
        )
    )
    assert isinstance(ManualMeasurement.__table__.c.ph.type, Numeric)
    assert isinstance(ManualMeasurement.__table__.c.ec_ms_cm.type, Numeric)
    assert isinstance(
        DailyCheckIn.__table__.c.event_refs.type.dialect_impl(
            build_database(AppSettings()).engine().dialect
        ),
        JSONB,
    )
    assert all(
        fk.ondelete == "RESTRICT"
        for table in (DailyCheckIn.__table__, ManualMeasurement.__table__)
        for fk in table.foreign_keys
    )
    assert {constraint.name for constraint in DailyCheckIn.__table__.constraints if constraint.name} >= {
        "ck_daily_checkins_check_in_state",
        "ck_daily_checkins_observation_state",
        "ck_daily_checkins_observation_text_shape",
        "ck_daily_checkins_source_refs_object",
        "ck_daily_checkins_event_refs_object",
    }
    assert {constraint.name for constraint in ManualMeasurement.__table__.constraints if constraint.name} >= {
        "ck_manual_measurements_source_type",
        "ck_manual_measurements_trust_status",
        "ck_manual_measurements_value_required",
        "ck_manual_measurements_ph_range",
        "ck_manual_measurements_ec_non_negative",
        "ck_manual_measurements_source_refs_object",
        "ck_manual_measurements_event_refs_object",
    }


def test_ft004_revision_is_in_ordered_product_history_and_contains_guarded_downgrade():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    product_head = script.get_revision("head")
    assert product_head is not None
    assert product_head.revision == "ft012_task_approval_outcomes"
    assert product_head.down_revision == "ft011_safety_action_decisions"

    ft011_decisions = script.get_revision("ft011_safety_action_decisions")
    assert ft011_decisions is not None
    assert ft011_decisions.down_revision == "ft011_safety_classifications"

    ft011 = script.get_revision("ft011_safety_classifications")
    assert ft011 is not None
    assert ft011.down_revision == "ft009_plant_state"

    ft009 = script.get_revision("ft009_plant_state")
    assert ft009 is not None
    assert ft009.down_revision == "ft008_agent_chat_ui_feed"

    ft008 = script.get_revision("ft008_agent_chat_ui_feed")
    assert ft008 is not None
    assert ft008.down_revision == "ft005_photo_intake"

    ft005 = script.get_revision("ft005_photo_intake")
    assert ft005 is not None
    assert ft005.down_revision == "ft004_plant_operations"

    revision = script.get_revision("ft004_plant_operations")
    assert revision is not None
    assert revision.revision == "ft004_plant_operations"
    assert revision.down_revision == "ft002_farm_plant_access"

    source = Path(revision.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "timeline.jsonl" not in source
    assert "downgrade refused" in source


def test_ft004_postgresql_migration_schema_and_guarded_downgrade():
    settings = AppSettings.from_env()
    database = build_database(settings)
    schema = f"task019_schema_{uuid.uuid4().hex}"

    try:
        engine = database.engine()
        assert engine.dialect.name == "postgresql", (
            "TASK-019 migration evidence requires configured PostgreSQL"
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        ft001 = script.get_revision("ft001_access_sessions")
        ft002 = script.get_revision("ft002_farm_plant_access")
        ft004 = script.get_revision("ft004_plant_operations")
        assert ft001 is not None and ft002 is not None and ft004 is not None

        with engine.connect() as connection:
            outer = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    ft001.module.upgrade()
                    ft002.module.upgrade()
                    ft004.module.upgrade()

                db_inspector = inspect(connection)
                assert set(db_inspector.get_table_names(schema=schema)) == TASK_TABLES
                for table_name, column_names in {
                    "daily_checkins": [
                        "check_in_id",
                        "farm_id",
                        "plant_id",
                        "actor_account_id",
                        "actor_membership_id",
                    ],
                    "manual_measurements": [
                        "measurement_id",
                        "farm_id",
                        "plant_id",
                        "check_in_id",
                        "actor_account_id",
                        "actor_membership_id",
                    ],
                }.items():
                    columns = {
                        item["name"]: item
                        for item in db_inspector.get_columns(table_name, schema=schema)
                    }
                    for name in column_names:
                        assert isinstance(columns[name]["type"], Uuid)
                    for name in {"observed_at", "recorded_at", "measured_at", "created_at"} & columns.keys():
                        assert isinstance(columns[name]["type"], DateTime)
                        assert columns[name]["type"].timezone is True

                measurement_columns = {
                    item["name"]: item
                    for item in db_inspector.get_columns(
                        "manual_measurements", schema=schema
                    )
                }
                assert isinstance(measurement_columns["ph"]["type"], Numeric)
                assert isinstance(measurement_columns["ec_ms_cm"]["type"], Numeric)
                assert isinstance(measurement_columns["provenance_note"]["type"], Text)
                assert all(
                    isinstance(measurement_columns[name]["type"], JSONB)
                    for name in ("source_refs", "event_refs")
                )

                fks = db_inspector.get_foreign_keys("manual_measurements", schema=schema)
                assert all(fk["options"]["ondelete"] == "RESTRICT" for fk in fks)

                with Operations.context(context):
                    ft004.module.downgrade()
                assert {"daily_checkins", "manual_measurements"}.isdisjoint(
                    inspect(connection).get_table_names(schema=schema)
                )
            finally:
                outer.rollback()
    finally:
        database.dispose()
