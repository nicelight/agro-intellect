from pathlib import Path
import uuid

import pytest
from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Uuid, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from backend.app import AppSettings, build_database
from backend.app.access_admin.models import Base
from backend.app.safety_gate import SafetyClassification
from backend.app.task_follow_up import (
    Approval,
    OrdinaryTaskDispatchDisposition,
    Outcome,
    Task,
    TaskFollowUpDispositionResultV1,
    TaskFollowUpRuntimeDisposition,
    TaskFollowUpRuntimeValidationError,
)
from backend.migrations import build_alembic_config


_WRITE_ONCE_FUNCTION = "ft012_enforce_ordinary_dispatch_commitment_write_once"
_WRITE_ONCE_TRIGGER = "trg_ordinary_task_dispatch_commitment_write_once"
_WRITE_ONCE_CONSTRAINT = "ck_ordinary_task_dispatch_commitment_write_once"


def _assert_write_once_violation(error: DBAPIError) -> None:
    assert getattr(error.orig, "sqlstate", None) == "23514"
    assert getattr(getattr(error.orig, "diag", None), "constraint_name", None) == (
        _WRITE_ONCE_CONSTRAINT
    )


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
            "AND t.relname = 'ordinary_task_dispatch_dispositions' "
            "AND g.tgname = :name AND NOT g.tgisinternal"
        ),
        {"name": _WRITE_ONCE_TRIGGER},
    ).scalar_one()
    return function_count, trigger_count


def test_ft012_runtime_disposition_is_exact_additive_head():
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    head = script.get_revision("head")
    assert head is not None
    assert head.revision == "ft012_runtime_dispositions"
    assert head.down_revision == "ft012_task_approval_outcomes"
    source = Path(head.path).read_text(encoding="utf-8")
    assert "ON DELETE CASCADE" not in source.upper()
    assert "ft012_task_approval_outcomes" in source
    assert "downgrade refused" in source
    assert "expected_task_create_fingerprint" in source
    assert "postgresql_not_valid=True" in source
    assert _WRITE_ONCE_FUNCTION in source
    assert _WRITE_ONCE_TRIGGER in source
    assert _WRITE_ONCE_CONSTRAINT in source
    assert "IS DISTINCT FROM" in source
    assert "23514" in source
    assert all(token not in source for token in (
        "device_command", "provider_payload", "target_value", "dosage", "schedule_at"
    ))


def test_models_have_native_uuid_restrictive_authority_shape():
    for model in (
        TaskFollowUpRuntimeDisposition,
        OrdinaryTaskDispatchDisposition,
        Approval,
        Task,
        Outcome,
    ):
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
    assert {
        constraint.name
        for constraint in OrdinaryTaskDispatchDisposition.__table__.constraints
        if constraint.name
    } >= {
        "pk_ordinary_task_dispatch_dispositions",
        "uq_ordinary_task_dispatch_dispositions_run",
        "ck_ordinary_task_dispatch_dispositions_input_sha256",
        "ck_ordinary_task_dispatch_dispositions_terminal_matrix",
        "ck_ordinary_task_dispatch_dispositions_commitment_matrix",
    }
    assert {
        constraint.name
        for constraint in TaskFollowUpRuntimeDisposition.__table__.constraints
        if constraint.name
    } >= {
        "pk_task_follow_up_runtime_dispositions",
        "uq_task_follow_up_runtime_dispositions_message",
        "ck_task_follow_up_runtime_dispositions_command_sha256",
        "ck_task_follow_up_runtime_dispositions_terminal_matrix",
    }


