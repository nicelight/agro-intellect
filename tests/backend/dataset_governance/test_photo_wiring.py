from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.app import AppSettings
from backend.app.dataset_governance import (
    DatasetCandidate,
    DatasetGovernanceService,
    DatasetGovernanceErrorCode,
    RecordDatasetEvidenceCommandV1,
    SourceKind,
)
from backend.app.photo_intake import (
    PhotoArtifactStore,
    PhotoIntakeError,
    PhotoIntakeErrorCode,
    PhotoIntakeService,
    PhotoUploadInput,
)
from tests.backend.dataset_governance.conftest import (
    FT014_NOW,
    TimelineRecorder,
)
from tests.backend.plant_operations.conftest import (
    archive_plant,
    create_actor,
    create_active_plant,
    grant_access,
    revoke_access,
    seed_farm,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0ft014-wiring-photo"


@pytest.fixture
def photo_artifact_store(tmp_path):
    return PhotoArtifactStore(
        AppSettings(local_artifact_root=tmp_path / "artifacts")
    )


def _candidate_count(database, *, plant_id, photo_id) -> int:
    with database.session() as session:
        return session.scalar(
            select(func.count(DatasetCandidate.candidate_id)).where(
                DatasetCandidate.plant_id == plant_id,
                DatasetCandidate.source_kind == SourceKind.PHOTO_CATALOG_ITEM.value,
                DatasetCandidate.source_ref == photo_id,
            )
        )


def _candidate_for(database, *, photo_id):
    with database.session() as session:
        return session.scalar(
            select(DatasetCandidate).where(DatasetCandidate.source_ref == photo_id)
        )


def _accept_photo(
    database,
    actor,
    *,
    plant_id,
    store,
    recorder,
    upload=None,
):
    with database.session() as session:
        service = PhotoIntakeService(
            session,
            artifact_store=store,
            timeline_append=recorder,
            dataset_governance=DatasetGovernanceService(
                session,
                timeline_appender=recorder,
                clock=lambda: FT014_NOW,
            ),
        )
        return service.accept_photo(
            actor,
            plant_id=plant_id,
            upload=upload
            or PhotoUploadInput(
                content=JPEG_BYTES,
                content_type="image/jpeg",
                photo_type="whole_plant",
            ),
        )


def test_ft014_ac005_accept_photo_creates_exact_candidate_and_event_in_same_uow(
    ft014_database,
    photo_artifact_store,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_photo_001")
    recorder = TimelineRecorder()
    recorder.events.clear()

    result = _accept_photo(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        store=photo_artifact_store,
        recorder=recorder,
    )
    photo_id = result.item.photo_id

    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        photo_id=photo_id,
    ) == 1
    candidate = _candidate_for(ft014_database, photo_id=photo_id)
    assert candidate.farm_id == farm.farm_id
    assert candidate.plant_id == plant.plant_id
    assert candidate.candidate_status == "candidate"
    assert candidate.candidate_origin == "raw"
    assert candidate.quality_tier == "standard"
    assert candidate.split is None
    assert candidate.confirmation_source is None
    assert candidate.can_train_on is False
    assert candidate.follow_up_seen is False
    assert candidate.curator_run_id is None
    assert candidate.curator_command_sha256 is None
    assert candidate.curator_recorded_at is None
    assert candidate.corrected is False
    assert candidate.record_version == 1
    assert candidate.evidence_refs == [
        {"kind": "photo", "ref": str(photo_id)}
    ]
    assert candidate.source_kind == "photo_catalog_item"
    assert candidate.source_ref == photo_id
    assert len(candidate.event_refs) == 1
    created = candidate.event_refs[0]
    assert created["event_type"] == "dataset_candidate_created"
    assert created["timeline_ref"].startswith("timeline.jsonl#")
    assert uuid.UUID(created["timeline_event_id"])

    created_events = [e for e in recorder.events if e.event_type == "dataset_candidate_created"]
    assert len(created_events) == 1
    assert created_events[0].source_type == "dataset_candidate"
    assert created_events[0].source_id == candidate.candidate_id
    assert created_events[0].payload_summary["source_kind"] == "photo_catalog_item"
    assert created_events[0].payload_summary["candidate_origin"] == "raw"
    assert created_events[0].payload_summary["can_train_on"] is False

    assert result.item.can_train_on is False
    assert result.item.local_only is True


def test_ft014_ac005_same_photo_seam_retry_is_idempotent_and_new_photo_is_new_evidence(
    ft014_database,
    photo_artifact_store,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_idem_001")
    recorder = TimelineRecorder()

    result = _accept_photo(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        store=photo_artifact_store,
        recorder=recorder,
    )
    photo_id = result.item.photo_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        photo_id=photo_id,
    ) == 1

    recorder.events.clear()
    with ft014_database.session() as session:
        retry = DatasetGovernanceService(
            session,
            timeline_appender=recorder,
            clock=lambda: FT014_NOW,
        ).record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=boss,
                plant_id=plant.plant_id,
                source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                source_ref=photo_id,
            )
        )
    assert retry.result == "duplicate"
    assert retry.candidate_id == _candidate_for(ft014_database, photo_id=photo_id).candidate_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        photo_id=photo_id,
    ) == 1
    assert recorder.events == []

    second = _accept_photo(
        ft014_database,
        boss,
        plant_id=plant.plant_id,
        store=photo_artifact_store,
        recorder=recorder,
    )
    assert second.item.photo_id != photo_id
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        photo_id=photo_id,
    ) == 1
    assert _candidate_count(
        ft014_database,
        plant_id=plant.plant_id,
        photo_id=second.item.photo_id,
    ) == 1


