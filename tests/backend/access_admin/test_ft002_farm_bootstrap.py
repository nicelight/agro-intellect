from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import AppSettings
from backend.app.access_admin import AdminAuditRecord, Farm, Plant
from backend.app.access_admin.farm_bootstrap import (
    CanonicalFarmBootstrapError,
    bootstrap_canonical_farm,
)
from backend.app.database import build_database
from backend.migrations import build_alembic_config


@dataclass
class Store:
    farms: list[Farm] = field(default_factory=list)
    plants: list[Plant] = field(default_factory=list)
    membership_farm_ids: set[uuid.UUID] = field(default_factory=set)
    audits: list[dict[str, object]] = field(default_factory=list)


class FakeSession:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.rolled_back = False

    @contextmanager
    def begin(self):
        snapshot = deepcopy(self.store)
        try:
            yield
        except Exception:
            self.store.farms = snapshot.farms
            self.store.plants = snapshot.plants
            self.store.membership_farm_ids = snapshot.membership_farm_ids
            self.store.audits = snapshot.audits
            self.rolled_back = True
            raise


class FakeRepository:
    def __init__(self, session: FakeSession) -> None:
        self.store = session.store

    def lock_farms(self) -> list[Farm]:
        return list(self.store.farms)

    def membership_farm_ids(self) -> set[uuid.UUID]:
        return set(self.store.membership_farm_ids)

    def lock_canonical_plant(self) -> Plant | None:
        return next(
            (plant for plant in self.store.plants if plant.plant_key == "tomato_001"),
            None,
        )

    def add_farm(self, farm: Farm) -> None:
        farm.farm_id = farm.farm_id or uuid.uuid4()
        farm.created_at = farm.created_at or datetime.now(timezone.utc)
        farm.updated_at = farm.updated_at or farm.created_at
        self.store.farms.append(farm)

    def add_plant(self, plant: Plant) -> None:
        plant.plant_id = plant.plant_id or uuid.uuid4()
        plant.created_at = plant.created_at or datetime.now(timezone.utc)
        plant.updated_at = plant.updated_at or plant.created_at
        self.store.plants.append(plant)

    def flush(self) -> None:
        return None

    def add_system_audit(self, **values) -> None:
        self.store.audits.append(values)


def _factory(session: FakeSession) -> FakeRepository:
    return FakeRepository(session)


def test_canonical_bootstrap_is_idempotent_and_preserves_archived_state():
    store = Store()
    first = bootstrap_canonical_farm(FakeSession(store), repository_factory=_factory)
    before = deepcopy(store)
    second = bootstrap_canonical_farm(FakeSession(store), repository_factory=_factory)

    assert first.farm_created is True and first.plant_created is True
    assert second.farm_created is False and second.plant_created is False
    assert (first.farm_id, first.plant_id) == (second.farm_id, second.plant_id)
    assert len(store.farms) == 1 and len(store.plants) == 1
    assert [audit["action_type"] for audit in store.audits] == [
        "farm_created",
        "plant_created",
    ]
    assert store.farms[0].display_name == before.farms[0].display_name
    assert store.farms[0].updated_at == before.farms[0].updated_at
    assert store.plants[0].updated_at == before.plants[0].updated_at

    store.plants[0].status = "archived"
    archived_timestamp = store.plants[0].updated_at
    result = bootstrap_canonical_farm(FakeSession(store), repository_factory=_factory)
    assert result.plant_created is False
    assert store.plants[0].status == "archived"
    assert store.plants[0].updated_at == archived_timestamp
    assert len(store.audits) == 2


def test_canonical_bootstrap_partial_creation_writes_only_plant_audit():
    farm_id = uuid.uuid4()
    store = Store(
        farms=[
            Farm(
                farm_id=farm_id,
                farm_key="local_farm",
                display_name="Existing Name",
            )
        ],
        membership_farm_ids={farm_id},
    )
    result = bootstrap_canonical_farm(FakeSession(store), repository_factory=_factory)
    assert result.farm_created is False and result.plant_created is True
    assert store.farms[0].display_name == "Existing Name"
    assert [audit["action_type"] for audit in store.audits] == ["plant_created"]


