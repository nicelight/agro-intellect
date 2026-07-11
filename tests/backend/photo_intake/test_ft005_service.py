from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid

import pytest
from sqlalchemy import select

from backend.app import AppSettings
from backend.app.photo_intake import (
    PhotoArtifactStore,
    PhotoCatalogItem,
    PhotoIntakeError,
    PhotoIntakeErrorCode,
    PhotoIntakeService,
    PhotoUploadInput,
)
from backend.app.photo_intake.repository import PhotoIntakeRepository
from backend.app.photo_intake.storage import PhotoArtifactStorageError
from backend.app.plant_operations import ManualMeasurementInput, PlantOperationsService
from tests.backend.photo_intake.conftest import photo_count
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    disable_membership,
    grant_access,
    revoke_access,
    seed_farm,
)


JPEG_BYTES = b"\xff\xd8\xff\xe0ft005-service-photo"


def test_ft005_bhv001_engineer_accepts_photo_catalog_manifest_checksum_and_timeline(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    plant = create_active_plant(ft005_database, boss, plant_key="photo_001")
    grant = grant_access(
        ft005_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with ft005_database.session() as session:
        check_in = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            engineer,
            plant_id=plant.plant_id,
            observation_state="observed",
            observation_text="Photo check-in",
            measurement=ManualMeasurementInput(ph="6.50"),
        ).check_in
    event_ref_factory.events.clear()

    captured_at = datetime.now(timezone.utc)
    with ft005_database.session() as session:
        result = PhotoIntakeService(
            session,
            artifact_store=photo_artifact_store,
            timeline_append=event_ref_factory,
        ).accept_photo(
            engineer,
            plant_id=plant.plant_id,
            upload=PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="leaf_closeup",
                captured_at=captured_at,
                check_in_id=check_in.check_in_id,
                original_filename="../../leaky-name.jpg",
            ),
        )

    item = result.item
    assert item.photo_id == event_ref_factory.events[0].source_id
    assert item.photo_id == uuid.UUID(result.manifest["photo"]["photo_id"])
    assert item.farm_id == farm.farm_id
    assert item.plant_id == plant.plant_id
    assert item.check_in_id == check_in.check_in_id
    assert item.uploaded_by_account_id == engineer.account_id
    assert item.uploaded_by_membership_id == engineer_membership.membership_id
    assert item.photo_type == "leaf_closeup"
    assert item.content_type == "image/jpeg"
    assert item.size_bytes == len(JPEG_BYTES)
    assert item.sha256 == hashlib.sha256(JPEG_BYTES).hexdigest()
    assert item.original_file_ref == (
        f"plants/{plant.plant_id}/photos/{item.photo_id}/original.jpg"
    )
    assert item.manifest_ref == (
        f"plants/{plant.plant_id}/photos/{item.photo_id}/"
        "manifest.initial_capture.json"
    )
    assert item.local_only is True
    assert item.can_train_on is False
    assert item.event_refs["photo_accepted"]["event_type"] == "photo_accepted"
    assert item.source_refs["grant_id"] == str(grant.grant_id)
    assert "session_id" not in item.source_refs
    assert "leaky-name" not in str(item.source_refs)

    original_path = photo_artifact_store.path_for_test(item.original_file_ref)
    manifest_path = photo_artifact_store.path_for_test(item.manifest_ref)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert original_path.read_bytes() == JPEG_BYTES
    assert manifest["schema_version"] == "photo_manifest.v1"
    assert manifest["manifest_kind"] == "initial_capture"
    assert manifest["photo"]["photo_id"] == str(item.photo_id)
    assert manifest["photo"]["farm_id"] == str(item.farm_id)
    assert manifest["photo"]["plant_id"] == str(item.plant_id)
    assert manifest["photo"]["photo_type"] == item.photo_type
    assert manifest["file"]["original_file_ref"] == item.original_file_ref
    assert manifest["file"]["manifest_ref"] == item.manifest_ref
    assert manifest["file"]["content_type"] == item.content_type
    assert manifest["file"]["size_bytes"] == item.size_bytes
    assert manifest["file"]["sha256"] == item.sha256
    assert manifest["authority"]["runtime_authority"] == "postgresql_read_model"
    assert manifest["authority"]["local_only"] is True
    assert manifest["authority"]["can_train_on"] is False

    event = event_ref_factory.events[0]
    assert event.event_type == "photo_accepted"
    assert event.source_type == "photo_catalog_item"
    assert event.source_id == item.photo_id
    assert event.payload_summary["sha256"] == item.sha256
    assert event.payload_summary["original_file_ref"] == item.original_file_ref
    assert event.payload_summary["manifest_ref"] == item.manifest_ref
    assert event.payload_summary["local_only"] is True
    assert event.payload_summary["can_train_on"] is False

    serialized = json.dumps(manifest, sort_keys=True) + str(event.payload_summary)
    assert "synthetic-test-token" not in serialized
    assert "leaky-name" not in serialized
    assert str(photo_artifact_store.path_for_test(item.original_file_ref).parent) not in (
        item.original_file_ref + item.manifest_ref + serialized
    )

    with ft005_database.session() as session:
        stored = session.scalar(select(PhotoCatalogItem))
        assert stored.photo_id == item.photo_id
        assert stored.event_refs["photo_accepted"]["event_type"] == "photo_accepted"
        assert photo_count(ft005_database) == 1