def test_ft014_ac005_audit_failure_rolls_back_photo_and_cleans_artifacts(
    ft014_database,
    photo_artifact_store,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_audit_001")
    recorder = TimelineRecorder(fail_on="dataset_candidate_created")

    with ft014_database.session() as session:
        with pytest.raises(PhotoIntakeError) as failure:
            PhotoIntakeService(
                session,
                artifact_store=photo_artifact_store,
                timeline_append=recorder,
                dataset_governance=DatasetGovernanceService(
                    session,
                    timeline_appender=recorder,
                    clock=lambda: FT014_NOW,
                ),
            ).accept_photo(
                boss,
                plant_id=plant.plant_id,
                upload=PhotoUploadInput(
                    content=JPEG_BYTES,
                    content_type="image/jpeg",
                    photo_type="whole_plant",
                ),
            )

    assert failure.value.code is PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
    from backend.app.photo_intake.models import PhotoCatalogItem

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
        assert session.scalar(select(func.count(PhotoCatalogItem.photo_id))) == 0
    artifact_root = photo_artifact_store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))


def test_ft014_ac005_persistence_failure_rolls_back_photo_and_cleans_artifacts(
    ft014_database,
    photo_artifact_store,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    plant = create_active_plant(ft014_database, boss, plant_key="wire_persist_001")
    recorder = TimelineRecorder()

    class FailingGovernance(DatasetGovernanceService):
        def record_dataset_evidence(self, command):
            from backend.app.dataset_governance import DatasetGovernanceError

            raise DatasetGovernanceError(DatasetGovernanceErrorCode.PERSISTENCE_FAILED)

    with ft014_database.session() as session:
        with pytest.raises(PhotoIntakeError) as failure:
            PhotoIntakeService(
                session,
                artifact_store=photo_artifact_store,
                timeline_append=recorder,
                dataset_governance=FailingGovernance(
                    session,
                    timeline_appender=recorder,
                ),
            ).accept_photo(
                boss,
                plant_id=plant.plant_id,
                upload=PhotoUploadInput(
                    content=JPEG_BYTES,
                    content_type="image/jpeg",
                    photo_type="whole_plant",
                ),
            )

    assert failure.value.code is PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
    from backend.app.photo_intake.models import PhotoCatalogItem

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(PhotoCatalogItem.photo_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    artifact_root = photo_artifact_store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))


def test_ft014_ac005_unauthorized_and_archived_plant_acceptance_creates_neither(
    ft014_database,
    photo_artifact_store,
):
    farm = seed_farm(ft014_database)
    boss, _ = create_actor(ft014_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft014_database, farm, "engineer")
    recorder = TimelineRecorder()

    revoked_plant = create_active_plant(ft014_database, boss, plant_key="wire_revoked")
    grant_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    revoke_access(
        ft014_database,
        boss,
        plant_id=revoked_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )

    archived_plant = create_active_plant(ft014_database, boss, plant_key="wire_archived")
    grant_access(
        ft014_database,
        boss,
        plant_id=archived_plant.plant_id,
        membership_id=engineer_membership.membership_id,
    )
    archive_plant(ft014_database, boss, plant_id=archived_plant.plant_id)

    for actor, plant in [
        (engineer, revoked_plant),
        (boss, archived_plant),
        (engineer, create_active_plant(ft014_database, boss, plant_key="wire_ungranted")),
    ]:
        with ft014_database.session() as session:
            with pytest.raises(PhotoIntakeError) as denied:
                PhotoIntakeService(
                    session,
                    artifact_store=photo_artifact_store,
                    timeline_append=recorder,
                ).accept_photo(
                    actor,
                    plant_id=plant.plant_id,
                    upload=PhotoUploadInput(
                        content=JPEG_BYTES,
                        content_type="image/jpeg",
                        photo_type="problem_area",
                    ),
                )
        assert denied.value.code is PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN

    from backend.app.photo_intake.models import PhotoCatalogItem

    with ft014_database.session() as session:
        assert session.scalar(select(func.count(PhotoCatalogItem.photo_id))) == 0
        assert session.scalar(select(func.count(DatasetCandidate.candidate_id))) == 0
    artifact_root = photo_artifact_store.path_for_test("plants")
    assert not artifact_root.exists() or not any(artifact_root.glob("**/*"))
