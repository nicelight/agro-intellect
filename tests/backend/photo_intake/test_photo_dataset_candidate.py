from __future__ import annotations

import uuid

from sqlalchemy import func, select

from backend.app.dataset_governance import DatasetCandidate, SourceKind
from backend.app.photo_intake import (
    PhotoIntakeError,
    PhotoIntakeService,
    PhotoUploadInput,
)
from tests.backend.photo_intake.conftest import photo_count
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    seed_farm,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0ft014-photo-candidate"


def _candidate_for_photo(database, *, photo_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(DatasetCandidate.source_ref == photo_id)
        )


def test_accept_photo_default_seam_creates_one_non_trainable_candidate(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    plant = create_active_plant(ft005_database, boss, plant_key="candidate_001")

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
                photo_type="leaf_closeup",
            ),
        )

    photo_id = result.item.photo_id
    assert photo_count(ft005_database) == 1
    assert result.item.can_train_on is False
    assert result.item.event_refs["photo_accepted"]["event_type"] == "photo_accepted"

    candidate = _candidate_for_photo(ft005_database, photo_id=photo_id)
    assert candidate is not None
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.source_kind == SourceKind.PHOTO_CATALOG_ITEM.value
    assert candidate.source_ref == photo_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.evidence_refs == [{"kind": "photo", "ref": str(photo_id)}]
    assert len(candidate.event_refs) == 1
    assert candidate.event_refs[0]["event_type"] == "dataset_candidate_created"

    created = [e for e in event_ref_factory.events if e.event_type == "dataset_candidate_created"]
    assert len(created) == 1


def test_accept_photo_second_upload_is_new_candidate_and_catalog_unchanged(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    plant = create_active_plant(ft005_database, boss, plant_key="candidate_002")
    grant_access(
        ft005_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    first = None
    second = None
    with ft005_database.session() as session:
        service = PhotoIntakeService(
            session,
            artifact_store=photo_artifact_store,
            timeline_append=event_ref_factory,
        )
        first = service.accept_photo(
            engineer,
            plant_id=plant.plant_id,
            upload=PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="whole_plant",
            ),
        )
        second = service.accept_photo(
            engineer,
            plant_id=plant.plant_id,
            upload=PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="problem_area",
            ),
        )

    assert first.item.photo_id != second.item.photo_id
    assert photo_count(ft005_database) == 2
    assert first.item.can_train_on is False
    assert second.item.can_train_on is False
    assert first.item.event_refs.keys() == {"photo_accepted"}
    assert second.item.event_refs.keys() == {"photo_accepted"}

    first_candidate = _candidate_for_photo(ft005_database, photo_id=first.item.photo_id)
    second_candidate = _candidate_for_photo(ft005_database, photo_id=second.item.photo_id)
    assert first_candidate.candidate_id != second_candidate.candidate_id
    assert first_candidate.source_ref == first.item.photo_id
    assert second_candidate.source_ref == second.item.photo_id

    with ft005_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 2


def test_archived_plant_acceptance_creates_no_photo_and_no_candidate(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    plant = create_active_plant(ft005_database, boss, plant_key="candidate_archived")
    grant_access(
        ft005_database,
        boss,
        plant_id=plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft005_database, boss, plant_id=plant.plant_id)

    with ft005_database.session() as session:
        try:
            PhotoIntakeService(
                session,
                artifact_store=photo_artifact_store,
                timeline_append=event_ref_factory,
            ).accept_photo(
                engineer,
                plant_id=plant.plant_id,
                upload=PhotoUploadInput(
                    content=JPEG_BYTES,
                    content_type="image/jpeg",
                    photo_type="whole_plant",
                ),
            )
        except PhotoIntakeError:
            pass
        else:
            raise AssertionError("archived-Plant acceptance must fail")

    assert photo_count(ft005_database) == 0
    with ft005_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    assert event_ref_factory.events == []
    artifact_root = photo_artifact_store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))


def test_unknown_plant_id_acceptance_creates_no_candidate(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
):
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    with ft005_database.session() as session:
        try:
            PhotoIntakeService(
                session,
                artifact_store=photo_artifact_store,
                timeline_append=event_ref_factory,
            ).accept_photo(
                boss,
                plant_id=uuid.uuid4(),
                upload=PhotoUploadInput(
                    content=JPEG_BYTES,
                    content_type="image/jpeg",
                    photo_type="whole_plant",
                ),
            )
        except PhotoIntakeError:
            pass
        else:
            raise AssertionError("unknown-Plant acceptance must fail")

    assert photo_count(ft005_database) == 0
    with ft005_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    artifact_root = photo_artifact_store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))
