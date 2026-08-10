from __future__ import annotations

from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, Enum, Uuid, inspect, text
from sqlalchemy.dialects.postgresql import JSONB

from backend.app import AppSettings
from backend.app.dataset_governance import DatasetCandidate
from backend.app.database import build_database
from backend.migrations import build_alembic_config

_TABLE = "dataset_candidates"

_ENUM_COLUMNS = {
    "candidate_status": "dataset_candidate_status",
    "candidate_origin": "dataset_candidate_origin",
    "quality_tier": "dataset_quality_tier",
    "split": "dataset_split",
    "confirmation_source": "dataset_confirmation_source",
    "source_kind": "dataset_source_kind",
    "curator_decision": "dataset_curator_decision",
}

_CHECK_NAMES = {
    "ck_dataset_candidates_evidence_refs",
    "ck_dataset_candidates_event_refs",
    "ck_dataset_candidates_curator_identity",
    "ck_dataset_candidates_gold_guard",
    "ck_dataset_candidates_trainability_guard",
    "ck_dataset_candidates_record_version",
}


def test_dataset_candidate_model_has_native_uuid_restrictive_aggregate_shape():
    table = DatasetCandidate.__table__
    assert table.name == _TABLE
    uuid_columns = [column for column in table.c if column.name.endswith("_id")]
    assert uuid_columns
    assert all(
        isinstance(column.type, Uuid) and column.type.as_uuid
        for column in uuid_columns
    )
    assert all(
        foreign_key.ondelete == "RESTRICT"
        for foreign_key in table.foreign_keys
    )
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert _CHECK_NAMES <= check_names
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if getattr(constraint, "name", None)
        and isinstance(constraint.name, str)
        and constraint.name.startswith("uq_dataset_candidates")
    }
    assert {
        "uq_dataset_candidates_source_identity",
        "uq_dataset_candidates_curator_run",
    } <= unique_names
    for column in table.c:
        if column.name in _ENUM_COLUMNS:
            assert isinstance(column.type, Enum)
            assert column.type.name == _ENUM_COLUMNS[column.name]


def test_dataset_candidate_json_columns_are_postgresql_native():
    database = build_database(AppSettings())
    try:
        dialect = database.engine().dialect
    finally:
        database.dispose()
    for column in (DatasetCandidate.__table__.c.evidence_refs,
                   DatasetCandidate.__table__.c.event_refs):
        assert isinstance(column.type.dialect_impl(dialect), JSONB)


def test_ft014_revision_is_exact_guarded_linear_product_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft014_dataset_candidates"
    assert head.down_revision == "ft013_decision_effects"
    assert script.get_heads() == ["ft014_dataset_candidates"]
    source = Path(head.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert all(
        name in source
        for name in (
            "uq_dataset_candidates_source_identity",
            "uq_dataset_candidates_curator_run",
            "ck_dataset_candidates_evidence_refs",
            "ck_dataset_candidates_curator_identity",
            "ck_dataset_candidates_gold_guard",
            "ck_dataset_candidates_trainability_guard",
            "dataset_candidate_status",
            "dataset_candidate_origin",
            "dataset_quality_tier",
            "dataset_split",
            "dataset_confirmation_source",
            "dataset_source_kind",
            "dataset_curator_decision",
        )
    )
    assert all(
        forbidden not in source
        for forbidden in (
            "provider_payload",
            "raw_chat",
            "device_command",
            "can_train_on = true",
            "ON DELETE CASCADE",
        )
    )


def test_ft014_migration_creates_complete_empty_aggregate(ft014_database):
    inspector = inspect(ft014_database.engine())
    assert _TABLE in inspector.get_table_names()
    catalog_columns = {
        column["name"] for column in inspector.get_columns(_TABLE)
    }
    assert catalog_columns == {column.name for column in DatasetCandidate.__table__.c}
    catalog_types = {
        column["name"]: column["type"] for column in inspector.get_columns(_TABLE)
    }
    for column, type_name in _ENUM_COLUMNS.items():
        assert catalog_types[column].name == type_name
    assert all(
        foreign_key["options"]["ondelete"] == "RESTRICT"
        for foreign_key in inspector.get_foreign_keys(_TABLE)
    )
    check_names = {
        item["name"] for item in inspector.get_check_constraints(_TABLE)
    }
    assert _CHECK_NAMES <= check_names
    unique_names = {
        item["name"] for item in inspector.get_unique_constraints(_TABLE)
    }
    assert {
        "uq_dataset_candidates_source_identity",
        "uq_dataset_candidates_curator_run",
    } <= unique_names
    with ft014_database.engine().connect() as connection:
        enum_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT typname FROM pg_type "
                    "WHERE typtype = 'e' AND typname LIKE 'dataset_%'"
                )
            )
        }
        assert set(_ENUM_COLUMNS.values()) <= enum_names
        assert connection.execute(
            text("SELECT count(*) FROM dataset_candidates")
        ).scalar_one() == 0


def test_ft014_migration_upgrade_downgrade_roundtrip(ft014_pre_migration_database):
    database = ft014_pre_migration_database
    inspector = inspect(database.engine())
    assert _TABLE not in inspector.get_table_names()

    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft014_dataset_candidates")
    with database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
        connection.commit()

    inspector = inspect(database.engine())
    assert _TABLE in inspector.get_table_names()
    with database.engine().connect() as connection:
        enum_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT typname FROM pg_type "
                    "WHERE typtype = 'e' AND typname LIKE 'dataset_%'"
                )
            )
        }
        assert set(_ENUM_COLUMNS.values()) <= enum_names

    with database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.downgrade()
        connection.commit()

    inspector = inspect(database.engine())
    assert _TABLE not in inspector.get_table_names()
    with database.engine().connect() as connection:
        enum_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT typname FROM pg_type "
                    "WHERE typtype = 'e' AND typname LIKE 'dataset_%'"
                )
            )
        }
        assert set(_ENUM_COLUMNS.values()).isdisjoint(enum_names)
