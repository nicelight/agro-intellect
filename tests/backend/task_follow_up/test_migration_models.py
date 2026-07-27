from pathlib import Path
import uuid

import pytest
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Uuid, inspect, text
from sqlalchemy.engine import make_url

from backend.app import AppSettings, build_database
from backend.app.access_admin.models import Base
from backend.app.task_follow_up import (
    Approval,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    Task,
    TaskFollowUpInvocationResultV1,
    TaskFollowUpRunResultV1,
)
from backend.migrations import build_alembic_config


_RUNTIME_TABLE = "task_follow_up_runtime_dispositions"
_DISPATCH_TABLE = "ordinary_task_dispatch_dispositions"
_COMMITMENT_COLUMN = "expected_task_create_fingerprint"
_COMMITMENT_CHECK = (
    "ck_ordinary_task_dispatch_dispositions_commitment_matrix"
)
_WRITE_ONCE_FUNCTION = "ft012_enforce_ordinary_dispatch_commitment_write_once"
_WRITE_ONCE_TRIGGER = "trg_ordinary_task_dispatch_commitment_write_once"


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(build_alembic_config(AppSettings()))


def _apply(database, *revision_ids: str) -> None:
    script = _script()
    with database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            for revision_id in revision_ids:
                script.get_revision(revision_id).module.upgrade()
        connection.commit()


def _cleanup_downgrade(database) -> None:
    revision = _script().get_revision(
        "ft012_simplify_follow_up_runtime"
    )
    with database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.downgrade()
        connection.commit()


def _write_once_object_counts(connection) -> tuple[int, int]:
    function_count = connection.execute(
        text(
            "SELECT count(*) FROM pg_proc p "
            "JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = current_schema() AND p.proname = :name "
            "AND pg_get_function_identity_arguments(p.oid) = ''"
        ),
        {"name": _WRITE_ONCE_FUNCTION},
    ).scalar_one()
    trigger_count = connection.execute(
        text(
            "SELECT count(*) FROM pg_trigger g "
            "JOIN pg_class t ON t.oid = g.tgrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            "WHERE n.nspname = current_schema() "
            f"AND t.relname = '{_DISPATCH_TABLE}' "
            "AND g.tgname = :name AND NOT g.tgisinternal"
        ),
        {"name": _WRITE_ONCE_TRIGGER},
    ).scalar_one()
    return function_count, trigger_count


def _active_schema_shape(database) -> tuple[set[str], set[str], set[str]]:
    inspector = inspect(database.engine())
    tables = set(inspector.get_table_names())
    columns = {
        column["name"] for column in inspector.get_columns(_DISPATCH_TABLE)
    }
    checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints(_DISPATCH_TABLE)
    }
    return tables, columns, checks


def test_cleanup_revision_is_exact_head_after_retained_ft013():
    script = _script()
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft012_simplify_follow_up_runtime"
    assert head.down_revision == "ft013_governance_aggregate"

    retained = script.get_revision("ft013_governance_aggregate")
    historical = script.get_revision("ft012_runtime_dispositions")
    assert retained.down_revision == "ft012_runtime_dispositions"
    assert historical.down_revision == "ft012_task_approval_outcomes"

    cleanup_source = Path(head.path).read_text(encoding="utf-8")
    assert "SELECT EXISTS" in cleanup_source
    assert _RUNTIME_TABLE in cleanup_source
    assert _COMMITMENT_COLUMN in cleanup_source
    assert _WRITE_ONCE_FUNCTION in cleanup_source
    assert _WRITE_ONCE_TRIGGER in cleanup_source
    assert "drop_table" in cleanup_source
    assert all(
        token not in cleanup_source
        for token in (
            "device_command",
            "provider_payload",
            "target_value",
            "dosage",
            "schedule_at",
        )
    )


def test_fresh_models_omit_runtime_ledger_commitment_and_result_union():
    assert _RUNTIME_TABLE not in Base.metadata.tables
    assert _COMMITMENT_COLUMN not in {
        column.name for column in OrdinaryTaskDispatchDisposition.__table__.c
    }
    assert _COMMITMENT_CHECK not in {
        constraint.name
        for constraint in OrdinaryTaskDispatchDisposition.__table__.constraints
        if constraint.name
    }
    assert TaskFollowUpInvocationResultV1 is TaskFollowUpRunResultV1

    for model in (OrdinaryTaskDispatchDisposition, Approval, Task, Outcome):
        table = model.__table__
        uuid_columns = [
            column
            for column in table.c
            if column.name.endswith("_id")
            and column.name != "created_by_agent_id"
        ]
        assert uuid_columns
        assert all(
            isinstance(column.type, Uuid) and column.type.as_uuid
            for column in uuid_columns
        )
        assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in table.foreign_keys)
        assert all(
            column.type.timezone
            for column in table.c
            if isinstance(column.type, DateTime)
        )


