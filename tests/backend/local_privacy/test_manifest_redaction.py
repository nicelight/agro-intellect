from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

import pytest

from backend.app import AppSettings
from backend.app.photo_intake import (
    PhotoArtifactStore,
    PhotoIntakeErrorCode,
    PhotoIntakeService,
    PhotoUploadInput,
)
from backend.app.photo_intake.storage import PhotoArtifactStorageError
from backend.app.plant_operations import PlantOperationsService
from tests.backend.plant_operations.conftest import (
    create_actor,
    create_active_plant,
    grant_access,
    seed_farm,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0task067-photo"

CORPUS_DB_PASSWORD = "corpus-manifest-db-pw-9x2k"
CORPUS_ENV_SECRET = "corpus-manifest-env-secret-41f7"
CORPUS_BEARER = "corpus-manifest-bearer-q2z9"
CORPUS_API_KEY = "corpus-manifest-api-key-77m3"

CORPUS = [
    CORPUS_DB_PASSWORD,
    CORPUS_ENV_SECRET,
    CORPUS_BEARER,
    CORPUS_API_KEY,
]


@pytest.fixture
def photo_artifact_store(tmp_path):
    return PhotoArtifactStore(
        AppSettings(
            app_name="agro-intellect-test",
            environment="test",
            local_artifact_root=tmp_path / "artifacts",
        )
    )


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


def _store(tmp_path) -> PhotoArtifactStore:
    return PhotoArtifactStore(
        AppSettings(
            app_name="agro-intellect-test",
            environment="test",
            database_url=(
                "postgresql+psycopg://postgres:"
                f"{CORPUS_DB_PASSWORD}@localhost/agro_intellect"
            ),
            database_echo=False,
            database_pool_pre_ping=True,
            local_artifact_root=tmp_path / "artifacts",
        )
    )


def _manifest_with_corpus(plant_id: uuid.UUID, photo_id: uuid.UUID) -> dict:
    return {
        "schema_version": "photo_manifest.v1",
        "manifest_kind": "initial_capture",
        "created_at": "2026-07-10T12:00:00+05:00",
        "photo": {
            "photo_id": str(photo_id),
            "farm_id": str(uuid.uuid4()),
            "plant_id": str(plant_id),
            "photo_type": "leaf_closeup",
            "captured_at": "2026-07-10T12:00:00+05:00",
        },
        "file": {
            "original_file_ref": (
                f"plants/{plant_id}/photos/{photo_id}/original.jpg"
            ),
            "content_type": "image/jpeg",
            "size_bytes": 123456,
            "sha256": "a" * 64,
            "note": (
                f"Authorization: Bearer {CORPUS_BEARER} | "
                f"password={CORPUS_DB_PASSWORD} | "
                f"postgresql+psycopg://postgres:{CORPUS_DB_PASSWORD}@dbhost/agro | "
                f"env={CORPUS_ENV_SECRET} | key={CORPUS_API_KEY}"
            ),
        },
        "source": {"source_refs": {"request_id": CORPUS_ENV_SECRET}},
        "authority": {"local_only": True, "can_train_on": False},
    }


class _Unrenderable(str):
    def __str__(self) -> str:
        raise ValueError(f"boom {CORPUS_ENV_SECRET}")


class _FailingManifestStore(PhotoArtifactStore):
    def write_manifest(self, *, plant_id, photo_id, manifest):
        path = self.path_for_test(
            self.manifest_ref(plant_id=plant_id, photo_id=photo_id)
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_name(".manifest.tmp").write_bytes(b"partial")
        raise PhotoArtifactStorageError


def test_manifest_writer_removes_configured_corpus_before_atomic_write(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_API_KEY", CORPUS_API_KEY)
    store = _store(tmp_path)
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    source_url = store._settings.database_url

    ref = store.write_manifest(
        plant_id=plant_id,
        photo_id=photo_id,
        manifest=_manifest_with_corpus(plant_id, photo_id),
    )

    path = store.path_for_test(ref)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(persisted, sort_keys=True)
    for raw in CORPUS:
        assert raw not in text
    assert "***" in text
    assert store._settings.database_url == source_url
    assert persisted["schema_version"] == "photo_manifest.v1"
    assert persisted["file"]["content_type"] == "image/jpeg"
    assert persisted["file"]["size_bytes"] == 123456


def test_manifest_writer_preserves_strict_allowed_shape_for_safe_values(tmp_path):
    store = _store(tmp_path)
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    manifest = _manifest_with_corpus(plant_id, photo_id)
    manifest["file"]["note"] = "safe note with no secrets"
    manifest["source"]["source_refs"] = {"request_id": "safe-request-id"}

    ref = store.write_manifest(
        plant_id=plant_id,
        photo_id=photo_id,
        manifest=manifest,
    )

    persisted = json.loads(store.path_for_test(ref).read_text(encoding="utf-8"))
    assert persisted["file"]["note"] == "safe note with no secrets"
    assert persisted["source"]["source_refs"] == {"request_id": "safe-request-id"}
    assert persisted["file"]["original_file_ref"] == manifest["file"]["original_file_ref"]
    assert set(persisted) == set(manifest)
    assert json.dumps(persisted, sort_keys=True).count("***") == 0


def test_manifest_sanitizer_failure_persists_no_manifest_and_leaks_no_raw_value(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    store = _store(tmp_path)
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    manifest = _manifest_with_corpus(plant_id, photo_id)
    manifest["source"]["source_refs"]["request_id"] = _Unrenderable(CORPUS_ENV_SECRET)

    with pytest.raises(PhotoArtifactStorageError):
        store.write_manifest(
            plant_id=plant_id,
            photo_id=photo_id,
            manifest=manifest,
        )

    manifest_path = store.path_for_test(
        store.manifest_ref(plant_id=plant_id, photo_id=photo_id)
    )
    assert not manifest_path.exists()
    assert not manifest_path.parent.exists()
    assert not any(store.path_for_test("plants").glob("**/.*.tmp"))


def test_manifest_write_failure_cleanup_leaves_no_accepted_unsafe_manifest(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    store = _FailingManifestStore(_store(tmp_path)._settings)
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()

    with pytest.raises(PhotoArtifactStorageError):
        store.write_manifest(
            plant_id=plant_id,
            photo_id=photo_id,
            manifest=_manifest_with_corpus(plant_id, photo_id),
        )

    store.cleanup_generated_refs(
        plant_id=plant_id,
        photo_id=photo_id,
        refs=[store.manifest_ref(plant_id=plant_id, photo_id=photo_id)],
    )
    assert not store.path_for_test("plants").exists()


def test_manifest_writer_leaves_no_temp_files_after_atomic_accept(tmp_path):
    store = _store(tmp_path)
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()

    ref = store.write_manifest(
        plant_id=plant_id,
        photo_id=photo_id,
        manifest=_manifest_with_corpus(plant_id, photo_id),
    )
    assert store.path_for_test(ref).exists()
    assert not any(store.path_for_test("plants").glob("**/.*.tmp"))


def test_service_accept_persists_corpus_free_manifest_through_actual_writer(
    ft005_database,
    photo_artifact_store,
    event_ref_factory,
    monkeypatch,
):
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_TOKEN", CORPUS_ENV_SECRET)
    monkeypatch.setenv("AGRO_MANIFEST_CORPUS_API_KEY", CORPUS_API_KEY)
    farm = seed_farm(ft005_database)
    boss, _ = create_actor(ft005_database, farm, "boss")
    engineer, engineer_membership = create_actor(ft005_database, farm, "engineer")
    plant = create_active_plant(ft005_database, boss, plant_key="task067_photo")
    grant_access(
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
        ).check_in

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
                check_in_id=check_in.check_in_id,
            ),
        )

    manifest_path = photo_artifact_store.path_for_test(result.item.manifest_ref)
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = json.dumps(persisted, sort_keys=True)
    for raw in CORPUS:
        assert raw not in text
    assert persisted["schema_version"] == "photo_manifest.v1"
    assert persisted["manifest_kind"] == "initial_capture"
    assert persisted["photo"]["photo_id"] == str(result.item.photo_id)
    assert persisted["authority"]["local_only"] is True
    assert result.item.event_refs["photo_accepted"]["event_type"] == "photo_accepted"
    assert not any(photo_artifact_store.path_for_test("plants").glob("**/.*.tmp"))
