from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
import json
import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import AdminAuditRecord, Plant
from ..access_admin.permissions import (
    MembershipStatus,
    OperationKind,
    PermissionSource,
    PlantPermissionContext,
    PlantStatus,
    _BoundedPlantPermissionResolver,
)
from ..core.redaction import REDACTION, is_sensitive_key, redact_text
from ..photo_intake.models import PhotoCatalogItem
from ..plant_operations.models import DailyCheckIn, ManualMeasurement
from .repository import PlantHistoryRepository


AUTHORITY_SOURCE = "postgresql_read_model"
ENTRY_SOURCE_TYPES = frozenset(
    {
        "plant_admin_audit",
        "daily_checkin",
        "manual_measurement",
        "photo_catalog_item",
    }
)
_FORBIDDEN_REF_KEYS = frozenset(
    {
        "session_id",
        "token_hash",
        "password_hash",
        "cookie",
        "cookies",
        "headers",
        "authorization",
        "auth_provenance",
        "raw_sql",
        "provider_payload",
        "hidden_reasoning",
        "raw_chat",
        "raw_companion_proposal_text",
    }
)
_OBVIOUS_LOCAL_PATH_RE = re.compile(
    r"""
    (?<!\S)
    (?:
        file://\S+
        |
        [A-Za-z]:[\\/]\S*
        |
        \\\\[^\\\s]+\\\S+
        |
        /+\S+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
_CURSOR_ALPHABET_RE = re.compile(r"[A-Za-z0-9_-]+")
_CURSOR_FIELDS = frozenset(
    {"v", "occurred_at", "recorded_at", "source_type", "source_id"}
)
_CURSOR_VERSION = 1


class PlantHistoryErrorCode(StrEnum):
    AUTH_PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    HISTORY_CURSOR_INVALID = "HISTORY_CURSOR_INVALID"
    HISTORY_LIMIT_INVALID = "HISTORY_LIMIT_INVALID"
    HISTORY_SOURCE_TYPE_INVALID = "HISTORY_SOURCE_TYPE_INVALID"
    HISTORY_PERSISTENCE_FAILED = "HISTORY_PERSISTENCE_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class PlantHistoryError(RuntimeError):
    def __init__(self, code: PlantHistoryErrorCode) -> None:
        self.code = code
        super().__init__(f"Plant history failed: {code.value}.")


@dataclass(frozen=True, slots=True)
class PlantHistoryCard:
    plant_id: uuid.UUID
    farm_id: uuid.UUID
    plant_key: str
    display_name: str
    status: str
    permissions: dict[str, object]
    latest_check_in_ref: dict[str, object] | None
    latest_ph_ref: dict[str, object] | None
    latest_ec_ref: dict[str, object] | None
    latest_ph: Decimal | None
    latest_ec_ms_cm: Decimal | None
    ph_fresh_for_analysis: bool
    ec_fresh_for_analysis: bool
    photo_count: int
    history_entry_count: int
    retained_history_mode: str
    computed_at: datetime


@dataclass(frozen=True, slots=True)
class PlantHistoryEntry:
    history_entry_id: str
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    occurred_at: datetime
    recorded_at: datetime
    actor_ref: dict[str, object] | None
    summary: dict[str, object]
    source_refs: dict[str, object] | list[object]
    event_refs: dict[str, object]
    artifact_refs: dict[str, object]
    authority_source: str = AUTHORITY_SOURCE


@dataclass(frozen=True, slots=True)
class PlantHistoryList:
    items: tuple[PlantHistoryEntry, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class _AuthorizedRead:
    plant: Plant
    permission: PlantPermissionContext
    retained_history_mode: str


RepositoryFactory = Callable[[Session], PlantHistoryRepository]


class PlantHistoryService:
    def __init__(
        self,
        session: Session,
        *,
        repository_factory: RepositoryFactory = PlantHistoryRepository,
    ) -> None:
        self._session = session
        self._repository_factory = repository_factory

    def get_card(self, actor: ActorContext, *, plant_id: uuid.UUID) -> PlantHistoryCard:
        try:
            repository = self._repository_factory(self._session)
            authorized = _require_history_read(repository, actor, plant_id=plant_id)
            computed_at = _now()
            latest_check_in = repository.latest_check_in(
                farm_id=actor.farm_id,
                plant_id=plant_id,
            )
            latest_ph = repository.latest_ph_measurement(
                farm_id=actor.farm_id,
                plant_id=plant_id,
            )
            latest_ec = repository.latest_ec_measurement(
                farm_id=actor.farm_id,
                plant_id=plant_id,
            )
            return PlantHistoryCard(
                plant_id=authorized.plant.plant_id,
                farm_id=authorized.plant.farm_id,
                plant_key=_safe_string(authorized.plant.plant_key),
                display_name=_safe_string(authorized.plant.display_name),
                status=_safe_string(authorized.plant.status),
                permissions=_permission_summary(authorized.permission),
                latest_check_in_ref=_row_ref(
                    "daily_checkin",
                    latest_check_in.check_in_id if latest_check_in else None,
                ),
                latest_ph_ref=_row_ref(
                    "manual_measurement",
                    latest_ph.measurement_id if latest_ph else None,
                ),
                latest_ec_ref=_row_ref(
                    "manual_measurement",
                    latest_ec.measurement_id if latest_ec else None,
                ),
                latest_ph=latest_ph.ph if latest_ph is not None else None,
                latest_ec_ms_cm=(
                    latest_ec.ec_ms_cm if latest_ec is not None else None
                ),
                ph_fresh_for_analysis=_measurement_is_fresh(
                    latest_ph,
                    computed_at,
                    hours=24,
                ),
                ec_fresh_for_analysis=_measurement_is_fresh(
                    latest_ec,
                    computed_at,
                    hours=24,
                ),
                photo_count=repository.count_photos(
                    farm_id=actor.farm_id,
                    plant_id=plant_id,
                ),
                history_entry_count=repository.count_history_entries(
                    farm_id=actor.farm_id,
                    plant_id=plant_id,
                ),
                retained_history_mode=_safe_string(
                    authorized.retained_history_mode
                ),
                computed_at=computed_at,
            )
        except PlantHistoryError:
            raise
        except (IntegrityError, Exception):
            raise PlantHistoryError(
                PlantHistoryErrorCode.HISTORY_PERSISTENCE_FAILED
            ) from None

    def list_history(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 50,
        source_type: str | None = None,
    ) -> PlantHistoryList:
        normalized_limit = _validate_limit(limit)
        normalized_source_type = _validate_source_type(source_type)
        cursor_key = _decode_cursor(cursor)
        try:
            repository = self._repository_factory(self._session)
            _require_history_read(repository, actor, plant_id=plant_id)
            entries = _build_entries(
                repository,
                farm_id=actor.farm_id,
                plant_id=plant_id,
            )
            if normalized_source_type is not None:
                entries = [
                    item
                    for item in entries
                    if item.source_type == normalized_source_type
                ]
            entries.sort(key=_entry_sort_key, reverse=True)
            if cursor_key is not None:
                entries = [
                    item for item in entries if _entry_sort_key(item) < cursor_key
                ]
            page = entries[:normalized_limit]
            next_cursor = None
            if len(entries) > normalized_limit and page:
                next_cursor = _encode_cursor(page[-1])
            return PlantHistoryList(items=tuple(page), next_cursor=next_cursor)
        except PlantHistoryError:
            raise
        except (IntegrityError, Exception):
            raise PlantHistoryError(
                PlantHistoryErrorCode.HISTORY_PERSISTENCE_FAILED
            ) from None


def _require_history_read(
    repository: PlantHistoryRepository,
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
) -> _AuthorizedRead:
    if not isinstance(plant_id, uuid.UUID):
        raise PlantHistoryError(PlantHistoryErrorCode.VALIDATION_FAILED)
    identity = repository.get_actor_identity(
        account_id=actor.account_id,
        membership_id=actor.membership_id,
        farm_id=actor.farm_id,
    )
    if identity is None:
        raise PlantHistoryError(PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN)
    account, membership = identity
    if (
        account.account_status != "active"
        or membership.membership_status != MembershipStatus.ACTIVE.value
        or membership.account_id != actor.account_id
        or membership.role_preset != _enum_value(actor.role_preset)
    ):
        raise PlantHistoryError(PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN)

    resolver = _BoundedPlantPermissionResolver(
        farm_id=actor.farm_id,
        membership_id=actor.membership_id,
        membership_status=actor.membership_status,
        role_preset=actor.role_preset,
        snapshot_provider=repository.get_plant_access_snapshot,
    )
    active_permission = resolver.resolve(plant_id, OperationKind.NORMAL_READ)
    if (
        active_permission.plant_status is PlantStatus.ACTIVE
        and active_permission.can_read
    ):
        plant = repository.get_plant(farm_id=actor.farm_id, plant_id=plant_id)
        if plant is None:
            raise PlantHistoryError(PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN)
        return _AuthorizedRead(
            plant=plant,
            permission=active_permission,
            retained_history_mode="active_history",
        )

    retained_permission = resolver.resolve(
        plant_id,
        OperationKind.RETAINED_HISTORY_READ,
    )
    if (
        retained_permission.plant_status is PlantStatus.ARCHIVED
        and retained_permission.can_read
    ):
        plant = repository.get_plant(farm_id=actor.farm_id, plant_id=plant_id)
        if plant is None:
            raise PlantHistoryError(PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN)
        return _AuthorizedRead(
            plant=plant,
            permission=retained_permission,
            retained_history_mode="archived_retained_history",
        )

    raise PlantHistoryError(PlantHistoryErrorCode.AUTH_PLANT_FORBIDDEN)


def _build_entries(
    repository: PlantHistoryRepository,
    *,
    farm_id: uuid.UUID,
    plant_id: uuid.UUID,
) -> list[PlantHistoryEntry]:
    entries: list[PlantHistoryEntry] = []
    entries.extend(
        _check_in_entry(row)
        for row in repository.list_check_ins(farm_id=farm_id, plant_id=plant_id)
    )
    entries.extend(
        _measurement_entry(row)
        for row in repository.list_measurements(farm_id=farm_id, plant_id=plant_id)
    )
    entries.extend(
        _photo_entry(row)
        for row in repository.list_photos(farm_id=farm_id, plant_id=plant_id)
    )
    entries.extend(
        _admin_audit_entry(row)
        for row in repository.list_admin_audits(farm_id=farm_id, plant_id=plant_id)
    )
    return entries


def _check_in_entry(row: DailyCheckIn) -> PlantHistoryEntry:
    summary = {
        "check_in_id": str(row.check_in_id),
        "check_in_state": row.check_in_state,
        "observation_state": row.observation_state,
        "has_observation_text": bool(row.observation_text),
        "observed_at": _stored_timestamp(row.observed_at).isoformat(),
        "recorded_at": _stored_timestamp(row.recorded_at).isoformat(),
    }
    return PlantHistoryEntry(
        history_entry_id=_history_entry_id("daily_checkin", row.check_in_id),
        farm_id=row.farm_id,
        plant_id=row.plant_id,
        source_type="daily_checkin",
        source_id=row.check_in_id,
        occurred_at=_stored_timestamp(row.observed_at),
        recorded_at=_stored_timestamp(row.recorded_at),
        actor_ref=_actor_ref(
            account_id=row.actor_account_id,
            membership_id=row.actor_membership_id,
            source_refs=row.source_refs,
        ),
        summary=_safe_mapping(summary),
        source_refs=_safe_mapping(
            {
                "source_type": "daily_checkin",
                "source_id": str(row.check_in_id),
                "source_refs": row.source_refs,
            }
        ),
        event_refs=_safe_mapping(row.event_refs or {}),
        artifact_refs={},
    )


def _measurement_entry(row: ManualMeasurement) -> PlantHistoryEntry:
    summary: dict[str, object] = {
        "measurement_id": str(row.measurement_id),
        "check_in_id": str(row.check_in_id) if row.check_in_id else None,
        "measured_at": _stored_timestamp(row.measured_at).isoformat(),
        "recorded_at": _stored_timestamp(row.recorded_at).isoformat(),
        "has_ph": row.ph is not None,
        "has_ec": row.ec_ms_cm is not None,
        "source_type": row.source_type,
        "trust_status": row.trust_status,
    }
    if row.ph is not None:
        summary["ph"] = row.ph
    if row.ec_ms_cm is not None:
        summary["ec_ms_cm"] = row.ec_ms_cm
    return PlantHistoryEntry(
        history_entry_id=_history_entry_id(
            "manual_measurement",
            row.measurement_id,
        ),
        farm_id=row.farm_id,
        plant_id=row.plant_id,
        source_type="manual_measurement",
        source_id=row.measurement_id,
        occurred_at=_stored_timestamp(row.measured_at),
        recorded_at=_stored_timestamp(row.recorded_at),
        actor_ref=_actor_ref(
            account_id=row.actor_account_id,
            membership_id=row.actor_membership_id,
            source_refs=row.source_refs,
        ),
        summary=_safe_mapping(summary),
        source_refs=_safe_mapping(
            {
                "source_type": "manual_measurement",
                "source_id": str(row.measurement_id),
                "source_refs": row.source_refs,
            }
        ),
        event_refs=_safe_mapping(row.event_refs or {}),
        artifact_refs={},
    )


def _photo_entry(row: PhotoCatalogItem) -> PlantHistoryEntry:
    summary = {
        "photo_id": str(row.photo_id),
        "check_in_id": str(row.check_in_id) if row.check_in_id else None,
        "photo_type": row.photo_type,
        "captured_at": _stored_timestamp(row.captured_at).isoformat(),
        "uploaded_at": _stored_timestamp(row.uploaded_at).isoformat(),
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
        "local_only": row.local_only,
        "can_train_on": row.can_train_on,
    }
    artifact_refs = {
        "original_file_ref": row.original_file_ref,
        "manifest_ref": row.manifest_ref,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
    }
    return PlantHistoryEntry(
        history_entry_id=_history_entry_id("photo_catalog_item", row.photo_id),
        farm_id=row.farm_id,
        plant_id=row.plant_id,
        source_type="photo_catalog_item",
        source_id=row.photo_id,
        occurred_at=_stored_timestamp(row.captured_at),
        recorded_at=_stored_timestamp(row.uploaded_at),
        actor_ref=_actor_ref(
            account_id=row.uploaded_by_account_id,
            membership_id=row.uploaded_by_membership_id,
            source_refs=row.source_refs,
        ),
        summary=_safe_mapping(summary),
        source_refs=_safe_mapping(
            {
                "source_type": "photo_catalog_item",
                "source_id": str(row.photo_id),
                "source_refs": row.source_refs,
            }
        ),
        event_refs=_safe_mapping(row.event_refs or {}),
        artifact_refs=_safe_mapping(artifact_refs),
    )


def _admin_audit_entry(row: AdminAuditRecord) -> PlantHistoryEntry:
    summary = {
        "admin_audit_id": str(row.admin_audit_id),
        "actor_kind": row.actor_kind,
        "action_type": row.action_type,
        "target_type": row.target_type,
        "target_id": str(row.target_id),
        "plant_id": str(row.plant_id) if row.plant_id else None,
        "request_id": row.request_id,
        "before_summary": row.before_summary,
        "after_summary": row.after_summary,
    }
    return PlantHistoryEntry(
        history_entry_id=_history_entry_id(
            "plant_admin_audit",
            row.admin_audit_id,
        ),
        farm_id=row.farm_id,
        plant_id=row.plant_id or uuid.UUID(int=0),
        source_type="plant_admin_audit",
        source_id=row.admin_audit_id,
        occurred_at=_stored_timestamp(row.created_at),
        recorded_at=_stored_timestamp(row.created_at),
        actor_ref=_safe_mapping(
            {
                "actor_kind": row.actor_kind,
                "account_id": str(row.actor_account_id)
                if row.actor_account_id
                else None,
                "membership_id": str(row.actor_membership_id)
                if row.actor_membership_id
                else None,
                "role_preset": row.actor_role_preset,
            }
        ),
        summary=_safe_mapping(summary),
        source_refs=_safe_value(row.source_refs or []),
        event_refs={},
        artifact_refs={},
    )


def _permission_summary(permission: PlantPermissionContext) -> dict[str, object]:
    summary: dict[str, object] = {
        "plant_id": str(permission.plant_id),
        "plant_status": _enum_value(permission.plant_status),
        "can_read": permission.can_read,
        "can_comment": permission.can_comment,
        "can_operate": permission.can_operate,
        "can_create_domain_tasks": permission.can_create_domain_tasks,
        "can_manage_access": permission.can_manage_access,
        "can_approve_actions": permission.can_approve_actions,
        "source": _enum_value(permission.source),
    }
    if permission.source is PermissionSource.PLANT_ACCESS_GRANT:
        summary["grant_id"] = str(permission.grant_id)
    return summary


def _actor_ref(
    *,
    account_id: uuid.UUID,
    membership_id: uuid.UUID,
    source_refs: dict[str, object],
) -> dict[str, object]:
    return _safe_mapping(
        {
            "account_id": str(account_id),
            "membership_id": str(membership_id),
            "role_preset": source_refs.get("role_preset")
            if isinstance(source_refs, dict)
            else None,
        }
    )


def _row_ref(source_type: str, source_id: uuid.UUID | None) -> dict[str, object] | None:
    if source_id is None:
        return None
    return {"source_type": source_type, "source_id": str(source_id)}


def _history_entry_id(source_type: str, source_id: uuid.UUID) -> str:
    return f"{source_type}:{source_id}"


def _validate_limit(limit: int) -> int:
    if type(limit) is not int or limit < 1 or limit > 100:
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_LIMIT_INVALID)
    return limit


def _validate_source_type(source_type: str | None) -> str | None:
    if source_type is None:
        return None
    if not isinstance(source_type, str) or source_type not in ENTRY_SOURCE_TYPES:
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_SOURCE_TYPE_INVALID)
    return source_type


def _entry_sort_key(entry: PlantHistoryEntry) -> tuple[datetime, datetime, str, str]:
    return (
        _stored_timestamp(entry.occurred_at),
        _stored_timestamp(entry.recorded_at),
        entry.source_type,
        str(entry.source_id),
    )


def _encode_cursor(entry: PlantHistoryEntry) -> str:
    occurred_at, recorded_at, source_type, source_id = _entry_sort_key(entry)
    return _encode_cursor_values(
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        source_type=source_type,
        source_id=source_id,
    )


def _encode_cursor_values(
    *,
    occurred_at: datetime,
    recorded_at: datetime,
    source_type: str,
    source_id: str,
) -> str:
    payload = {
        "v": _CURSOR_VERSION,
        "occurred_at": occurred_at.isoformat(),
        "recorded_at": recorded_at.isoformat(),
        "source_type": source_type,
        "source_id": source_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[datetime, datetime, str, str] | None:
    if cursor is None:
        return None
    if (
        not isinstance(cursor, str)
        or not cursor
        or _CURSOR_ALPHABET_RE.fullmatch(cursor) is None
    ):
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_CURSOR_INVALID)
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        decoded = base64.b64decode(
            padded.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != _CURSOR_FIELDS:
            raise ValueError
        if type(payload["v"]) is not int or payload["v"] != _CURSOR_VERSION:
            raise ValueError
        occurred_at = _parse_timestamp(payload["occurred_at"])
        recorded_at = _parse_timestamp(payload["recorded_at"])
        source_type = payload["source_type"]
        source_id = payload["source_id"]
        if not isinstance(source_type, str) or source_type not in ENTRY_SOURCE_TYPES:
            raise ValueError
        if not isinstance(source_id, str) or str(uuid.UUID(source_id)) != source_id:
            raise ValueError
        if cursor != _encode_cursor_values(
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            source_type=source_type,
            source_id=source_id,
        ):
            raise ValueError
        return (
            occurred_at,
            recorded_at,
            source_type,
            source_id,
        )
    except Exception:
        raise PlantHistoryError(PlantHistoryErrorCode.HISTORY_CURSOR_INVALID) from None


def _safe_mapping(value: dict[str, object]) -> dict[str, object]:
    safe = _safe_value(value)
    return safe if isinstance(safe, dict) else {}


def _safe_value(value: object) -> object:
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            string_key = str(key)
            redacted_key = redact_text(string_key)
            if redacted_key != string_key or _key_is_forbidden(string_key):
                continue
            safe_item = _safe_value(item)
            if safe_item is not None:
                result[string_key] = safe_item
        return result
    if isinstance(value, list | tuple):
        return [
            safe_item
            for item in value
            if (safe_item := _safe_value(item)) is not None
        ]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return _stored_timestamp(value).isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str):
        return _safe_string(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    return redact_text(str(value))


def _key_is_forbidden(key: str) -> bool:
    normalized = key.strip().lower()
    return (
        _contains_absolute_local_path(key)
        or normalized in _FORBIDDEN_REF_KEYS
        or is_sensitive_key(normalized)
        or normalized.endswith("_path")
        or normalized == "path"
    )


def _safe_string(value: str) -> str:
    if _contains_absolute_local_path(value):
        return REDACTION
    return redact_text(value)


def _contains_absolute_local_path(value: str) -> bool:
    return _OBVIOUS_LOCAL_PATH_RE.search(value) is not None


def _measurement_is_fresh(
    measurement: ManualMeasurement | None,
    computed_at: datetime,
    *,
    hours: int,
) -> bool:
    if measurement is None:
        return False
    return _stored_timestamp(measurement.measured_at) >= computed_at - timedelta(
        hours=hours
    )


def _stored_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError
    return parsed


def _enum_value(value: object) -> object:
    return value.value if hasattr(value, "value") else value


def _now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AUTHORITY_SOURCE",
    "ENTRY_SOURCE_TYPES",
    "PlantHistoryCard",
    "PlantHistoryEntry",
    "PlantHistoryError",
    "PlantHistoryErrorCode",
    "PlantHistoryList",
    "PlantHistoryService",
]