def test_task_local_disposition_result_has_exact_seven_branch_matrix():
    run_id = uuid.uuid4()
    classification_ref = f"safety_classification:{uuid.uuid4()}"
    task_ref = f"task:{uuid.uuid4()}"
    cases = (
        ("conflict", "TASK_FOLLOW_UP_RUN_CONFLICT", None, None),
        ("failed", "TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED", None, None),
        ("incomplete", "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE", None, None),
        (
            "incomplete",
            "TASK_FOLLOW_UP_HANDOFF_INCOMPLETE",
            classification_ref,
            None,
        ),
        (
            "not_taskable",
            "TASK_FOLLOW_UP_ALREADY_NOT_TASKABLE",
            classification_ref,
            None,
        ),
        (
            "denied",
            "TASK_FOLLOW_UP_DISPATCH_DENIED",
            classification_ref,
            None,
        ),
        (
            "duplicate",
            "TASK_FOLLOW_UP_ALREADY_CONSUMED",
            classification_ref,
            task_ref,
        ),
        ("blocked", "TASK_FOLLOW_UP_REPLAY_BLOCKED", None, None),
    )
    for status, code, classification, task in cases:
        value = TaskFollowUpDispositionResultV1(
            run_id=run_id,
            result_status=status,
            result_code=code,
            classification_ref=classification,
            task_ref=task,
        )
        assert value.retry_requires_new_run is True
        assert value.as_value()["result_code"] == code
    with pytest.raises(TaskFollowUpRuntimeValidationError):
        TaskFollowUpDispositionResultV1(
            run_id=run_id,
            result_status="duplicate",
            result_code="TASK_FOLLOW_UP_ALREADY_CONSUMED",
            classification_ref=classification_ref,
            task_ref=None,
        )


def test_postgresql_migration_creates_exact_relations(ft012_database):
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            script.get_revision("ft012_runtime_dispositions").module.upgrade()
        connection.commit()
    inspector = inspect(ft012_database.engine())
    assert {
        "task_follow_up_runtime_dispositions",
        "ordinary_task_dispatch_dispositions",
        "approvals",
        "tasks",
        "outcomes",
    } <= set(inspector.get_table_names())
    for model in (
        TaskFollowUpRuntimeDisposition,
        OrdinaryTaskDispatchDisposition,
        Approval,
        Task,
        Outcome,
    ):
        table = model.__table__
        assert {item["name"] for item in inspector.get_columns(table.name)} == {
            column.name for column in table.c
        }
        assert all(
            item["options"]["ondelete"] == "RESTRICT"
            for item in inspector.get_foreign_keys(table.name)
        )
    disposition_checks = {
        item["name"]
        for item in inspector.get_check_constraints(
            "ordinary_task_dispatch_dispositions"
        )
    }
    assert disposition_checks >= {
        "ck_ordinary_task_dispatch_dispositions_input_sha256",
        "ck_ordinary_task_dispatch_dispositions_outcome",
        "ck_ordinary_task_dispatch_dispositions_denial_code",
        "ck_ordinary_task_dispatch_dispositions_terminal_matrix",
        "ck_ordinary_task_dispatch_dispositions_commitment_matrix",
    }
    runtime_checks = {
        item["name"]
        for item in inspector.get_check_constraints(
            "task_follow_up_runtime_dispositions"
        )
    }
    assert runtime_checks >= {
        "ck_task_follow_up_runtime_dispositions_command_sha256",
        "ck_task_follow_up_runtime_dispositions_input_sha256",
        "ck_task_follow_up_runtime_dispositions_outcome",
        "ck_task_follow_up_runtime_dispositions_denial_code",
        "ck_task_follow_up_runtime_dispositions_event_ref_object",
        "ck_task_follow_up_runtime_dispositions_terminal_matrix",
    }
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (1, 1)
        trigger_definition = connection.execute(
            text(
                "SELECT pg_get_triggerdef(g.oid) FROM pg_trigger g "
                "JOIN pg_class t ON t.oid = g.tgrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = current_schema() "
                "AND t.relname = 'ordinary_task_dispatch_dispositions' "
                "AND g.tgname = :name AND NOT g.tgisinternal"
            ),
            {"name": _WRITE_ONCE_TRIGGER},
        ).scalar_one()
    assert "BEFORE UPDATE OF expected_task_create_fingerprint" in trigger_definition


