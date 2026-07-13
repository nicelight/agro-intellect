from __future__ import annotations

from datetime import datetime
from pathlib import Path
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Boolean, DateTime, Text, Uuid, inspect
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.access_admin import (
    AdminAuditRecord,
    Farm,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from backend.app.database import build_database
from backend.migrations import build_alembic_config


TASK_TABLES = {
    "accounts",
    "farm_memberships",
    "local_sessions",
    "farms",
    "plants",
    "plant_access_grants",
    "admin_audit_records",
}


def test_ft002_models_match_native_uuid_authority_contract():
    uuid_columns = [
        Farm.__table__.c.farm_id,
        FarmMembership.__table__.c.farm_id,
        Plant.__table__.c.plant_id,
        Plant.__table__.c.farm_id,
        PlantAccessGrant.__table__.c.grant_id,
        PlantAccessGrant.__table__.c.membership_id,
        PlantAccessGrant.__table__.c.plant_id,
        AdminAuditRecord.__table__.c.admin_audit_id,
        AdminAuditRecord.__table__.c.farm_id,
        AdminAuditRecord.__table__.c.target_id,
    ]
    assert all(isinstance(column.type, Uuid) and column.type.as_uuid for column in uuid_columns)
    assert all(
        column.default is not None and column.default.arg.__name__ == "uuid4"
        for column in (
            Farm.__table__.c.farm_id,
            Plant.__table__.c.plant_id,
            PlantAccessGrant.__table__.c.grant_id,
            AdminAuditRecord.__table__.c.admin_audit_id,
        )
    )
    assert isinstance(PlantAccessGrant.__table__.c.plant_approve_actions.type, Boolean)
    assert isinstance(AdminAuditRecord.__table__.c.before_summary.type.dialect_impl(build_database(AppSettings()).engine().dialect), JSONB)

    assert Farm(farm_key="local_farm", display_name="  Local Farm  ").display_name == "Local Farm"
    assert Plant(
        farm_id=uuid.uuid4(),
        plant_key="tomato_001",
        display_name=" Tomato 001 ",
        status="active",
    ).display_name == "Tomato 001"
    with pytest.raises(ValueError):
        Farm(farm_key="other_farm", display_name="Other")
    with pytest.raises(ValueError):
        Plant(
            farm_id=uuid.uuid4(),
            plant_key="Tomato-001",
            display_name="Tomato",
            status="active",
        )

    membership_farm_fk = next(iter(FarmMembership.__table__.c.farm_id.foreign_keys))
    assert membership_farm_fk.target_fullname == "farms.farm_id"
    assert membership_farm_fk.ondelete == "RESTRICT"
    for table in (Plant.__table__, PlantAccessGrant.__table__, AdminAuditRecord.__table__):
        assert all(fk.ondelete == "RESTRICT" for fk in table.foreign_keys)

    assert {constraint.name for constraint in Farm.__table__.constraints if constraint.name} >= {
        "ck_farms_farm_key",
        "ck_farms_display_name",
        "uq_farms_farm_key",
    }
    assert {index.name for index in Plant.__table__.indexes} == {
        "ix_plants_farm_status"
    }
    assert {index.name for index in PlantAccessGrant.__table__.indexes} == {
        "ix_plant_access_grants_plant_status"
    }
    assert {index.name for index in AdminAuditRecord.__table__.indexes} == {
        "ix_admin_audit_records_farm_created_desc",
        "ix_admin_audit_records_plant_created_desc",
    }


def test_ft002_revision_is_in_ordered_product_history_and_contains_no_destructive_reconciliation():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    product_head = script.get_revision("head")
    assert product_head is not None
    assert product_head.revision == "ft008_agent_chat_ui_feed"
    assert product_head.down_revision == "ft005_photo_intake"

    ft005 = script.get_revision("ft005_photo_intake")
    assert ft005 is not None
    assert ft005.down_revision == "ft004_plant_operations"

    ft004 = script.get_revision("ft004_plant_operations")
    assert ft004 is not None
    assert ft004.down_revision == "ft002_farm_plant_access"

    revision = script.get_revision("ft002_farm_plant_access")
    assert revision is not None
    assert revision.revision == "ft002_farm_plant_access"
    assert revision.down_revision == "ft001_access_sessions"

    source = Path(revision.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "DROP COLUMN farm_id" not in source
    assert "multiple legacy Farm identities" in source
    assert "downgrade refused" in source


def test_ft002_postgresql_migration_schema_reconciliation_and_guarded_downgrade():
    settings = AppSettings.from_env()
    database = build_database(settings)
    schema = f"task012_{uuid.uuid4().hex}"

    try:
        engine = database.engine()
        assert engine.dialect.name == "postgresql", (
            "TASK-012 migration evidence requires configured PostgreSQL"
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        ft001 = script.get_revision("ft001_access_sessions")
        ft002 = script.get_revision("ft002_farm_plant_access")
        assert ft001 is not None and ft002 is not None

        with engine.connect() as connection:
            outer = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    ft001.module.upgrade()
                    ft002.module.upgrade()

                db_inspector = inspect(connection)
                assert set(db_inspector.get_table_names(schema=schema)) == TASK_TABLES

                for table_name, column_names in {
                    "farms": ["farm_id"],
                    "plants": ["plant_id", "farm_id"],
                    "plant_access_grants": ["grant_id", "membership_id", "plant_id"],
                    "admin_audit_records": [
                        "admin_audit_id",
                        "farm_id",
                        "actor_account_id",
                        "actor_membership_id",
                        "target_id",
                        "plant_id",
                    ],
                }.items():
                    columns = {
                        item["name"]: item
                        for item in db_inspector.get_columns(table_name, schema=schema)
                    }
                    for name in column_names:
                        assert isinstance(columns[name]["type"], Uuid)
                    for name in {"created_at", "updated_at"} & columns.keys():
                        assert isinstance(columns[name]["type"], DateTime)
                        assert columns[name]["type"].timezone is True

                audit_columns = {
                    item["name"]: item
                    for item in db_inspector.get_columns(
                        "admin_audit_records", schema=schema
                    )
                }
                assert isinstance(audit_columns["request_id"]["type"], Text)
                assert all(
                    isinstance(audit_columns[name]["type"], JSONB)
                    for name in ("before_summary", "after_summary", "source_refs")
                )

                membership_fks = db_inspector.get_foreign_keys(
                    "farm_memberships", schema=schema
                )
                assert {
                    (tuple(fk["constrained_columns"]), fk["referred_table"], fk["options"]["ondelete"])
                    for fk in membership_fks
                } == {
                    (("account_id",), "accounts", "RESTRICT"),
                    (("farm_id",), "farms", "RESTRICT"),
                }
                assert connection.exec_driver_sql("SELECT count(*) FROM farms").scalar_one() == 0

                with Operations.context(context):
                    ft002.module.downgrade()
                assert {"farms", "plants", "plant_access_grants", "admin_audit_records"}.isdisjoint(
                    inspect(connection).get_table_names(schema=schema)
                )
            finally:
                outer.rollback()

        _exercise_one_and_multiple_legacy_paths(engine, script)
    finally:
        database.dispose()


def _exercise_one_and_multiple_legacy_paths(engine, script: ScriptDirectory) -> None:
    ft001 = script.get_revision("ft001_access_sessions")
    ft002 = script.get_revision("ft002_farm_plant_access")
    assert ft001 is not None and ft002 is not None
    for legacy_count in (1, 2):
        schema = f"task012_legacy_{legacy_count}_{uuid.uuid4().hex}"
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    ft001.module.upgrade()
                for item in range(legacy_count):
                    account_id = uuid.uuid4()
                    connection.exec_driver_sql(
                        "INSERT INTO accounts "
                        "(account_id, login_name, display_name, account_status, password_hash) "
                        "VALUES (%s, %s, %s, 'active', 'test-only-hash')",
                        (account_id, f"legacy-{item}", f"Legacy {item}"),
                    )
                    connection.exec_driver_sql(
                        "INSERT INTO farm_memberships "
                        "(membership_id, account_id, farm_id, role_preset, membership_status) "
                        "VALUES (%s, %s, %s, 'boss', 'active')",
                        (uuid.uuid4(), account_id, uuid.uuid4()),
                    )

                if legacy_count == 1:
                    legacy_farm_id = connection.exec_driver_sql(
                        "SELECT farm_id FROM farm_memberships"
                    ).scalar_one()
                    with Operations.context(context):
                        ft002.module.upgrade()
                    farm_row = connection.exec_driver_sql(
                        "SELECT farm_id, farm_key, display_name FROM farms"
                    ).one()
                    assert tuple(farm_row) == (
                        legacy_farm_id,
                        "local_farm",
                        "Local Farm",
                    )
                    assert connection.exec_driver_sql(
                        "SELECT count(*) FROM admin_audit_records "
                        "WHERE action_type = 'farm_created'"
                    ).scalar_one() == 1
                    with Operations.context(context):
                        with pytest.raises(RuntimeError, match="downgrade refused"):
                            ft002.module.downgrade()
                else:
                    with Operations.context(context):
                        with pytest.raises(RuntimeError, match="multiple legacy"):
                            ft002.module.upgrade()
                    assert "farms" not in inspect(connection).get_table_names(schema=schema)
            finally:
                outer.rollback()