@pytest.mark.parametrize("conflict", ["multiple_farms", "membership_mismatch"])
def test_canonical_bootstrap_conflicts_fail_before_mutation(conflict: str):
    farm = Farm(
        farm_id=uuid.uuid4(), farm_key="local_farm", display_name="Local Farm"
    )
    store = Store(farms=[farm])
    if conflict == "multiple_farms":
        store.farms.append(
            Farm(
                farm_id=uuid.uuid4(),
                farm_key="local_farm",
                display_name="Duplicate Farm",
            )
        )
    else:
        store.membership_farm_ids.add(uuid.uuid4())
    before = deepcopy(store)
    session = FakeSession(store)
    with pytest.raises(CanonicalFarmBootstrapError, match="repair them manually"):
        bootstrap_canonical_farm(session, repository_factory=_factory)
    assert session.rolled_back is True
    assert len(store.farms) == len(before.farms)
    assert store.plants == [] and store.audits == []


def test_bootstrap_audit_failure_rolls_back_and_redacts_internal_error():
    secret = "postgresql://admin:plain-secret@localhost/agro"

    class FailingAuditRepository(FakeRepository):
        def add_system_audit(self, **values) -> None:
            raise RuntimeError(f"audit insert failed for {secret}")

    store = Store()
    session = FakeSession(store)
    with pytest.raises(CanonicalFarmBootstrapError) as captured:
        bootstrap_canonical_farm(
            session,
            repository_factory=lambda current: FailingAuditRepository(current),
        )
    assert session.rolled_back is True
    assert store.farms == [] and store.plants == [] and store.audits == []
    assert "plain-secret" not in str(captured.value)
    assert "postgresql://" not in str(captured.value)


def test_bootstrap_script_dry_run_and_rejected_argument_are_secret_safe():
    script = Path("scripts/bootstrap-farm-local.sh")
    assert script.stat().st_mode & 0o111
    source = script.read_text(encoding="utf-8")
    assert "set -x" not in source
    assert "cat .env" not in source

    dry_run = subprocess.run(
        ["bash", str(script), "--dry-run"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert dry_run.returncode == 0
    assert "would create or reuse" in dry_run.stdout

    rejected = subprocess.run(
        ["bash", str(script), "--password=plain-secret"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert rejected.returncode == 2
    assert "plain-secret" not in rejected.stdout + rejected.stderr


def test_ft002_postgresql_bootstrap_first_partial_repeat_and_rollback():
    settings = AppSettings.from_env()
    database = build_database(settings)
    schema = f"task012_bootstrap_{uuid.uuid4().hex}"
    try:
        engine = database.engine()
        assert engine.dialect.name == "postgresql", (
            "TASK-012 bootstrap evidence requires configured PostgreSQL"
        )
        script = ScriptDirectory.from_config(build_alembic_config(settings))
        ft001 = script.get_revision("ft001_access_sessions")
        ft002 = script.get_revision("ft002_farm_plant_access")
        assert ft001 is not None and ft002 is not None
        with engine.connect() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.commit()
            connection.exec_driver_sql(f'SET search_path TO "{schema}", public')
            connection.commit()
            context = MigrationContext.configure(connection)
            try:
                with Operations.context(context):
                    ft001.module.upgrade()
                    ft002.module.upgrade()
                connection.commit()

                session = Session(bind=connection, expire_on_commit=False)
                first = bootstrap_canonical_farm(session)
                snapshot = session.execute(
                    select(
                        Farm.farm_id,
                        Farm.display_name,
                        Farm.updated_at,
                        Plant.plant_id,
                        Plant.display_name,
                        Plant.status,
                        Plant.updated_at,
                    ).join(Plant, Plant.farm_id == Farm.farm_id)
                ).one()
                audit_count = session.scalar(select(func.count(AdminAuditRecord.admin_audit_id)))
                session.commit()

                second = bootstrap_canonical_farm(session)
                repeated = session.execute(
                    select(
                        Farm.farm_id,
                        Farm.display_name,
                        Farm.updated_at,
                        Plant.plant_id,
                        Plant.display_name,
                        Plant.status,
                        Plant.updated_at,
                    ).join(Plant, Plant.farm_id == Farm.farm_id)
                ).one()
                repeated_audit_count = session.scalar(
                    select(func.count(AdminAuditRecord.admin_audit_id))
                )
                assert first.farm_created and first.plant_created
                assert not second.farm_created and not second.plant_created
                assert tuple(repeated) == tuple(snapshot)
                assert repeated_audit_count == audit_count == 2
                session.commit()
                session.close()
            finally:
                connection.rollback()
                connection.exec_driver_sql("SET search_path TO public")
                connection.commit()
                connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
                connection.commit()
    finally:
        database.dispose()
