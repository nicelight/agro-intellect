#!/usr/bin/env python3
"""Create an isolated local PostgreSQL backend for the Boss-provisioning e2e.

Given an admin DSN and a target DSN, this support script drops/recreates the
target database, runs the canonical Alembic migration head, and seeds the same
canonical fixture set as seed-auth-shell.py (one Farm, boss/engineer/consultant
identities, plants and grants). It is test-only support state; the backend
application code is never modified. Rerunning from a clean database reproduces
the same canonical records.
"""
from __future__ import annotations

import sys
from urllib.parse import unquote, urlparse

from alembic import command as alembic_command

from backend.app.access_admin import bootstrap_canonical_farm
from backend.app.access_admin.models import (
    Account,
    FarmMembership,
    Plant,
    PlantAccessGrant,
)
from backend.app.access_admin.security import hash_password
from backend.app.config import AppSettings
from backend.app.database import build_database
from backend.migrations import build_alembic_config
from sqlalchemy import create_engine, text

SEED_PASSWORD = "Op3rator-Demo-Pa$$w0rd!"


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def ensure_database(admin_dsn: str, target_dsn: str) -> None:
    """Drop and recreate the target database through the admin connection."""
    parsed_target = urlparse(target_dsn)
    parsed_admin = urlparse(admin_dsn)._replace(path="/postgres")
    dbname = parsed_target.path.lstrip("/")
    if not dbname:
        raise SystemExit("target DSN must include a database name")
    admin_url = parsed_admin.geturl()
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_catalog.pg_database WHERE datname = :name"),
                {"name": dbname},
            ).scalar()
            if exists:
                connection.execute(text(f"DROP DATABASE {_quote_ident(dbname)}"))
            owner = unquote(parsed_admin.username or "")
            connection.execute(
                text(f"CREATE DATABASE {_quote_ident(dbname)} OWNER {_quote_ident(owner)}")
            )
    finally:
        engine.dispose()


def migrate_and_seed(target_dsn: str) -> None:
    settings = AppSettings(
        app_name="agro-intellect-e2e-provisioning",
        environment="test",
        database_url=target_dsn,
        database_echo=False,
        database_pool_pre_ping=True,
    )
    config = build_alembic_config(settings)
    alembic_command.ensure_version(config)
    alembic_command.upgrade(config, "head")

    database = build_database(settings)
    try:
        with database.session() as session:
            farm = bootstrap_canonical_farm(session)
            farm_id = farm.farm_id

            def add_identity(
                *,
                login_name: str,
                display_name: str,
                role_preset: str,
                account_status: str = "active",
                membership_status: str = "active",
            ):
                account = Account(
                    login_name=login_name,
                    display_name=display_name,
                    account_status=account_status,
                    password_hash=hash_password(SEED_PASSWORD),
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

            def add_plant(*, plant_key: str, display_name: str, status: str = "active"):
                plant = Plant(
                    farm_id=farm_id,
                    plant_key=plant_key,
                    display_name=display_name,
                    status=status,
                )
                session.add(plant)
                session.flush()
                return plant.plant_id

            def add_grant(*, membership_id, plant_id, status: str = "active"):
                grant = PlantAccessGrant(
                    membership_id=membership_id,
                    plant_id=plant_id,
                    status=status,
                    plant_approve_actions=False,
                )
                session.add(grant)
                session.flush()
                return grant.grant_id

            add_identity(login_name="boss", display_name="Boss Operator", role_preset="boss")
            engineer_membership_id = add_identity(
                login_name="engineer", display_name="Engineer User", role_preset="engineer"
            )
            add_identity(
                login_name="engineer_nogrant",
                display_name="Engineer No Grant",
                role_preset="engineer",
            )
            engineer_revoked_membership_id = add_identity(
                login_name="engineer_revoked",
                display_name="Engineer Revoked",
                role_preset="engineer",
            )
            add_identity(
                login_name="consultant", display_name="Consultant User", role_preset="consultant"
            )
            account_only = Account(
                login_name="noseat",
                display_name="No Seat User",
                account_status="active",
                password_hash=hash_password(SEED_PASSWORD),
            )
            session.add(account_only)
            session.flush()
            add_identity(
                login_name="boss_disabled",
                display_name="Disabled Boss",
                role_preset="boss",
                account_status="disabled",
            )
            add_identity(
                login_name="engineer_disabledmem",
                display_name="Disabled Membership",
                role_preset="engineer",
                membership_status="disabled",
            )

            tomato_id = farm.plant_id
            add_plant(plant_key="pepper_002", display_name="Pepper 002")
            add_plant(plant_key="herb_003", display_name="Herb 003", status="archived")
            add_grant(membership_id=engineer_membership_id, plant_id=tomato_id)
            add_grant(
                membership_id=engineer_revoked_membership_id,
                plant_id=tomato_id,
                status="revoked",
            )
            session.commit()
    finally:
        database.dispose()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: provision-postgres.py <admin-dsn> <target-dsn>", file=sys.stderr)
        return 2
    admin_dsn, target_dsn = sys.argv[1:3]
    ensure_database(admin_dsn, target_dsn)
    migrate_and_seed(target_dsn)
    print("provisioned isolated PostgreSQL e2e database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())