def test_active_boss_can_accept_photo_without_check_in(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="boss_photo_001")

    with ft005_database.session() as session:
        result = PhotoIntakeService(
            session,
            artifact_store=photo_artifact_store,
            timeline_append=event_ref_factory,
        ).accept_photo(
            boss,
            plant_id=plant.plant_id,
            upload=PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="whole_plant",
            ),
        )

    assert result.item.check_in_id is None
    assert result.item.source_refs["permission_source"] == "boss_role"
    assert result.item.event_refs["photo_accepted"]["event_type"] == "photo_accepted"


def test_catalog_keyset_pages_enumerate_postgresql_rows_exactly_once(
    ft005_database,
):
    farm = seed_farm(ft005_database)
    boss, boss_membership = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="page_catalog")
    base = datetime(2026, 7, 11, 8, 0, tzinfo=timezone.utc)
    newest_id = uuid.UUID(int=30)
    tied_first_id = uuid.UUID(int=10)
    tied_second_id = uuid.UUID(int=20)
    oldest_id = uuid.UUID(int=40)
    rows = [
        _catalog_item(
            actor=boss,
            membership_id=boss_membership.membership_id,
            plant_id=plant.plant_id,
            photo_id=newest_id,
            uploaded_at=base + timedelta(minutes=2),
        ),
        _catalog_item(
            actor=boss,
            membership_id=boss_membership.membership_id,
            plant_id=plant.plant_id,
            photo_id=tied_second_id,
            uploaded_at=base + timedelta(minutes=1),
        ),
        _catalog_item(
            actor=boss,
            membership_id=boss_membership.membership_id,
            plant_id=plant.plant_id,
            photo_id=oldest_id,
            uploaded_at=base,
        ),
        _catalog_item(
            actor=boss,
            membership_id=boss_membership.membership_id,
            plant_id=plant.plant_id,
            photo_id=tied_first_id,
            uploaded_at=base + timedelta(minutes=1),
        ),
    ]
    with ft005_database.session() as session:
        session.add_all(rows)
        session.commit()

    expected = [newest_id, tied_first_id, tied_second_id, oldest_id]
    enumerated = []
    cursors = []
    cursor = None
    with ft005_database.session() as session:
        service = PhotoIntakeService(session)
        while True:
            page = service.list_photos(
                boss,
                plant_id=plant.plant_id,
                cursor=cursor,
                limit=1,
            )
            enumerated.extend(item.photo_id for item in page.items)
            if page.next_cursor is None:
                break
            assert page.next_cursor not in cursors
            cursors.append(page.next_cursor)
            cursor = page.next_cursor

    assert enumerated == expected
    assert len(enumerated) == len(set(enumerated)) == len(rows)
    assert len(cursors) == len(rows) - 1


