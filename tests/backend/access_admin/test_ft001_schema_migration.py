from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import DateTime, Text, Uuid, delete, inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from backend.app import AppSettings
from backend.app.access_admin import (
    Account,
    FarmMembership,
    LocalSession,
    normalize_login_name,
)
from backend.app.database import build_database
from backend.migrations import build_alembic_config


TASK_TABLES = {"accounts", "farm_memberships", "local_sessions"}


def _assert_integrity_error(connection: Connection, statement) -> None:
    savepoint = connection.begin_nested()
    try:
        with pytest.raises(IntegrityError):
            connection.execute(statement)
    finally:
        savepoint.rollback()


def _columns_by_name(db_inspector, table_name: str, schema: str):
    return {
        column["name"]: column
        for column in db_inspector.get_columns(table_name, schema=schema)
    }


def test_models_use_canonical_uuid_identity_and_digest_only_session_storage():
    assert normalize_login_name("  Boss.Admin  ") == "boss.admin"
    account = Account(
        login_name="  Boss.Admin  ",
        display_name="Boss Admin",
        account_status="active",
        password_hash="test-only-hash",
    )
    assert account.login_name == "boss.admin"

    uuid_columns = [
        Account.__table__.c.account_id,
        FarmMembership.__table__.c.membership_id,
        FarmMembership.__table__.c.account_id,
        FarmMembership.__table__.c.farm_id,
        LocalSession.__table__.c.session_id,
        LocalSession.__table__.c.account_id,
    ]
    assert all(isinstance(column.type, Uuid) for column in uuid_columns)
    assert all(column.type.as_uuid for column in uuid_columns)
    id_defaults = [
        Account.__table__.c.account_id.default.arg,
        FarmMembership.__table__.c.membership_id.default.arg,
        LocalSession.__table__.c.session_id.default.arg,
    ]
    assert all(callable(default) for default in id_defaults)
    assert all(default.__name__ == "uuid4" for default in id_defaults)

    assert set(LocalSession.__table__.c.keys()) == {
        "session_id",
        "account_id",
        "token_hash",
        "created_at",
        "expires_at",
        "revoked_at",
        "last_seen_at",
        "auth_method",
        "client_label",
    }
    assert {
        "raw_session_token",
        "password",
        "cookie",
        "bearer",
        "authorization",
    }.isdisjoint(LocalSession.__table__.c.keys())


