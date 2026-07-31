from __future__ import annotations

from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import BigInteger, Boolean, DateTime, Text, Uuid, inspect
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.database import build_database
from backend.app.photo_intake import PhotoCatalogItem
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
    "photo_catalog_items",
}


def test_ft005_models_match_native_uuid_and_catalog_contract():
    uuid_columns = [
        PhotoCatalogItem.__table__.c.photo_id,
        PhotoCatalogItem.__table__.c.farm_id,
        PhotoCatalogItem.__table__.c.plant_id,
        PhotoCatalogItem.__table__.c.check_in_id,
        PhotoCatalogItem.__table__.c.uploaded_by_account_id,
        PhotoCatalogItem.__table__.c.uploaded_by_membership_id,
    ]
    assert all(
        isinstance(column.type, Uuid) and column.type.as_uuid
        for column in uuid_columns
    )
    assert (
        PhotoCatalogItem.__table__.c.photo_id.default is not None
        and PhotoCatalogItem.__table__.c.photo_id.default.arg.__name__ == "uuid4"
    )
    assert isinstance(PhotoCatalogItem.__table__.c.size_bytes.type, BigInteger)
    assert isinstance(PhotoCatalogItem.__table__.c.local_only.type, Boolean)
    assert isinstance(PhotoCatalogItem.__table__.c.can_train_on.type, Boolean)

    database = build_database(AppSettings())
    try:
        assert isinstance(
            PhotoCatalogItem.__table__.c.event_refs.type.dialect_impl(
                database.engine().dialect
            ),
            JSONB,
        )
    finally:
        database.dispose()


    assert all(fk.ondelete == "RESTRICT" for fk in PhotoCatalogItem.__table__.foreign_keys)
    assert {constraint.name for constraint in PhotoCatalogItem.__table__.constraints if constraint.name} >= {
        "ck_photo_catalog_items_photo_type",
        "ck_photo_catalog_items_content_type",
        "ck_photo_catalog_items_size_bytes_range",
        "ck_photo_catalog_items_sha256_lower_hex",
        "ck_photo_catalog_items_original_file_ref_shape",
        "ck_photo_catalog_items_manifest_ref_shape",
        "ck_photo_catalog_items_source_refs_object",
        "ck_photo_catalog_items_event_refs_object",
        "ck_photo_catalog_items_local_only_true",
        "ck_photo_catalog_items_can_train_on_false",
    }


def test_ft005_revision_is_ordered_head_and_contains_guarded_downgrade():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    product_head = script.get_revision("head")
    assert product_head is not None
    assert product_head.revision == "ft013_decision_effects"
    assert product_head.down_revision == "ft008_lazy_introductions"
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

    ft008 = script.get_revision("ft008_agent_chat_ui_feed")
    assert ft008 is not None
    assert ft008.down_revision == "ft005_photo_intake"

    revision = script.get_revision("ft005_photo_intake")
    assert revision is not None
    assert revision.revision == "ft005_photo_intake"
    assert revision.down_revision == "ft004_plant_operations"

    source = Path(revision.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "photo_catalog_items" in source
    assert "downgrade refused" in source


def test_ft005_postgresql_migration_schema_and_guarded_downgrade():
    settings = AppSettings.from_env()
    database = build_database(settings)
    schema = f"task021_schema_{uuid.uuid4().hex}"

    try:
        engine = database.engine()
        assert engine.dialect.name == "postgresql", (
            "TASK-021 migration evidence requires configured PostgreSQL"
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        revisions = [
            script.get_revision("ft001_access_sessions"),
            script.get_revision("ft002_farm_plant_access"),
            script.get_revision("ft004_plant_operations"),
            script.get_revision("ft005_photo_intake"),
        ]
        assert all(revision is not None for revision in revisions)

        with engine.connect() as connection:
            outer = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    for revision in revisions:
                        revision.module.upgrade()

                db_inspector = inspect(connection)
                assert set(db_inspector.get_table_names(schema=schema)) == TASK_TABLES
                columns = {
                    item["name"]: item
                    for item in db_inspector.get_columns(
                        "photo_catalog_items",
                        schema=schema,
                    )
                }
                for name in {
                    "photo_id",
                    "farm_id",
                    "plant_id",
                    "check_in_id",
                    "uploaded_by_account_id",
                    "uploaded_by_membership_id",
                }:
                    assert isinstance(columns[name]["type"], Uuid)
                for name in {"captured_at", "uploaded_at", "created_at", "updated_at"}:
                    assert isinstance(columns[name]["type"], DateTime)
                    assert columns[name]["type"].timezone is True
                assert isinstance(columns["size_bytes"]["type"], BigInteger)
                assert isinstance(columns["original_file_ref"]["type"], Text)
                assert isinstance(columns["manifest_ref"]["type"], Text)
                assert isinstance(columns["local_only"]["type"], Boolean)
                assert isinstance(columns["can_train_on"]["type"], Boolean)
                assert all(
                    isinstance(columns[name]["type"], JSONB)
                    for name in ("source_refs", "event_refs")
                )

                fks = db_inspector.get_foreign_keys(
                    "photo_catalog_items",
                    schema=schema,
                )
                assert all(fk["options"]["ondelete"] == "RESTRICT" for fk in fks)

                with Operations.context(context):
                    revisions[-1].module.downgrade()
                assert "photo_catalog_items" not in inspect(connection).get_table_names(
                    schema=schema
                )
            finally:
                outer.rollback()
    finally:
        database.dispose()
