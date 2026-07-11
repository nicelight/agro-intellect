from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any
import uuid

from ..config import AppSettings


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class PhotoArtifactStorageError(RuntimeError):
    """Safe artifact storage failure."""

    def __init__(self) -> None:
        super().__init__("Photo artifact write failed.")


@dataclass(frozen=True, slots=True)
class StoredOriginal:
    original_file_ref: str
    content_type: str
    size_bytes: int
    sha256: str


class PhotoArtifactStore:
    def __init__(self, settings: AppSettings | None = None) -> None:
        self._settings = settings or AppSettings.from_env()
        self._root = Path(self._settings.local_artifact_root)

    def original_ref(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        content_type: str,
    ) -> str:
        extension = CONTENT_TYPE_EXTENSIONS[content_type]
        return f"plants/{plant_id}/photos/{photo_id}/original.{extension}"

    def manifest_ref(self, *, plant_id: uuid.UUID, photo_id: uuid.UUID) -> str:
        return f"plants/{plant_id}/photos/{photo_id}/manifest.initial_capture.json"

    def write_original(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        content: bytes,
        content_type: str,
    ) -> StoredOriginal:
        ref = self.original_ref(
            plant_id=plant_id,
            photo_id=photo_id,
            content_type=content_type,
        )
        path = self._path_for_ref(ref)
        try:
            self._write_atomic(path, content)
        except OSError:
            raise PhotoArtifactStorageError from None
        return StoredOriginal(
            original_file_ref=ref,
            content_type=content_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def write_manifest(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        manifest: dict[str, object],
    ) -> str:
        ref = self.manifest_ref(plant_id=plant_id, photo_id=photo_id)
        path = self._path_for_ref(ref)
        data = json.dumps(
            _json_ready(manifest),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            self._write_atomic(path, data)
        except OSError:
            raise PhotoArtifactStorageError from None
        return ref

    def read_manifest(self, ref: str) -> dict[str, object]:
        path = self._path_for_ref(ref)
        with path.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, dict):
            raise PhotoArtifactStorageError
        return loaded

    def path_for_test(self, ref: str) -> Path:
        return self._path_for_ref(ref)

    def cleanup_generated_refs(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        refs: list[str],
    ) -> None:
        expected_prefix = f"plants/{plant_id}/photos/{photo_id}/"
        for ref in refs:
            if not ref.startswith(expected_prefix):
                continue
            try:
                self._path_for_ref(ref).unlink(missing_ok=True)
            except OSError:
                pass

        photo_dir = self._path_for_ref(expected_prefix)
        for temp in photo_dir.glob(".*.tmp") if photo_dir.exists() else ():
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            photo_dir.rmdir()
        except OSError:
            pass
        self._remove_empty_generated_parents(photo_dir.parent)

    def _write_atomic(self, path: Path, data: bytes) -> None:
        if path.exists():
            raise PhotoArtifactStorageError
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temp_path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                raise PhotoArtifactStorageError
            os.replace(temp_path, path)
        except Exception:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def _path_for_ref(self, ref: str) -> Path:
        if not isinstance(ref, str) or not ref:
            raise PhotoArtifactStorageError
        pure = PurePosixPath(ref)
        if pure.is_absolute() or ".." in pure.parts:
            raise PhotoArtifactStorageError
        root = self._root.resolve()
        path = (root / Path(*pure.parts)).resolve()
        if not path.is_relative_to(root):
            raise PhotoArtifactStorageError
        return path

    def _remove_empty_generated_parents(self, start: Path) -> None:
        root = self._root.resolve()
        current = start
        while current != root and current.is_relative_to(root):
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


__all__ = [
    "CONTENT_TYPE_EXTENSIONS",
    "PhotoArtifactStorageError",
    "PhotoArtifactStore",
    "StoredOriginal",
]