def test_invalid_check_in_association_fails_without_artifacts(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    first_plant = create_active_plant(ft005_database, boss, plant_key="checkin_a")
    second_plant = create_active_plant(ft005_database, boss, plant_key="checkin_b")
    grant_access(
        ft005_database,
        boss,
        plant_id=first_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    grant_access(
        ft005_database,
        boss,
        plant_id=second_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    with ft005_database.session() as session:
        check_in = PlantOperationsService(
            session,
            timeline_append=event_ref_factory,
        ).create_check_in(
            engineer,
            plant_id=first_plant.plant_id,
            observation_state="observed",
            observation_text="First Plant only",
        ).check_in
    event_ref_factory.events.clear()

    with ft005_database.session() as session:
        with pytest.raises(PhotoIntakeError) as denied:
            PhotoIntakeService(
                session,
                artifact_store=photo_artifact_store,
                timeline_append=event_ref_factory,
            ).accept_photo(
                engineer,
                plant_id=second_plant.plant_id,
                upload=PhotoUploadInput(
                    content=JPEG_BYTES,
                    content_type="image/jpeg",
                    photo_type="leaf_closeup",
                    check_in_id=check_in.check_in_id,
                ),
            )

    assert denied.value.code is PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN
    assert photo_count(ft005_database) == 0
    assert event_ref_factory.events == []
    assert not any(photo_artifact_store.path_for_test("plants").glob("**/*"))


def test_ft005_bhv003_archived_and_unauthorized_uploads_fail_before_artifacts(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    consultant, consultant_membership = create_actor(
        ft005_database,
        farm,
        "consultant",
    )
    disabled_engineer, disabled_membership = create_actor(
        ft005_database,
        farm,
        "engineer",
    )

    consultant_plant = create_active_plant(
        ft005_database,
        boss,
        plant_key="consultant_photo",
    )
    grant_access(
        ft005_database,
        boss,
        plant_id=consultant_plant.plant_id,
        membership_id=consultant_membership.membership_id,
    )

    revoked_plant = create_active_plant(ft005_database, boss, plant_key="revoked_photo")
    grant_access(
        ft005_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft005_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    archived_plant = create_active_plant(ft005_database, boss, plant_key="archive_photo")
    grant_access(
        ft005_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft005_database, boss, plant_id=archived_plant.plant_id)

    disabled_plant = create_active_plant(ft005_database, boss, plant_key="disabled_pic")
    grant_access(
        ft005_database,
        boss,
        plant_id=disabled_plant.plant_id,
        membership_id=disabled_membership.membership_id,
    )
    disable_membership(ft005_database, disabled_membership.membership_id)

    cases = [
        (consultant, consultant_plant.plant_id),
        (engineer, revoked_plant.plant_id),
        (boss, archived_plant.plant_id),
        (disabled_engineer, disabled_plant.plant_id),
        (engineer, uuid.uuid4()),
    ]
    for actor, plant_id in cases:
        with ft005_database.session() as session:
            with pytest.raises(PhotoIntakeError) as denied:
                PhotoIntakeService(
                    session,
                    artifact_store=photo_artifact_store,
                    timeline_append=event_ref_factory,
                ).accept_photo(
                    actor,
                    plant_id=plant_id,
                    upload=PhotoUploadInput(
                        content=JPEG_BYTES,
                        content_type="image/jpeg",
                        photo_type="problem_area",
                    ),
                )
        assert denied.value.code is PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN

    assert photo_count(ft005_database) == 0
    assert event_ref_factory.events == []
    assert not any(photo_artifact_store.path_for_test("plants").glob("**/*"))


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [
        ("file", PhotoIntakeErrorCode.PHOTO_ARTIFACT_WRITE_FAILED),
        ("manifest", PhotoIntakeErrorCode.PHOTO_ARTIFACT_WRITE_FAILED),
        ("catalog", PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED),
        ("checksum", PhotoIntakeErrorCode.PHOTO_CHECKSUM_MISMATCH),
        ("timeline", PhotoIntakeErrorCode.TIMELINE_APPEND_FAILED),
    ],
)
def test_ft005_bhv002_failures_leave_no_accepted_artifact(
    ft005_database,
    tmp_path,
    mode,
    expected_code,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    plant = create_active_plant(ft005_database, boss, plant_key=f"failure_{mode}")
    grant_access(
        ft005_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    store = _store_for_mode(mode, tmp_path)
    repository_factory = (
        (lambda session: FailingFlushRepository(session))
        if mode == "catalog"
        else PhotoIntakeRepository
    )

    def append(event):
        if mode == "timeline":
            raise RuntimeError("timeline secret=hidden")
        timeline_event_id = uuid.uuid4()
        return {
            "timeline_event_id": str(timeline_event_id),
            "timeline_ref": f"timeline.jsonl#{timeline_event_id}",
            "event_type": event.event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    upload = PhotoUploadInput(
        content=JPEG_BYTES,
        content_type="image/jpeg",
        photo_type="leaf_closeup",
        expected_sha256=("0" * 64 if mode == "checksum" else None),
    )

    with ft005_database.session() as session:
        with pytest.raises(PhotoIntakeError) as failure:
            PhotoIntakeService(
                session,
                repository_factory=repository_factory,
                artifact_store=store,
                timeline_append=append,
            ).accept_photo(engineer, plant_id=plant.plant_id, upload=upload)

    assert failure.value.code is expected_code
    assert "hidden" not in str(failure.value)
    assert photo_count(ft005_database) == 0
    artifact_root = store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))


class FailingOriginalStore(PhotoArtifactStore):
    def write_original(self, *, plant_id, photo_id, content, content_type):
        ref = self.original_ref(
            plant_id=plant_id,
            photo_id=photo_id,
            content_type=content_type,
        )
        path = self.path_for_test(ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_name(".original.tmp").write_bytes(b"partial")
        raise PhotoArtifactStorageError


class FailingManifestStore(PhotoArtifactStore):
    def write_manifest(self, *, plant_id, photo_id, manifest):
        raise PhotoArtifactStorageError


class FailingFlushRepository(PhotoIntakeRepository):
    def flush(self) -> None:
        raise RuntimeError("catalog password=hidden")


def _catalog_item(
    *,
    actor,
    membership_id: uuid.UUID,
    plant_id: uuid.UUID,
    photo_id: uuid.UUID,
    uploaded_at: datetime,
) -> PhotoCatalogItem:
    return PhotoCatalogItem(
        photo_id=photo_id,
        farm_id=actor.farm_id,
        plant_id=plant_id,
        uploaded_by_account_id=actor.account_id,
        uploaded_by_membership_id=membership_id,
        photo_type="whole_plant",
        captured_at=uploaded_at,
        uploaded_at=uploaded_at,
        content_type="image/jpeg",
        size_bytes=1,
        sha256="a" * 64,
        original_file_ref=f"plants/{plant_id}/photos/{photo_id}/original.jpg",
        manifest_ref=(
            f"plants/{plant_id}/photos/{photo_id}/manifest.initial_capture.json"
        ),
        source_refs={},
        event_refs={},
        local_only=True,
        can_train_on=False,
    )


def _store_for_mode(mode: str, tmp_path) -> PhotoArtifactStore:
    settings = AppSettings(local_artifact_root=tmp_path / f"artifacts-{mode}")
    if mode == "file":
        return FailingOriginalStore(settings)
    if mode == "manifest":
        return FailingManifestStore(settings)
    return PhotoArtifactStore(settings)
