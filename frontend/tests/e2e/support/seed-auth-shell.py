#!/usr/bin/env python3
"""Seed an isolated disposable SQLite backend for the auth-shell e2e suite.

This is test-only support state. It never touches PostgreSQL, the real .env,
or any production record, and the backend application code is never modified.
Rerunning from scratch rebuilds the schema and the same canonical records.
"""
from __future__ import annotations

import pathlib
import sys
import uuid

from sqlalchemy import event

from backend.app.access_admin import bootstrap_canonical_farm
from backend.app.access_admin.models import (
    Account,
    Base,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from backend.app.access_admin.security import hash_password
from backend.app.config import AppSettings
from backend.app.database import build_database

E2E_PASSWORD = "Op3rator-Demo-Pa$$w0rd!"


def register_sqlite(dbapi_connection, _connection_record) -> None:
    dbapi_connection.create_function(
        "btrim", 1, lambda value: value.strip() if value is not None else None
    )
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def add_identity(
    session,
    *,
    farm_id,
    login_name: str,
    display_name: str,
    role_preset: str,
    account_status: str = "active",
    membership_status: str = "active",
) -> uuid.UUID:
    account = Account(
        login_name=login_name,
        display_name=display_name,
        account_status=account_status,
        password_hash=hash_password(E2E_PASSWORD),
    )
    session.add(account)
    session.flush()
    membership = FarmMembership(
        account_id=account.account_id,
        farm_id=farm_id,
        role_preset=role_preset,
        membership_status=membership_status,
    )
    session.add(membership)
    session.flush()
    return membership.membership_id


def add_plant(session, *, farm_id, plant_key: str, display_name: str, status: str = "active") -> uuid.UUID:
    plant = Plant(
        farm_id=farm_id,
        plant_key=plant_key,
        display_name=display_name,
        status=status,
    )
    session.add(plant)
    session.flush()
    return plant.plant_id


def add_grant(session, *, membership_id, plant_id, status: str = "active") -> uuid.UUID:
    grant = PlantAccessGrant(
        membership_id=membership_id,
        plant_id=plant_id,
        status=status,
        plant_approve_actions=False,
    )
    session.add(grant)
    session.flush()
    return grant.grant_id


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: seed-auth-shell.py <sqlite-db-path>", file=sys.stderr)
        return 2
    database_path = pathlib.Path(sys.argv[1])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        database_path.unlink()

    settings = AppSettings(
        app_name="agro-intellect-e2e",
        environment="test",
        database_url=f"sqlite+pysqlite:///{database_path}",
        database_echo=False,
        database_pool_pre_ping=True,
    )
    database = build_database(settings)
    engine = database.engine()
    event.listen(engine, "connect", register_sqlite)
    Base.metadata.create_all(engine)

    with database.session() as session:
        farm = bootstrap_canonical_farm(session)
        farm_id = farm.farm_id

        add_identity(
            session,
            farm_id=farm_id,
            login_name="boss",
            display_name="Boss Operator",
            role_preset="boss",
        )
        engineer_membership_id = add_identity(
            session,
            farm_id=farm_id,
            login_name="engineer",
            display_name="Engineer User",
            role_preset="engineer",
        )
        add_identity(
            session,
            farm_id=farm_id,
            login_name="engineer_nogrant",
            display_name="Engineer No Grant",
            role_preset="engineer",
        )
        engineer_revoked_membership_id = add_identity(
            session,
            farm_id=farm_id,
            login_name="engineer_revoked",
            display_name="Engineer Revoked",
            role_preset="engineer",
        )
        add_identity(
            session,
            farm_id=farm_id,
            login_name="consultant",
            display_name="Consultant User",
            role_preset="consultant",
        )
        account_only = Account(
            login_name="noseat",
            display_name="No Seat User",
            account_status="active",
            password_hash=hash_password(E2E_PASSWORD),
        )
        session.add(account_only)
        session.flush()
        add_identity(
            session,
            farm_id=farm_id,
            login_name="boss_disabled",
            display_name="Disabled Boss",
            role_preset="boss",
            account_status="disabled",
        )
        add_identity(
            session,
            farm_id=farm_id,
            login_name="engineer_disabledmem",
            display_name="Disabled Membership",
            role_preset="engineer",
            membership_status="disabled",
        )

        tomato_id = farm.plant_id
        add_plant(
            session,
            farm_id=farm_id,
            plant_key="pepper_002",
            display_name="Pepper 002",
        )
        add_plant(
            session,
            farm_id=farm_id,
            plant_key="herb_003",
            display_name="Herb 003",
            status="archived",
        )

        add_grant(session, membership_id=engineer_membership_id, plant_id=tomato_id)
        add_grant(
            session,
            membership_id=engineer_revoked_membership_id,
            plant_id=tomato_id,
            status="revoked",
        )
        session.commit()

    database.dispose()
    print(f"seeded {database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())