from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import uuid

import pytest

from backend.app import AppSettings
from backend.app.photo_intake import (
    PROMPT_THRESHOLD_BYTES,
    PhotoArtifactStore,
    PhotoCatalogItem,
    PhotoIntakeError,
    PhotoIntakeErrorCode,
    PhotoIntakeService,
)
from backend.app.photo_intake.repository import PhotoIntakeRepository
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_active_plant,
    create_actor,
    seed_farm,
)

TWO_HUNDRED_MIB = 209715200


def test_empty_farm_returns_zero_and_not_eligible(ft005_database):
    farm = seed_farm(ft005_database)
    with ft005_database.session() as session:
        pressure = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
    assert pressure.accepted_original_photo_bytes == 0
    assert pressure.prompt_threshold_bytes == TWO_HUNDRED_MIB
    assert pressure.prompt_eligible is False


@pytest.mark.parametrize(
    ("total", "expected_eligible"),
    [
        (TWO_HUNDRED_MIB - 1, False),
        (TWO_HUNDRED_MIB, False),
        (TWO_HUNDRED_MIB + 1, True),
    ],
)
def test_pressure_matrix_below_exact_above_threshold(
    ft005_database, total, expected_eligible
):
    farm = seed_farm(ft005_database)
    boss, boss_membership = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="matrix_plant")
    _seed_catalog_bytes(
        ft005_database=ft005_database,
        actor=boss,
        membership_id=boss_membership.membership_id,
        plant_id=plant.plant_id,
        total=total,
    )
    with ft005_database.session() as session:
        pressure = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
    assert pressure.accepted_original_photo_bytes == total
    assert pressure.prompt_eligible is expected_eligible


def test_other_farm_ids_cannot_attract_rows(ft005_database):
    farm = seed_farm(ft005_database)
    boss, boss_membership = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="farm_a")
    _seed_catalog_bytes(
        ft005_database=ft005_database,
        actor=boss,
        membership_id=boss_membership.membership_id,
        plant_id=plant.plant_id,
        total=1200,
    )
    with ft005_database.session() as session:
        own_pressure = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
        foreign_pressure = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=uuid.uuid4()
        )
    assert own_pressure.accepted_original_photo_bytes == 1200
    assert foreign_pressure.accepted_original_photo_bytes == 0
    assert foreign_pressure.prompt_eligible is False


def test_query_shape_aggregates_only_catalog_size_bytes_by_farm(ft005_database):
    from sqlalchemy import event

    farm = seed_farm(ft005_database)
    statements: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "photo_catalog_items" in statement.lower():
            statements.append(statement)

    with ft005_database.session() as session:
        event.listen(session.bind, "before_cursor_execute", capture)
        try:
            PhotoIntakeService(session).farm_storage_pressure(farm_id=farm.farm_id)
        finally:
            event.remove(session.bind, "before_cursor_execute", capture)
    captured = " ".join(statements).lower()
    assert "from photo_catalog_items" in captured
    assert "coalesce(sum(photo_catalog_items.size_bytes)" in captured
    assert "photo_catalog_items.farm_id" in captured
    assert "manifest" not in captured
    assert "dataset_candidates" not in captured
    assert "pg_database" not in captured
    assert "timeline" not in captured


def test_archived_plant_retained_photos_still_contribute(ft005_database):
    farm = seed_farm(ft005_database)
    boss, boss_membership = create_actor(ft005_database, farm, "boss")
    active_plant = create_active_plant(ft005_database, boss, plant_key="active_pic")
    archived_plant = create_active_plant(
        ft005_database, boss, plant_key="archive_pic"
    )
    _seed_catalog_bytes(
        ft005_database=ft005_database,
        actor=boss,
        membership_id=boss_membership.membership_id,
        plant_id=active_plant.plant_id,
        total=1000,
    )
    _seed_catalog_bytes(
        ft005_database=ft005_database,
        actor=boss,
        membership_id=boss_membership.membership_id,
        plant_id=archived_plant.plant_id,
        total=2500,
    )
    archive_plant(ft005_database, boss, plant_id=archived_plant.plant_id)
    with ft005_database.session() as session:
        pressure = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
    assert pressure.accepted_original_photo_bytes == 3500


