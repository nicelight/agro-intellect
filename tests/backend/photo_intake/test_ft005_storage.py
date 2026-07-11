from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import uuid

import pytest

from backend.app.photo_intake.storage import PhotoArtifactStorageError


JPEG_BYTES = b"\xff\xd8\xff\xe0ft005-photo"


def test_photo_storage_uses_safe_relative_layout_and_immutable_files(
    photo_artifact_store,
):
    plant_id = uuid.uuid4()
    photo_id = uuid.uuid4()
    original = photo_artifact_store.write_original(
        plant_id=plant_id,
        photo_id=photo_id,
        content=JPEG_BYTES,
        content_type="image/jpeg",
    )
    manifest_ref = photo_artifact_store.write_manifest(
        plant_id=plant_id,
        photo_id=photo_id,
        manifest={
            "schema_version": "photo_manifest.v1",
            "manifest_kind": "initial_capture",
            "created_at": datetime.now(timezone.utc),
            "photo": {"photo_id": photo_id, "plant_id": plant_id},
            "file": {
                "original_file_ref": original.original_file_ref,
                "content_type": original.content_type,
                "size_bytes": original.size_bytes,
                "sha256": original.sha256,
            },
            "source": {"source_refs": {}},
            "authority": {"local_only": True, "can_train_on": False},
        },
    )

    assert original.original_file_ref == (
        f"plants/{plant_id}/photos/{photo_id}/original.jpg"
    )
    assert manifest_ref == (
        f"plants/{plant_id}/photos/{photo_id}/manifest.initial_capture.json"
    )
    assert not original.original_file_ref.startswith("/")
    assert ".." not in original.original_file_ref
    assert original.size_bytes == len(JPEG_BYTES)
    assert original.sha256 == hashlib.sha256(JPEG_BYTES).hexdigest()
    assert photo_artifact_store.path_for_test(original.original_file_ref).read_bytes() == (
        JPEG_BYTES
    )

    manifest_path = photo_artifact_store.path_for_test(manifest_ref)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "photo_manifest.v1"
    assert manifest["file"]["sha256"] == original.sha256
    assert str(manifest_path.parent) not in str(manifest)

    with pytest.raises(PhotoArtifactStorageError):
        photo_artifact_store.write_original(
            plant_id=plant_id,
            photo_id=photo_id,
            content=b"replacement",
            content_type="image/jpeg",
        )
    with pytest.raises(PhotoArtifactStorageError):
        photo_artifact_store.path_for_test(f"/plants/{plant_id}/bad")
    with pytest.raises(PhotoArtifactStorageError):
        photo_artifact_store.path_for_test("../escape")
