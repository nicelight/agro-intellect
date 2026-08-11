from __future__ import annotations

import base64
import binascii
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.permissions import (
    MembershipStatus,
    OperationKind,
    PermissionSource,
    PlantPermissionContext,
    PlantStatus,
    _BoundedPlantPermissionResolver,
)
from ..dataset_governance import (
    DatasetGovernanceService,
    RecordDatasetEvidenceCommandV1,
    SourceKind,
)
from ..timeline import TimelineEvent, TimelineJsonlAppender
from .models import PhotoCatalogItem
from .repository import PhotoIntakeRepository
from .storage import (
    CONTENT_TYPE_EXTENSIONS,
    PhotoArtifactStorageError,
    PhotoArtifactStore,
    StoredOriginal,
)


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
PHOTO_TYPES = {"whole_plant", "leaf_closeup", "roots", "problem_area", "other"}


class PhotoIntakeErrorCode(StrEnum):
    AUTH_PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    PHOTO_NOT_FOUND = "PHOTO_NOT_FOUND"
    PHOTO_TYPE_INVALID = "PHOTO_TYPE_INVALID"
    UPLOAD_FILE_REQUIRED = "UPLOAD_FILE_REQUIRED"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    PHOTO_CHECKSUM_MISMATCH = "PHOTO_CHECKSUM_MISMATCH"
    PHOTO_ARTIFACT_WRITE_FAILED = "PHOTO_ARTIFACT_WRITE_FAILED"
    TIMELINE_APPEND_FAILED = "TIMELINE_APPEND_FAILED"
    PHOTO_PERSISTENCE_FAILED = "PHOTO_PERSISTENCE_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class PhotoIntakeError(RuntimeError):
    def __init__(self, code: PhotoIntakeErrorCode) -> None:
        self.code = code
        super().__init__(f"Photo intake failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class PhotoUploadInput:
    content: bytes
    content_type: str
    photo_type: str
    captured_at: datetime | None = None
    check_in_id: uuid.UUID | None = None
    expected_sha256: str | None = None
    original_filename: str | None = None


@dataclass(frozen=True, slots=True)
class PhotoAcceptanceResult:
    item: PhotoCatalogItem
    manifest: dict[str, object]


@dataclass(frozen=True, slots=True)
class PhotoCatalogPage:
    items: list[PhotoCatalogItem]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class _ValidatedUpload:
    content: bytes
    content_type: str
    photo_type: str
    captured_at: datetime
    captured_at_source: str
    check_in_id: uuid.UUID | None
    expected_sha256: str | None


@dataclass(frozen=True, slots=True)
class _CatalogCursor:
    plant_id: uuid.UUID
    uploaded_at: datetime
    photo_id: uuid.UUID


RepositoryFactory = Callable[[Session], PhotoIntakeRepository]
TimelineAppender = Callable[[TimelineEvent], dict[str, object]]


class PhotoIntakeService:
    def __init__(
        self,
        session: Session,
        *,
        repository_factory: RepositoryFactory = PhotoIntakeRepository,
        artifact_store: PhotoArtifactStore | None = None,
        timeline_append: TimelineAppender | None = None,
        dataset_governance: DatasetGovernanceService | None = None,
    ) -> None:
        self._session = session
        self._repository_factory = repository_factory
        self._artifact_store = artifact_store or PhotoArtifactStore()
        self._timeline_append = timeline_append or TimelineJsonlAppender()
        self._dataset_governance = dataset_governance

    def accept_photo(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        upload: PhotoUploadInput,
    ) -> PhotoAcceptanceResult:
        uploaded_at = _now()
        values = _validated_upload(upload, uploaded_at=uploaded_at)
        photo_id = uuid.uuid4()
        created_refs: list[str] = []

        try:
            with self._session.begin():
                repository = self._repository_factory(self._session)
                permission = _require_permission(
                    repository,
                    actor,
                    plant_id=plant_id,
                    operation=OperationKind.OPERATE,
                )
                check_in_matches = (
                    values.check_in_id is None
                    or repository.check_in_belongs_to_plant(
                        farm_id=actor.farm_id,
                        plant_id=plant_id,
                        check_in_id=values.check_in_id,
                    )
                )
                if not check_in_matches:
                    raise PhotoIntakeError(PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN)

                source_refs = _source_refs(
                    actor,
                    permission,
                    check_in_id=values.check_in_id,
                )
                original = self._write_original(
                    plant_id=plant_id,
                    photo_id=photo_id,
                    values=values,
                )
                created_refs.append(original.original_file_ref)
                if (
                    values.expected_sha256 is not None
                    and values.expected_sha256 != original.sha256
                ):
                    raise PhotoIntakeError(
                        PhotoIntakeErrorCode.PHOTO_CHECKSUM_MISMATCH
                    )

                manifest = _initial_manifest(
                    photo_id=photo_id,
                    farm_id=actor.farm_id,
                    plant_id=plant_id,
                    values=values,
                    uploaded_at=uploaded_at,
                    original=original,
                    manifest_ref=self._artifact_store.manifest_ref(
                        plant_id=plant_id,
                        photo_id=photo_id,
                    ),
                    source_refs=source_refs,
                )
                manifest_ref = self._write_manifest(
                    plant_id=plant_id,
                    photo_id=photo_id,
                    manifest=manifest,
                )
                created_refs.append(manifest_ref)

                item = PhotoCatalogItem(
                    photo_id=photo_id,
                    farm_id=actor.farm_id,
                    plant_id=plant_id,
                    check_in_id=values.check_in_id,
                    uploaded_by_account_id=actor.account_id,
                    uploaded_by_membership_id=actor.membership_id,
                    photo_type=values.photo_type,
                    captured_at=values.captured_at,
                    uploaded_at=uploaded_at,
                    content_type=original.content_type,
                    size_bytes=original.size_bytes,
                    sha256=original.sha256,
                    original_file_ref=original.original_file_ref,
                    manifest_ref=manifest_ref,
                    source_refs=source_refs,
                    event_refs={},
                    local_only=True,
                    can_train_on=False,
                )
                repository.add_photo(item)
                repository.flush()
                item.event_refs = {
                    "photo_accepted": _append_event(
                        self._timeline_append,
                        _photo_event(item, source_refs),
                    )
                }
                repository.flush()
                self._record_dataset_evidence(
                    actor,
                    plant_id=plant_id,
                    photo_id=photo_id,
                )
                return PhotoAcceptanceResult(item=item, manifest=manifest)
        except PhotoIntakeError:
            self._artifact_store.cleanup_generated_refs(
                plant_id=plant_id,
                photo_id=photo_id,
                refs=created_refs,
            )
            raise
        except (IntegrityError, Exception):
            self._artifact_store.cleanup_generated_refs(
                plant_id=plant_id,
                photo_id=photo_id,
                refs=created_refs,
            )
            raise PhotoIntakeError(
                PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
            ) from None

    def list_photos(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
    ) -> PhotoCatalogPage:
        if (
            not isinstance(limit, int)
            or limit < 1
            or limit > 100
            or (cursor is not None and not isinstance(cursor, str))
        ):
            raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
        try:
            repository = self._repository_factory(self._session)
            _require_permission(
                repository,
                actor,
                plant_id=plant_id,
                operation=OperationKind.NORMAL_READ,
            )
            decoded_cursor = (
                _decode_catalog_cursor(cursor, plant_id=plant_id)
                if cursor is not None
                else None
            )
            rows = repository.list_photos(
                farm_id=actor.farm_id,
                plant_id=plant_id,
                limit=limit + 1,
                after=(
                    (decoded_cursor.uploaded_at, decoded_cursor.photo_id)
                    if decoded_cursor is not None
                    else None
                ),
            )
            has_more = len(rows) > limit
            items = rows[:limit]
            next_cursor = (
                _encode_catalog_cursor(items[-1]) if has_more else None
            )
            return PhotoCatalogPage(items=items, next_cursor=next_cursor)
        except PhotoIntakeError:
            raise
        except Exception:
            raise PhotoIntakeError(
                PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
            ) from None

    def get_photo(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> PhotoCatalogItem:
        if not isinstance(photo_id, uuid.UUID):
            raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
        try:
            repository = self._repository_factory(self._session)
            _require_permission(
                repository,
                actor,
                plant_id=plant_id,
                operation=OperationKind.NORMAL_READ,
            )
            item = repository.get_photo(
                farm_id=actor.farm_id,
                plant_id=plant_id,
                photo_id=photo_id,
            )
        except PhotoIntakeError:
            raise
        except Exception:
            raise PhotoIntakeError(
                PhotoIntakeErrorCode.PHOTO_PERSISTENCE_FAILED
            ) from None
        if item is None:
            raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_NOT_FOUND)
        return item

    def _write_original(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        values: _ValidatedUpload,
    ) -> StoredOriginal:
        try:
            return self._artifact_store.write_original(
                plant_id=plant_id,
                photo_id=photo_id,
                content=values.content,
                content_type=values.content_type,
            )
        except PhotoArtifactStorageError:
            raise PhotoIntakeError(
                PhotoIntakeErrorCode.PHOTO_ARTIFACT_WRITE_FAILED
            ) from None

    def _write_manifest(
        self,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
        manifest: dict[str, object],
    ) -> str:
        try:
            return self._artifact_store.write_manifest(
                plant_id=plant_id,
                photo_id=photo_id,
                manifest=manifest,
            )
        except PhotoArtifactStorageError:
            raise PhotoIntakeError(
                PhotoIntakeErrorCode.PHOTO_ARTIFACT_WRITE_FAILED
            ) from None

    def _record_dataset_evidence(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> None:
        governance = self._dataset_governance or DatasetGovernanceService(
            self._session,
            timeline_appender=self._timeline_append,
        )
        governance.record_dataset_evidence(
            RecordDatasetEvidenceCommandV1(
                actor_context=actor,
                plant_id=plant_id,
                source_kind=SourceKind.PHOTO_CATALOG_ITEM,
                source_ref=photo_id,
            )
        )


def _validated_upload(
    upload: PhotoUploadInput,
    *,
    uploaded_at: datetime,
) -> _ValidatedUpload:
    if not isinstance(upload, PhotoUploadInput):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    if not isinstance(upload.content, bytes) or len(upload.content) == 0:
        raise PhotoIntakeError(PhotoIntakeErrorCode.UPLOAD_FILE_REQUIRED)
    if len(upload.content) > MAX_UPLOAD_BYTES:
        raise PhotoIntakeError(PhotoIntakeErrorCode.UPLOAD_TOO_LARGE)
    try:
        content_type = upload.content_type.strip().lower()
        photo_type = upload.photo_type.strip()
    except Exception:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
    if content_type not in CONTENT_TYPE_EXTENSIONS:
        raise PhotoIntakeError(PhotoIntakeErrorCode.UNSUPPORTED_MEDIA_TYPE)
    if photo_type not in PHOTO_TYPES:
        raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_TYPE_INVALID)
    if upload.check_in_id is not None and not isinstance(upload.check_in_id, uuid.UUID):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    captured_at_source = "server_received_at"
    captured_at = uploaded_at
    if upload.captured_at is not None:
        captured_at = _aware_timestamp(upload.captured_at)
        captured_at_source = "user_input"
    expected_sha256 = upload.expected_sha256
    if expected_sha256 is not None:
        try:
            expected_sha256 = expected_sha256.strip().lower()
        except Exception:
            raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
        if len(expected_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in expected_sha256
        ):
            raise PhotoIntakeError(PhotoIntakeErrorCode.PHOTO_CHECKSUM_MISMATCH)
    return _ValidatedUpload(
        content=upload.content,
        content_type=content_type,
        photo_type=photo_type,
        captured_at=captured_at,
        captured_at_source=captured_at_source,
        check_in_id=upload.check_in_id,
        expected_sha256=expected_sha256,
    )


def _require_permission(
    repository: PhotoIntakeRepository,
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
    operation: OperationKind,
) -> PlantPermissionContext:
    if not isinstance(plant_id, uuid.UUID):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    identity = repository.lock_actor_identity(
        account_id=actor.account_id,
        membership_id=actor.membership_id,
        farm_id=actor.farm_id,
    )
    if identity is None:
        raise PhotoIntakeError(PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN)
    account, membership = identity
    if (
        account.account_status != "active"
        or membership.membership_status != MembershipStatus.ACTIVE.value
        or membership.account_id != actor.account_id
        or membership.role_preset != actor.role_preset.value
    ):
        raise PhotoIntakeError(PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN)

    resolver = _BoundedPlantPermissionResolver(
        farm_id=actor.farm_id,
        membership_id=actor.membership_id,
        membership_status=actor.membership_status,
        role_preset=actor.role_preset,
        snapshot_provider=repository.lock_plant_access_snapshot,
    )
    permission = resolver.resolve(plant_id, operation)
    allowed = (
        permission.can_operate
        if operation is OperationKind.OPERATE
        else permission.can_read
        if operation is OperationKind.NORMAL_READ
        else False
    )
    if permission.plant_status is not PlantStatus.ACTIVE or not allowed:
        raise PhotoIntakeError(PhotoIntakeErrorCode.AUTH_PLANT_FORBIDDEN)
    return permission


def _initial_manifest(
    *,
    photo_id: uuid.UUID,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
    values: _ValidatedUpload,
    uploaded_at: datetime,
    original: StoredOriginal,
    manifest_ref: str,
    source_refs: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": "photo_manifest.v1",
        "manifest_kind": "initial_capture",
        "created_at": uploaded_at.isoformat(),
        "photo": {
            "photo_id": str(photo_id),
            "farm_id": str(farm_id),
            "plant_id": str(plant_id),
            "photo_type": values.photo_type,
            "captured_at": values.captured_at.isoformat(),
        },
        "file": {
            "original_file_ref": original.original_file_ref,
            "manifest_ref": manifest_ref,
            "content_type": original.content_type,
            "size_bytes": original.size_bytes,
            "sha256": original.sha256,
        },
        "source": {
            "source_type": "manual_user_upload",
            "captured_at_source": values.captured_at_source,
            "uploaded_at": uploaded_at.isoformat(),
            "source_refs": source_refs,
        },
        "authority": {
            "authoritative_for_mutable_state": False,
            "runtime_authority": "postgresql_read_model",
            "local_only": True,
            "can_train_on": False,
        },
    }


def _photo_event(
    item: PhotoCatalogItem,
    source_refs: dict[str, object],
) -> TimelineEvent:
    return TimelineEvent(
        farm_id=item.farm_id,
        plant_id=item.plant_id,
        actor_ref=_actor_ref(source_refs),
        event_type="photo_accepted",
        source_type="photo_catalog_item",
        source_id=item.photo_id,
        source_refs=source_refs,
        payload_summary={
            "photo_type": item.photo_type,
            "captured_at": item.captured_at,
            "uploaded_at": item.uploaded_at,
            "content_type": item.content_type,
            "size_bytes": item.size_bytes,
            "sha256": item.sha256,
            "original_file_ref": item.original_file_ref,
            "manifest_ref": item.manifest_ref,
            "local_only": True,
            "can_train_on": False,
        },
    )


def _append_event(
    timeline_append: TimelineAppender,
    event: TimelineEvent,
) -> dict[str, object]:
    try:
        ref = timeline_append(event)
    except Exception:
        raise PhotoIntakeError(PhotoIntakeErrorCode.TIMELINE_APPEND_FAILED) from None
    if not _event_ref_shape_is_valid(ref, event.event_type):
        raise PhotoIntakeError(PhotoIntakeErrorCode.TIMELINE_APPEND_FAILED)
    return ref


def _event_ref_shape_is_valid(ref: object, event_type: str) -> bool:
    if not isinstance(ref, dict) or ref.get("event_type") != event_type:
        return False
    try:
        uuid.UUID(str(ref["timeline_event_id"]))
    except (KeyError, TypeError, ValueError):
        return False
    return (
        isinstance(ref.get("timeline_ref"), str)
        and str(ref["timeline_ref"]).startswith("timeline.jsonl#")
        and isinstance(ref.get("created_at"), str)
    )


def _source_refs(
    actor: ActorContext,
    permission: PlantPermissionContext,
    *,
    check_in_id: uuid.UUID | None,
) -> dict[str, object]:
    refs: dict[str, object] = {
        "request_id": actor.request_id,
        "account_id": str(actor.account_id),
        "membership_id": str(actor.membership_id),
        "farm_id": str(actor.farm_id),
        "plant_id": str(permission.plant_id),
        "role_preset": _enum_value(actor.role_preset),
        "membership_status": _enum_value(actor.membership_status),
        "permission_source": _enum_value(permission.source),
    }
    if permission.source is PermissionSource.PLANT_ACCESS_GRANT:
        refs["grant_id"] = str(permission.grant_id)
    if check_in_id is not None:
        refs["check_in_id"] = str(check_in_id)
    return refs


def _actor_ref(source_refs: dict[str, object]) -> dict[str, object]:
    return {
        "account_id": source_refs["account_id"],
        "membership_id": source_refs["membership_id"],
        "role_preset": source_refs["role_preset"],
    }


def _enum_value(value: object) -> object:
    return value.value if hasattr(value, "value") else value


def _aware_timestamp(value: datetime) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    return value


def _encode_catalog_cursor(item: PhotoCatalogItem) -> str:
    return _encode_catalog_cursor_values(
        plant_id=item.plant_id,
        uploaded_at=item.uploaded_at,
        photo_id=item.photo_id,
    )


def _encode_catalog_cursor_values(
    *,
    plant_id: uuid.UUID,
    uploaded_at: datetime,
    photo_id: uuid.UUID,
) -> str:
    payload = {
        "v": 1,
        "plant_id": str(plant_id),
        "uploaded_at": _canonical_cursor_timestamp(uploaded_at),
        "photo_id": str(photo_id),
    }
    raw = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_catalog_cursor(
    cursor: str,
    *,
    plant_id: uuid.UUID,
) -> _CatalogCursor:
    if not cursor or any(
        char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for char in cursor
    ):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    try:
        raw = base64.b64decode(
            cursor + ("=" * (-len(cursor) % 4)),
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
    if not isinstance(payload, dict) or set(payload) != {
        "v",
        "plant_id",
        "uploaded_at",
        "photo_id",
    }:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    if type(payload["v"]) is not int or payload["v"] != 1:
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    if not all(
        isinstance(payload[field], str)
        for field in ("plant_id", "uploaded_at", "photo_id")
    ):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    try:
        cursor_plant_id = uuid.UUID(payload["plant_id"])
        cursor_photo_id = uuid.UUID(payload["photo_id"])
        uploaded_at = datetime.fromisoformat(payload["uploaded_at"])
    except (TypeError, ValueError):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED) from None
    if (
        payload["plant_id"] != str(cursor_plant_id)
        or payload["photo_id"] != str(cursor_photo_id)
        or uploaded_at.tzinfo is None
        or uploaded_at.utcoffset() is None
        or cursor_plant_id != plant_id
        or _encode_catalog_cursor_values(
            plant_id=cursor_plant_id,
            uploaded_at=uploaded_at,
            photo_id=cursor_photo_id,
        )
        != cursor
    ):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    return _CatalogCursor(
        plant_id=cursor_plant_id,
        uploaded_at=uploaded_at.astimezone(timezone.utc),
        photo_id=cursor_photo_id,
    )


def _canonical_cursor_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise PhotoIntakeError(PhotoIntakeErrorCode.VALIDATION_FAILED)
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "MAX_UPLOAD_BYTES",
    "PHOTO_TYPES",
    "PhotoAcceptanceResult",
    "PhotoCatalogPage",
    "PhotoIntakeError",
    "PhotoIntakeErrorCode",
    "PhotoIntakeService",
    "PhotoUploadInput",
]