def test_each_catalog_row_counts_once_and_filesystem_cannot_influence(
    ft005_database, tmp_path
):
    farm = seed_farm(ft005_database)
    boss, boss_membership = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="once_plant")
    sizes = [314, 159, 2653, 5897]
    rows = _catalog_items(
        actor=boss,
        membership_id=boss_membership.membership_id,
        plant_id=plant.plant_id,
        sizes=sizes,
    )
    with ft005_database.session() as session:
        session.add_all(rows)
        session.commit()
        aggregate = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
    assert aggregate.accepted_original_photo_bytes == sum(sizes)

    store = PhotoArtifactStore(
        AppSettings(local_artifact_root=tmp_path / "artifacts")
    )
    oversized_manifest = store.path_for_test(
        f"plants/{plant.plant_id}/photos/{rows[0].photo_id}/"
        "manifest.initial_capture.json"
    )
    oversized_manifest.parent.mkdir(parents=True, exist_ok=True)
    oversized_manifest.write_text(
        json.dumps({"file": {"size_bytes": 999999999}}), encoding="utf-8"
    )
    with ft005_database.session() as session:
        after = PhotoIntakeService(session).farm_storage_pressure(
            farm_id=farm.farm_id
        )
    assert after.accepted_original_photo_bytes == sum(sizes)
    assert after.prompt_eligible is False


def test_non_uuid_farm_id_fails_validation(ft005_database):
    with ft005_database.session() as session:
        with pytest.raises(PhotoIntakeError) as invalid:
            PhotoIntakeService(session).farm_storage_pressure(
                farm_id="not-a-uuid"
            )
    assert invalid.value.code is PhotoIntakeErrorCode.VALIDATION_FAILED


def test_database_failure_fails_closed_without_partial_total(ft005_database):
    farm = seed_farm(ft005_database)
    with ft005_database.session() as session:
        service = PhotoIntakeService(
            session,
            repository_factory=lambda s: FailingPressureRepository(s),
        )
        with pytest.raises(PhotoIntakeError) as failure:
            service.farm_storage_pressure(farm_id=farm.farm_id)
    assert failure.value.code is PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED


class FailingPressureRepository(PhotoIntakeRepository):
    def sum_farm_photo_bytes(self, *, farm_id):
        raise RuntimeError("database unavailable")


def _seed_catalog_bytes(
    *,
    ft005_database,
    actor,
    membership_id,
    plant_id,
    total,
):
    chunk = 20 * 1024 * 1024
    sizes = []
    remaining = total
    while remaining > chunk:
        sizes.append(chunk)
        remaining -= chunk
    sizes.append(remaining)
    rows = _catalog_items(
        actor=actor,
        membership_id=membership_id,
        plant_id=plant_id,
        sizes=sizes,
    )
    with ft005_database.session() as session:
        session.add_all(rows)
        session.commit()


def _catalog_items(*, actor, membership_id, plant_id, sizes):
    base = datetime(2026, 7, 11, 8, 0, tzinfo=timezone.utc)
    rows = []
    for index, size in enumerate(sizes):
        photo_id = uuid.uuid4()
        uploaded_at = base + timedelta(minutes=index)
        rows.append(
            PhotoCatalogItem(
                photo_id=photo_id,
                farm_id=actor.farm_id,
                plant_id=plant_id,
                uploaded_by_account_id=actor.account_id,
                uploaded_by_membership_id=membership_id,
                photo_type="whole_plant",
                captured_at=uploaded_at,
                uploaded_at=uploaded_at,
                content_type="image/jpeg",
                size_bytes=size,
                sha256="a" * 64,
                original_file_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/original.jpg"
                ),
                manifest_ref=(
                    f"plants/{plant_id}/photos/{photo_id}/"
                    "manifest.initial_capture.json"
                ),
                source_refs={},
                event_refs={},
                local_only=True,
                can_train_on=False,
            )
        )
    return rows