def test_fresh_orm_schema_installs_write_once_objects_once(ft012_database):
    schema = f"task040_fresh_orm_{uuid.uuid4().hex}"
    engine = ft012_database.engine()
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            Base.metadata.create_all(connection, checkfirst=True)
            Base.metadata.create_all(connection, checkfirst=True)
            assert connection.execute(text("SELECT current_schema()" )).scalar_one() == schema
            assert _write_once_object_counts(connection) == (1, 1)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


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
                "ft012_runtime_dispositions"
            )
            assert _write_once_object_counts(connection) == (1, 1)
    finally:
        if scoped_database is not None:
            scoped_database.dispose()
        with base_database.engine().begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        base_database.dispose()


def test_additive_commitment_keeps_legacy_null_untrusted_and_enforces_new_rows(
    ft012_database,
    ft012_seed,
):
    farm, _boss, _membership, plant = ft012_seed
    message_ids = [uuid.uuid4() for _index in range(3)]
    with ft012_database.session() as session, session.begin():
        for message_id in message_ids:
            session.add(
                SafetyClassification(
                    message_id=message_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    origin_agent_id="task_follow_up",
                    classifier_version="safety_gate_v1",
                    classification="safe_task_request",
                    safe_task_kind="check",
                    reason_code="safe_check_request",
                    physical_action_kind=None,
                    provider_status="completed",
                    model_ref="test_provider:safety_gate_v1",
                    input_sha256="a" * 64,
                    result_sha256="b" * 64,
                )
            )
    legacy_run = uuid.uuid4()
    with ft012_database.engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ordinary_task_dispatch_dispositions "
                "(classification_message_id, run_id, farm_id, plant_id, "
                "input_sha256, outcome, denial_code) "
                "VALUES (:message_id, :run_id, :farm_id, :plant_id, "
                ":input_sha256, 'consumed', NULL)"
            ),
            {
                "message_id": message_ids[0],
                "run_id": legacy_run,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "input_sha256": "c" * 64,
            },
        )

    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft012_runtime_dispositions")
    assert revision is not None
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
        connection.commit()

    inspector = inspect(ft012_database.engine())
    column = next(
        item
        for item in inspector.get_columns("ordinary_task_dispatch_dispositions")
        if item["name"] == "expected_task_create_fingerprint"
    )
    assert column["nullable"] is True
    with ft012_database.engine().connect() as connection:
        assert connection.execute(
            text(
                "SELECT expected_task_create_fingerprint "
                "FROM ordinary_task_dispatch_dispositions "
                "WHERE run_id = :run_id"
            ),
            {"run_id": legacy_run},
        ).scalar_one() is None
        assert connection.execute(
            text(
                "SELECT convalidated FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN pg_namespace n ON n.oid = t.relnamespace "
                "WHERE n.nspname = current_schema() "
                "AND t.relname = 'ordinary_task_dispatch_dispositions' "
                "AND c.conname = "
                "'ck_ordinary_task_dispatch_dispositions_commitment_matrix'"
            )
        ).scalar_one() is False

    with ft012_database.engine().connect() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(
                text(
                    "INSERT INTO ordinary_task_dispatch_dispositions "
                    "(classification_message_id, run_id, farm_id, plant_id, "
                    "input_sha256, outcome, denial_code, "
                    "expected_task_create_fingerprint) "
                    "VALUES (:message_id, :run_id, :farm_id, :plant_id, "
                    ":input_sha256, 'consumed', NULL, NULL)"
                ),
                {
                    "message_id": message_ids[1],
                    "run_id": uuid.uuid4(),
                    "farm_id": farm.farm_id,
                    "plant_id": plant.plant_id,
                    "input_sha256": "c" * 64,
                },
            )
        connection.rollback()

    denied_run = uuid.uuid4()
    consumed_run = uuid.uuid4()
    with ft012_database.engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO ordinary_task_dispatch_dispositions "
                "(classification_message_id, run_id, farm_id, plant_id, "
                "input_sha256, outcome, denial_code, "
                "expected_task_create_fingerprint) "
                "VALUES (:message_id, :run_id, :farm_id, :plant_id, "
                ":input_sha256, 'consumed', NULL, :fingerprint)"
            ),
            {
                "message_id": message_ids[1],
                "run_id": consumed_run,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "input_sha256": "d" * 64,
                "fingerprint": "e" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO ordinary_task_dispatch_dispositions "
                "(classification_message_id, run_id, farm_id, plant_id, "
                "input_sha256, outcome, denial_code, "
                "expected_task_create_fingerprint) "
                "VALUES (:message_id, :run_id, :farm_id, :plant_id, "
                ":input_sha256, 'denied', 'TASK_COMMAND_FORBIDDEN', NULL)"
            ),
            {
                "message_id": message_ids[2],
                "run_id": denied_run,
                "farm_id": farm.farm_id,
                "plant_id": plant.plant_id,
                "input_sha256": "f" * 64,
            },
        )

    distinct_updates = (
        (consumed_run, "a" * 64),
        (consumed_run, None),
        (denied_run, "b" * 64),
        (legacy_run, "c" * 64),
    )
    with ft012_database.engine().connect() as connection:
        for run_id, replacement in distinct_updates:
            with pytest.raises(DBAPIError) as rejected:
                connection.execute(
                    text(
                        "UPDATE ordinary_task_dispatch_dispositions "
                        "SET expected_task_create_fingerprint = :fingerprint "
                        "WHERE run_id = :run_id"
                    ),
                    {"fingerprint": replacement, "run_id": run_id},
                )
            _assert_write_once_violation(rejected.value)
            connection.rollback()

    with ft012_database.engine().begin() as connection:
        same_value = connection.execute(
            text(
                "UPDATE ordinary_task_dispatch_dispositions "
                "SET expected_task_create_fingerprint = :fingerprint "
                "WHERE run_id = :run_id"
            ),
            {"fingerprint": "e" * 64, "run_id": consumed_run},
        )
        unrelated = connection.execute(
            text(
                "UPDATE ordinary_task_dispatch_dispositions "
                "SET recorded_at = recorded_at WHERE run_id = :run_id"
            ),
            {"run_id": consumed_run},
        )
        denied_same_null = connection.execute(
            text(
                "UPDATE ordinary_task_dispatch_dispositions "
                "SET expected_task_create_fingerprint = NULL "
                "WHERE run_id = :run_id"
            ),
            {"run_id": denied_run},
        )
    assert (same_value.rowcount, unrelated.rowcount, denied_same_null.rowcount) == (
        1,
        1,
        1,
    )

    with ft012_database.engine().connect() as connection:
        with pytest.raises(DBAPIError) as legacy_rewrite:
            connection.execute(
                text(
                    "UPDATE ordinary_task_dispatch_dispositions "
                    "SET recorded_at = recorded_at WHERE run_id = :run_id"
                ),
                {"run_id": legacy_run},
            )
        assert getattr(
            getattr(legacy_rewrite.value.orig, "diag", None),
            "constraint_name",
            None,
        ) == "ck_ordinary_task_dispatch_dispositions_commitment_matrix"
        connection.rollback()

    with ft012_database.engine().connect() as connection:
        rows = {
            run_id: fingerprint
            for run_id, fingerprint in connection.execute(
                text(
                    "SELECT run_id, expected_task_create_fingerprint "
                    "FROM ordinary_task_dispatch_dispositions "
                    "WHERE run_id IN (:consumed_run, :denied_run, :legacy_run)"
                ),
                {
                    "consumed_run": consumed_run,
                    "denied_run": denied_run,
                    "legacy_run": legacy_run,
                },
            ).tuples()
        }
    assert rows == {
        consumed_run: "e" * 64,
        denied_run: None,
        legacy_run: None,
    }


