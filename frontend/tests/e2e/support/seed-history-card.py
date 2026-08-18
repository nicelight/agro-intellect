#!/usr/bin/env python3
"""Seed isolated Plant-history card state for the TASK-085 e2e (loopback Postgres).

Runs after provision-postgres.py against the already-migrated isolated
`agro_intellect_e2e_085` database. It inserts test-only history rows
(check-ins, manual measurements, photo catalog items, admin audit records) for
the active `tomato_001` and archived `herb_003` Plants so the authoritative
Plant card response carries exact refs, freshness, counts, permissions, and
retained-history mode. It never modifies application code or state outside the
isolated e2e database and never touches the real `.env` database.

Usage: seed-history-card.py <target-dsn>
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.app.access_admin.models import (
    Account,
    AdminAuditRecord,
    Farm,
    FarmMembership,
    Plant,
)
from backend.app.database import build_database
from backend.app.photo_intake.models import PhotoCatalogItem
from backend.app.plant_operations.models import DailyCheckIn, ManualMeasurement
from backend.app.config import AppSettings


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: seed-history-card.py <target-dsn>", file=sys.stderr)
        return 2
    settings = AppSettings(
        app_name="agro-intellect-e2e-085",
        environment="test",
        database_url=sys.argv[1],
        database_echo=False,
        database_pool_pre_ping=True,
    )
    database = build_database(settings)
    now = datetime.now(timezone.utc)
    stale = now - timedelta(days=3)
    try:
        with database.session() as session:
            farm = session.scalar(select(Farm).limit(1))
            if farm is None:
                raise SystemExit("no farm found in target database")
            boss = session.scalar(
                select(FarmMembership).where(
                    FarmMembership.farm_id == farm.farm_id,
                    FarmMembership.role_preset == "boss",
                )
            )
            if boss is None:
                raise SystemExit("no boss membership found in target database")
            boss_account = session.scalar(
                select(Account).where(Account.account_id == boss.account_id)
            )

            def add_check_in(plant: Plant, *, observed_at):
                row = DailyCheckIn(
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    actor_account_id=boss.account_id,
                    actor_membership_id=boss.membership_id,
                    check_in_state="completed",
                    observed_at=observed_at,
                    recorded_at=now,
                    observation_state="observed",
                    observation_text="Leaves look healthy; watering on schedule.",
                    source_refs={"role_preset": "boss"},
                    event_refs={},
                )
                session.add(row)
                session.flush()
                return row

            def add_measurement(plant: Plant, *, ph=None, ec_ms_cm=None, measured_at):
                row = ManualMeasurement(
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    check_in_id=None,
                    actor_account_id=boss.account_id,
                    actor_membership_id=boss.membership_id,
                    measured_at=measured_at,
                    recorded_at=now,
                    ph=ph,
                    ec_ms_cm=ec_ms_cm,
                    provenance_note=None,
                    source_type="manual_user",
                    source_refs={"role_preset": "boss"},
                    trust_status="confirmed",
                    event_refs={},
                )
                session.add(row)
                session.flush()
                return row

            def add_photo(plant: Plant, *, photo_type="whole_plant"):
                photo_id = uuid.uuid4()
                row = PhotoCatalogItem(
                    photo_id=photo_id,
                    farm_id=farm.farm_id,
                    plant_id=plant.plant_id,
                    check_in_id=None,
                    uploaded_by_account_id=boss.account_id,
                    uploaded_by_membership_id=boss.membership_id,
                    photo_type=photo_type,
                    captured_at=now,
                    uploaded_at=now,
                    content_type="image/jpeg",
                    size_bytes=12345,
                    sha256="a" * 64,
                    original_file_ref=(
                        f"plants/{plant.plant_id}/photos/{photo_id}/original.jpg"
                    ),
                    manifest_ref=(
                        f"plants/{plant.plant_id}/photos/{photo_id}/"
                        "manifest.initial_capture.json"
                    ),
                    source_refs={"role_preset": "boss"},
                    event_refs={"photo_accepted": {"timeline_ref": "timeline.jsonl#"}},
                    local_only=True,
                    can_train_on=False,
                )
                session.add(row)
                session.flush()
                return row

            def add_admin_audit(plant: Plant):
                row = AdminAuditRecord(
                    farm_id=farm.farm_id,
                    actor_kind="account",
                    actor_account_id=boss.account_id,
                    actor_membership_id=boss.membership_id,
                    actor_role_preset="boss",
                    action_type="plant_access_granted",
                    target_type="plant_access_grant",
                    target_id=uuid.uuid4(),
                    plant_id=plant.plant_id,
                    request_id=f"seed-request-085-{uuid.uuid4()}",
                    before_summary={},
                    after_summary={"status": "active"},
                    source_refs=[],
                )
                session.add(row)
                session.flush()
                return row

            tomato = session.scalar(
                select(Plant).where(
                    Plant.farm_id == farm.farm_id,
                    Plant.plant_key == "tomato_001",
                )
            )
            herb = session.scalar(
                select(Plant).where(
                    Plant.farm_id == farm.farm_id,
                    Plant.plant_key == "herb_003",
                )
            )
            if tomato is None or herb is None:
                raise SystemExit("seeded plants tomato_001/herb_003 missing")

            add_check_in(tomato, observed_at=now)
            add_measurement(tomato, ph=6.5, measured_at=now)
            add_measurement(tomato, ec_ms_cm=1.8, measured_at=now)
            add_photo(tomato)
            add_photo(tomato, photo_type="leaf_closeup")
            add_admin_audit(tomato)

            add_check_in(herb, observed_at=stale)
            add_measurement(herb, ph=6.8, ec_ms_cm=2.1, measured_at=stale)
            add_photo(herb)
            add_admin_audit(herb)

            session.commit()
    finally:
        database.dispose()
    print("seeded plant-history card state into isolated database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