def test_ft001_revision_is_postgresql_native_and_rollback_scoped():
    settings = AppSettings.from_env()
    database = build_database(settings)
    schema = f"task005_{uuid.uuid4().hex}"

    try:
        engine = database.engine()
        assert engine.dialect.name == "postgresql", (
            "TASK-005 schema evidence requires configured PostgreSQL"
        )

        config = build_alembic_config(settings)
        script = ScriptDirectory.from_config(config)
        script_revision = script.get_revision("head")
        assert script_revision is not None
        assert script_revision.revision == "ft001_access_sessions"

        with engine.connect() as connection:
            outer_transaction = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(
                    f'SET LOCAL search_path TO "{schema}", public'
                )
                migration_context = MigrationContext.configure(connection)

                with Operations.context(migration_context):
                    script_revision.module.upgrade()

                db_inspector = inspect(connection)
                assert set(db_inspector.get_table_names(schema=schema)) == TASK_TABLES
                assert {"farms", "plants", "plant_access_grants"}.isdisjoint(
                    db_inspector.get_table_names(schema=schema)
                )

                account_columns = _columns_by_name(db_inspector, "accounts", schema)
                membership_columns = _columns_by_name(
                    db_inspector,
                    "farm_memberships",
                    schema,
                )
                session_columns = _columns_by_name(
                    db_inspector,
                    "local_sessions",
                    schema,
                )

                for column in [
                    account_columns["account_id"],
                    membership_columns["membership_id"],
                    membership_columns["account_id"],
                    membership_columns["farm_id"],
                    session_columns["session_id"],
                    session_columns["account_id"],
                ]:
                    assert isinstance(column["type"], Uuid)
                    assert column["type"].as_uuid is True
                    assert column["nullable"] is False

                for table_columns, names in [
                    (
                        account_columns,
                        ["created_at", "updated_at", "disabled_at"],
                    ),
                    (
                        membership_columns,
                        ["created_at", "updated_at", "disabled_at"],
                    ),
                    (
                        session_columns,
                        ["created_at", "expires_at", "revoked_at", "last_seen_at"],
                    ),
                ]:
                    for name in names:
                        assert isinstance(table_columns[name]["type"], DateTime)
                        assert table_columns[name]["type"].timezone is True

                assert isinstance(account_columns["password_hash"]["type"], Text)
                assert account_columns["password_hash"]["nullable"] is False
                assert session_columns["token_hash"]["type"].length == 64
                assert session_columns["token_hash"]["nullable"] is False
                assert account_columns["created_at"]["default"] is not None
                assert account_columns["updated_at"]["default"] is not None
                assert membership_columns["created_at"]["default"] is not None
                assert membership_columns["updated_at"]["default"] is not None
                assert session_columns["created_at"]["default"] is not None

                assert {
                    item["name"]
                    for item in db_inspector.get_check_constraints(
                        "accounts",
                        schema=schema,
                    )
                } == {
                    "ck_accounts_account_status",
                    "ck_accounts_login_name_canonical",
                }
                assert {
                    item["name"]
                    for item in db_inspector.get_check_constraints(
                        "farm_memberships",
                        schema=schema,
                    )
                } == {
                    "ck_farm_memberships_membership_status",
                    "ck_farm_memberships_role_preset",
                }
                assert {
                    item["name"]
                    for item in db_inspector.get_check_constraints(
                        "local_sessions",
                        schema=schema,
                    )
                } == {"ck_local_sessions_auth_method"}

                assert {
                    item["name"]
                    for item in db_inspector.get_indexes("accounts", schema=schema)
                } == {"uq_accounts_login_name"}
                assert {
                    item["name"]
                    for item in db_inspector.get_indexes(
                        "farm_memberships",
                        schema=schema,
                    )
                } == {"uq_farm_memberships_account_farm"}
                assert {
                    item["name"]
                    for item in db_inspector.get_indexes(
                        "local_sessions",
                        schema=schema,
                    )
                } == {
                    "ix_local_sessions_account_id",
                    "ix_local_sessions_expires_at",
                    "uq_local_sessions_token_hash",
                }

                membership_fks = db_inspector.get_foreign_keys(
                    "farm_memberships",
                    schema=schema,
                )
                session_fks = db_inspector.get_foreign_keys(
                    "local_sessions",
                    schema=schema,
                )
                assert len(membership_fks) == 1
                assert membership_fks[0]["constrained_columns"] == ["account_id"]
                assert membership_fks[0]["referred_table"] == "accounts"
                assert membership_fks[0]["options"]["ondelete"] == "RESTRICT"
                assert len(session_fks) == 1
                assert session_fks[0]["constrained_columns"] == ["account_id"]
                assert session_fks[0]["referred_table"] == "accounts"
                assert session_fks[0]["options"]["ondelete"] == "RESTRICT"

                account_id = connection.execute(
                    Account.__table__
                    .insert()
                    .values(
                        login_name="boss.admin",
                        display_name="Boss Admin",
                        account_status="active",
                        password_hash="test-only-hash",
                    )
                    .returning(Account.account_id)
                ).scalar_one()
                disabled_account_id = connection.execute(
                    Account.__table__
                    .insert()
                    .values(
                        login_name="disabled.user",
                        display_name="Disabled User",
                        account_status="disabled",
                        password_hash="test-only-disabled-hash",
                        disabled_at=datetime.now(timezone.utc),
                    )
                    .returning(Account.account_id)
                ).scalar_one()
                farm_id = uuid.uuid4()
                membership_id = connection.execute(
                    FarmMembership.__table__
                    .insert()
                    .values(
                        account_id=account_id,
                        farm_id=farm_id,
                        role_preset="boss",
                        membership_status="active",
                    )
                    .returning(FarmMembership.membership_id)
                ).scalar_one()
                session_id = connection.execute(
                    LocalSession.__table__
                    .insert()
                    .values(
                        account_id=account_id,
                        token_hash="a" * 64,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                        auth_method="local_password",
                    )
                    .returning(LocalSession.session_id)
                ).scalar_one()

                assert isinstance(account_id, uuid.UUID)
                assert isinstance(disabled_account_id, uuid.UUID)
                assert isinstance(membership_id, uuid.UUID)
                assert isinstance(session_id, uuid.UUID)
                assert connection.execute(
                    select(Account.account_id).where(Account.account_id == account_id)
                ).scalar_one() == account_id
                assert connection.execute(
                    select(FarmMembership.farm_id).where(
                        FarmMembership.membership_id == membership_id
                    )
                ).scalar_one() == farm_id

                _assert_integrity_error(
                    connection,
                    Account.__table__.insert().values(
                        login_name=" Boss.Admin ",
                        display_name="Noncanonical",
                        account_status="active",
                        password_hash="test-only-hash",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    Account.__table__.insert().values(
                        login_name="invalid-status",
                        display_name="Invalid Status",
                        account_status="pending",
                        password_hash="test-only-hash",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    Account.__table__.insert().values(
                        login_name="missing-password",
                        display_name="Missing Password",
                        account_status="active",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    Account.__table__.insert().values(
                        login_name="boss.admin",
                        display_name="Duplicate Login",
                        account_status="active",
                        password_hash="test-only-hash",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    FarmMembership.__table__.insert().values(
                        account_id=account_id,
                        farm_id=uuid.uuid4(),
                        role_preset="owner",
                        membership_status="active",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    FarmMembership.__table__.insert().values(
                        account_id=account_id,
                        farm_id=uuid.uuid4(),
                        role_preset="engineer",
                        membership_status="revoked",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    FarmMembership.__table__.insert().values(
                        account_id=account_id,
                        farm_id=farm_id,
                        role_preset="boss",
                        membership_status="active",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    LocalSession.__table__.insert().values(
                        account_id=account_id,
                        token_hash="b" * 64,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                        auth_method="oauth",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    LocalSession.__table__.insert().values(
                        account_id=account_id,
                        token_hash="a" * 64,
                        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                        auth_method="local_password",
                    ),
                )
                _assert_integrity_error(
                    connection,
                    delete(Account.__table__).where(
                        Account.account_id == account_id
                    ),
                )

                with Operations.context(migration_context):
                    script_revision.module.downgrade()
                assert TASK_TABLES.isdisjoint(
                    inspect(connection).get_table_names(schema=schema)
                )
            finally:
                outer_transaction.rollback()
    finally:
        database.dispose()