def test_empty_runtime_downgrade_removes_only_additive_authority(
    ft012_database,
):
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft012_runtime_dispositions")
    assert revision is not None
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
            revision.module.downgrade()
        connection.commit()
    inspector = inspect(ft012_database.engine())
    assert "task_follow_up_runtime_dispositions" not in inspector.get_table_names()
    assert "expected_task_create_fingerprint" not in {
        item["name"]
        for item in inspector.get_columns("ordinary_task_dispatch_dispositions")
    }
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (0, 0)


def test_runtime_downgrade_refuses_while_immutable_authority_exists(
    ft012_database,
    ft012_seed,
):
    farm, _boss, _membership, plant = ft012_seed
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft012_runtime_dispositions")
    assert revision is not None
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
        connection.commit()
    with ft012_database.session() as session, session.begin():
        event_id = uuid.uuid4()
        session.add(
            TaskFollowUpRuntimeDisposition(
                run_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                command_sha256="a" * 64,
                outcome="publication_denied",
                message_id=None,
                input_sha256=None,
                denial_code="AGENT_PUBLICATION_BLOCKED",
                model_ref="test_provider:task_follow_up_v1",
                runtime_event_ref={
                    "timeline_event_id": str(event_id),
                    "timeline_ref": f"timeline.jsonl#{event_id}",
                    "event_type": "agent_runtime_decided",
                    "created_at": "2026-07-20T08:00:00+00:00",
                },
            )
        )
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context), pytest.raises(
            RuntimeError,
            match="downgrade refused",
        ):
            revision.module.downgrade()
        connection.rollback()
    inspector = inspect(ft012_database.engine())
    assert "task_follow_up_runtime_dispositions" in inspector.get_table_names()
    assert "expected_task_create_fingerprint" in {
        item["name"]
        for item in inspector.get_columns("ordinary_task_dispatch_dispositions")
    }
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (1, 1)


