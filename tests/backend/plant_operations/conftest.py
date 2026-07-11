from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from backend.app import AppSettings
from backend.app.access_admin.actor_context import ActorContextResolver, AuthTransport
from backend.app.access_admin.farm_service import FarmService
from backend.app.access_admin.models import (
    Account,
    Farm,
    FarmMembership,
    LocalSession,
)
from backend.app.access_admin.session_service import ValidatedSession
from backend.app.database import DatabaseHandle, build_database
from backend.migrations import build_alembic_config


class StaticValidator:
    def __init__(self, validated: ValidatedSession) -> None:
        self.validated = validated

    def validate_session(self, _token: object) -> ValidatedSession:
        return self.validated


@pytest.fixture
def ft004_database():
    with _postgres_database() as database:
        yield database


@pytest.fixture
def event_ref_factory():
    events = []

    def append(event):
        events.append(event)
        timeline_event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(timeline_event_id),
            "timeline_ref": f"timeline.jsonl#{timeline_event_id}",
            "event_type": event.event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    append.events = events
    return append


@contextmanager
def _postgres_database():
    settings = AppSettings.from_env()
    base = build_database(settings)
    schema = f"task019_ops_{uuid.uuid4().hex}"
    scoped: DatabaseHandle | None = None
    try:
        assert base.engine().dialect.name == "postgresql"
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
        url = make_url(settings.database_url).update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        )
        scoped_settings = settings.model_copy(
            update={"database_url": url.render_as_string(hide_password=False)}
        )
        scoped = build_database(scoped_settings)
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        with scoped.engine().connect() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                script.get_revision("ft001_access_sessions").module.upgrade()
                script.get_revision("ft002_farm_plant_access").module.upgrade()
                script.get_revision("ft004_plant_operations").module.upgrade()
            connection.commit()
        yield scoped
    finally:
        if scoped is not None:
            scoped.dispose()
        with base.engine().connect() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            connection.commit()
        base.dispose()


def seed_farm(database: DatabaseHandle) -> Farm:
    with database.session() as session, session.begin():
        farm = Farm(farm_key="local_farm", display_name="Local Farm")
        session.add(farm)
        session.flush()
        return farm


def create_actor(
    database: DatabaseHandle,
    farm: Farm,
    role: str,
    *,
    membership_status: str = "active",
):
    with database.session() as session, session.begin():
        account = Account(
            login_name=f"{role}-{uuid.uuid4().hex}",
            display_name=f"{role.title()} User",
            account_status="active",
            password_hash="test-only-hash",
        )
        session.add(account)
        session.flush()
        membership = FarmMembership(
            account_id=account.account_id,
            farm_id=farm.farm_id,
            role_preset=role,
            membership_status=membership_status,
        )
        session.add(membership)
        session.flush()
        now = datetime.now(timezone.utc)
        local_session = LocalSession(
            account_id=account.account_id,
            token_hash=uuid.uuid4().hex * 2,
            created_at=now,
            expires_at=now + timedelta(days=1),
            auth_method="local_password",
        )
        session.add(local_session)
        session.flush()
        validated = ValidatedSession(
            session=local_session,
            account=account,
            membership=membership,
        )
        actor = ActorContextResolver(
            session_validator=StaticValidator(validated),
            snapshot_provider=lambda **_kwargs: None,
        ).resolve(
            request_id=f"req-{role}-{uuid.uuid4().hex[:8]}",
            raw_session_token="synthetic-test-token",
            transport=AuthTransport.COOKIE,
        )
        return actor, membership


def create_active_plant(database: DatabaseHandle, boss, *, plant_key: str):
    with database.session() as session:
        return FarmService(session).create_plant(
            boss,
            plant_key=plant_key,
            display_name=plant_key.replace("_", " ").title(),
        ).plant


def grant_access(database: DatabaseHandle, boss, *, plant_id, membership_id):
    with database.session() as session:
        return FarmService(session).grant_access(
            boss,
            plant_id=plant_id,
            membership_id=membership_id,
        ).entity


def revoke_access(database: DatabaseHandle, boss, *, plant_id, membership_id) -> None:
    with database.session() as session:
        FarmService(session).revoke_access(
            boss,
            plant_id=plant_id,
            membership_id=membership_id,
        )


def archive_plant(database: DatabaseHandle, boss, *, plant_id) -> None:
    with database.session() as session:
        FarmService(session).archive_plant(boss, plant_id=plant_id)


def disable_membership(database: DatabaseHandle, membership_id) -> None:
    with database.session() as session, session.begin():
        membership = session.get(FarmMembership, membership_id)
        membership.membership_status = "disabled"


def row_counts(database: DatabaseHandle) -> tuple[int, int]:
    from backend.app.plant_operations import DailyCheckIn, ManualMeasurement

    with database.session() as session:
        return (
            session.scalar(select(func.count(DailyCheckIn.check_in_id))),
            session.scalar(select(func.count(ManualMeasurement.measurement_id))),
        )