def test_empty_historical_runtime_upgrade_removes_only_redundant_authority(
    ft012_database,
):
    _apply(ft012_database, "ft012_runtime_dispositions")
    tables, columns, checks = _active_schema_shape(ft012_database)
    assert _RUNTIME_TABLE in tables
    assert _COMMITMENT_COLUMN in columns
    assert _COMMITMENT_CHECK in checks
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (1, 1)

    _apply(ft012_database, "ft012_simplify_follow_up_runtime")

    tables, columns, checks = _active_schema_shape(ft012_database)
    assert _RUNTIME_TABLE not in tables
    assert _COMMITMENT_COLUMN not in columns
    assert _COMMITMENT_CHECK not in checks
    assert {"approvals", "tasks", "outcomes", _DISPATCH_TABLE} <= tables
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (0, 0)


def test_populated_runtime_refuses_before_any_cleanup_ddl(
    ft012_database,
    ft012_seed,
):
    farm, _boss, _membership, plant = ft012_seed
    _apply(ft012_database, "ft012_runtime_dispositions")
    with ft012_database.engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO task_follow_up_runtime_dispositions "
                "(run_id, farm_id, plant_id, command_sha256, outcome, "
                "message_id, input_sha256, denial_code, model_ref, "
                "runtime_event_ref) "
                "VALUES (:run_id, :farm_id, :plant_id, :command_sha256, "
                "'publication_denied', NULL, NULL, "
                "'AGENT_PUBLICATION_BLOCKED', :model_ref, '{}'::jsonb)"
            ),
            {
                "run_id": uuid.uuid4(),
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "command_sha256": "a" * 64,
                "model_ref": "test_provider:task_follow_up_v1",
            },
        )

    revision = _script().get_revision(
        "ft012_simplify_follow_up_runtime"
    )
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            with pytest.raises(RuntimeError, match="contains historical authority"):
                revision.module.upgrade()
        connection.rollback()

    tables, columns, checks = _active_schema_shape(ft012_database)
    assert _RUNTIME_TABLE in tables
    assert _COMMITMENT_COLUMN in columns
    assert _COMMITMENT_CHECK in checks
    with ft012_database.engine().connect() as connection:
        assert connection.execute(
            text(f"SELECT count(*) FROM {_RUNTIME_TABLE}")
        ).scalar_one() == 1
        assert _write_once_object_counts(connection) == (1, 1)


def test_cleanup_downgrade_restores_historical_schema_and_reupgrades(
    ft012_database,
):
    _apply(
        ft012_database,
        "ft012_runtime_dispositions",
        "ft012_simplify_follow_up_runtime",
    )
    _cleanup_downgrade(ft012_database)

    tables, columns, checks = _active_schema_shape(ft012_database)
    assert _RUNTIME_TABLE in tables
    assert _COMMITMENT_COLUMN in columns
    assert _COMMITMENT_CHECK in checks
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (1, 1)

    _apply(ft012_database, "ft012_simplify_follow_up_runtime")
    tables, columns, checks = _active_schema_shape(ft012_database)
    assert _RUNTIME_TABLE not in tables
    assert _COMMITMENT_COLUMN not in columns
    assert _COMMITMENT_CHECK not in checks
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (0, 0)


def test_fresh_orm_schema_omits_removed_objects(ft012_database):
    schema = f"task040_fresh_orm_{uuid.uuid4().hex}"
    engine = ft012_database.engine()
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            Base.metadata.create_all(connection, checkfirst=True)
            inspector = inspect(connection)
            assert _RUNTIME_TABLE not in inspector.get_table_names()
            assert _COMMITMENT_COLUMN not in {
                column["name"]
                for column in inspector.get_columns(_DISPATCH_TABLE)
            }
            assert _write_once_object_counts(connection) == (0, 0)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'
            )


def test_alembic_current_head_upgrade_is_idempotent(ft012_database):
    schema = f"task040_alembic_head_{uuid.uuid4().hex}"
    base_settings = AppSettings.from_env()
    base_database = build_database(base_settings)
    scoped_database = None
    try:
        with base_database.engine().begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        scoped_url = make_url(base_settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema}"}
        )
        scoped_settings = base_settings.model_copy(
            update={
                "database_url": scoped_url.render_as_string(hide_password=False)
            }
        )
        scoped_database = build_database(scoped_settings)
        config = build_alembic_config(base_settings)
        config.set_main_option(
            "sqlalchemy.url",
            scoped_settings.database_url.replace("%", "%%"),
        )
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        with scoped_database.engine().connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() == (
                "ft012_simplify_follow_up_runtime"
            )
            inspector = inspect(connection)
            assert _RUNTIME_TABLE not in inspector.get_table_names()
            assert _COMMITMENT_COLUMN not in {
                column["name"]
                for column in inspector.get_columns(_DISPATCH_TABLE)
            }
            assert "companion_issues" in inspector.get_table_names()
            assert _write_once_object_counts(connection) == (0, 0)
    finally:
        if scoped_database is not None:
            scoped_database.dispose()
        with base_database.engine().begin() as connection:
            connection.exec_driver_sql(
                f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'
            )
        base_database.dispose()