def test_runtime_downgrade_refuses_non_null_commitment_without_runtime_row(
    ft012_database,
    ft012_seed,
):
    farm, _boss, _membership, plant = ft012_seed
    script = ScriptDirectory.from_config(build_alembic_config(AppSettings()))
    revision = script.get_revision("ft012_runtime_dispositions")
    assert revision is not None
    with ft012_database.engine().connect() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()
        connection.commit()

    message_id = uuid.uuid4()
    with ft012_database.session() as session, session.begin():
        session.add(
            SafetyClassification(
                message_id=message_id,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                origin_agent_id="task_follow_up",
                classifier_version="safety_gate_v1",
                classification="safe_task_request",
                safe_task_kind="check",
                reason_code="safe_check_request",
                physical_action_kind=None,
                provider_status="completed",
                model_ref="test_provider:safety_gate_v1",
                input_sha256="a" * 64,
                result_sha256="b" * 64,
            )
        )
        session.add(
            OrdinaryTaskDispatchDisposition(
                classification_message_id=message_id,
                run_id=uuid.uuid4(),
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                input_sha256="c" * 64,
                outcome="consumed",
                expected_task_create_fingerprint="d" * 64,
                denial_code=None,
            )
        )

    with ft012_database.engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM task_follow_up_runtime_dispositions")
        ).scalar_one() == 0
        context = MigrationContext.configure(connection)
        with Operations.context(context), pytest.raises(
            RuntimeError,
            match="downgrade refused",
        ):
            revision.module.downgrade()
        connection.rollback()

    inspector = inspect(ft012_database.engine())
    assert "task_follow_up_runtime_dispositions" in inspector.get_table_names()
    assert "expected_task_create_fingerprint" in {
        item["name"]
        for item in inspector.get_columns("ordinary_task_dispatch_dispositions")
    }
    with ft012_database.engine().connect() as connection:
        assert _write_once_object_counts(connection) == (1, 1)
