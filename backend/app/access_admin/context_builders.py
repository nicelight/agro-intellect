from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import TypeAlias
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.security import (
    is_valid_session_token,
    is_valid_session_token_hash,
    redact_auth_material,
)
from .actor_context import ActorContext
from .permissions import (
    OperationKind,
    PermissionSource,
    PlantPermissionContext,
    PlantStatus,
    RolePreset,
    role_policy_for,
)


JsonScalar: TypeAlias = str | int | float | bool | None
SafeContextValue: TypeAlias = JsonScalar | list["SafeContextValue"] | dict[
    str,
    "SafeContextValue",
]

_SOURCE_REF_RE = re.compile(
    r"(?P<kind>[a-z][a-z0-9_]{0,63}):"
    r"(?P<identifier>[A-Za-z0-9][A-Za-z0-9._-]{0,127})\Z"
)
_SESSION_TOKEN_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{43,}(?![A-Za-z0-9_-])"
)
_TOKEN_HASH_FRAGMENT_RE = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])",
    re.IGNORECASE,
)
_JWT_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\."
    r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    r"(?![A-Za-z0-9_-])"
)


class ContextSourceKind(StrEnum):
    DOMAIN_RECORD = "domain_record"
    UI_FEED = "ui_feed"
    RAW_CHAT = "raw_chat"
    RAW_REASONING = "raw_reasoning"
    RAW_PROVIDER_OUTPUT = "raw_provider_output"
    ADMIN_NOTICE = "admin_notice"
    UNAPPROVED_PROPOSAL = "unapproved_proposal"


@dataclass(frozen=True, slots=True)
class PlantContextCandidate:
    plant_id: uuid.UUID
    source_ref: str
    source_kind: ContextSourceKind | str
    consumable_by_agents: bool
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class SafePlantContextRecord:
    source_ref: str
    payload: dict[str, SafeContextValue]


@dataclass(frozen=True, slots=True)
class AuthorizationScope:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    role_preset: RolePreset
    operation_kind: OperationKind
    plant_status: PlantStatus
    can_read: bool
    can_comment: bool
    can_operate: bool
    can_create_domain_tasks: bool
    can_manage_access: bool
    can_approve_actions: bool
    source: PermissionSource
    grant_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class AuthorizedPlantContext:
    authorization_scope: AuthorizationScope
    records: tuple[SafePlantContextRecord, ...]


def build_authorized_plant_context(
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
    operation_kind: OperationKind | str,
    candidates: Iterable[PlantContextCandidate],
) -> AuthorizedPlantContext | None:
    try:
        operation = OperationKind(operation_kind)
    except (TypeError, ValueError):
        return None

    permission = actor.resolve_plant_permission(plant_id, operation)
    if not plant_permission_allows(permission, operation):
        return None

    records: list[SafePlantContextRecord] = []
    for candidate in candidates:
        safe_record = _safe_record(candidate, plant_id=plant_id)
        if safe_record is not None:
            records.append(safe_record)

    assert permission.plant_status is not None
    return AuthorizedPlantContext(
        authorization_scope=AuthorizationScope(
            farm_id=actor.farm_id,
            plant_id=permission.plant_id,
            role_preset=actor.role_preset,
            operation_kind=operation,
            plant_status=permission.plant_status,
            can_read=permission.can_read,
            can_comment=permission.can_comment,
            can_operate=permission.can_operate,
            can_create_domain_tasks=permission.can_create_domain_tasks,
            can_manage_access=permission.can_manage_access,
            can_approve_actions=permission.can_approve_actions,
            source=permission.source,
            grant_id=permission.grant_id,
        ),
        records=tuple(records),
    )


def _safe_record(
    candidate: object,
    *,
    plant_id: uuid.UUID,
) -> SafePlantContextRecord | None:
    if not isinstance(candidate, PlantContextCandidate):
        return None
    try:
        source_kind = ContextSourceKind(candidate.source_kind)
    except (TypeError, ValueError):
        return None
    if (
        candidate.plant_id != plant_id
        or source_kind is not ContextSourceKind.DOMAIN_RECORD
        or candidate.consumable_by_agents is not True
        or not _source_ref_is_safe(candidate.source_ref)
        or not isinstance(candidate.payload, Mapping)
        or _contains_forbidden_key(candidate.payload)
    ):
        return None
    try:
        safe_payload = _copy_safe_mapping(candidate.payload)
    except (TypeError, ValueError):
        return None
    return SafePlantContextRecord(
        source_ref=candidate.source_ref.strip(),
        payload=safe_payload,
    )


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or _key_is_forbidden(key):
                return True
            if _contains_forbidden_key(nested):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _key_is_forbidden(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    forbidden_fragments = {
        "session_id",
        "session",
        "password",
        "token",
        "credential",
        "api_key",
        "authorization",
        "auth_header",
        "cookie",
        "ui_feed",
        "raw_chat",
        "raw_reasoning",
        "admin_notice",
        "companion_proposal",
        "unapproved_proposal",
    }
    return any(fragment in normalized for fragment in forbidden_fragments)


def _copy_safe_mapping(
    value: Mapping[str, object],
) -> dict[str, SafeContextValue]:
    return {key: _copy_safe_value(nested) for key, nested in value.items()}


def _copy_safe_value(value: object) -> SafeContextValue:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        if _string_contains_auth_material(value):
            raise ValueError("Context string contains auth material.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("Context keys must be strings.")
        return _copy_safe_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_copy_safe_value(item) for item in value]
    raise TypeError("Context values must be JSON-safe.")


def _source_ref_is_safe(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    match = _SOURCE_REF_RE.fullmatch(normalized)
    if match is None or _key_is_forbidden(match.group("kind")):
        return False
    identifier = match.group("identifier")
    return not (
        is_valid_session_token(identifier)
        or is_valid_session_token_hash(identifier)
        or _string_contains_auth_material(normalized)
    )


def _string_contains_auth_material(value: str) -> bool:
    if redact_auth_material(value) != value:
        return True
    stripped = value.strip()
    if is_valid_session_token(stripped) or is_valid_session_token_hash(stripped):
        return True
    return bool(
        _SESSION_TOKEN_FRAGMENT_RE.search(value)
        or _TOKEN_HASH_FRAGMENT_RE.search(value)
        or _JWT_FRAGMENT_RE.search(value)
        or "$argon2" in value.lower()
        or "-----begin private key-----" in value.lower()
    )


def plant_permission_allows(
    permission: PlantPermissionContext,
    operation: OperationKind,
) -> bool:
    if (
        permission.source is PermissionSource.DENIED
        or permission.plant_status is None
    ):
        return False
    if operation in {
        OperationKind.NORMAL_READ,
        OperationKind.RETAINED_HISTORY_READ,
    }:
        return permission.can_read
    if operation is OperationKind.OPERATE:
        return permission.can_operate
    if operation in {
        OperationKind.MANAGE_LIFECYCLE,
        OperationKind.MANAGE_ACCESS,
    }:
        return permission.can_manage_access
    if operation is OperationKind.APPROVE_ACTION:
        return permission.can_approve_actions
    return False


def build_current_agent_bus_context(
    session: Session,
    actor: ActorContext,
    *,
    plant_id: uuid.UUID,
    limit: int = 100,
) -> AuthorizedPlantContext | None:
    """Load only typed Bus records after a same-transaction current guard."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        return None
    # Local imports keep the shared access seam independent of FT-008 at import time.
    from ..agent_chat.authorization import lock_current_plant_authorization
    from ..agent_chat.contracts import AgentChatContractError, BusEventEnvelopeV1, timestamp_text
    from ..agent_chat.models import AgentBusEvent

    auth = lock_current_plant_authorization(
        session, actor, plant_id, allow_archived=False
    )
    if auth is None:
        return None
    rows = list(
        session.scalars(
            select(AgentBusEvent)
            .where(
                AgentBusEvent.farm_id == actor.farm_id,
                AgentBusEvent.plant_id == plant_id,
                AgentBusEvent.consumable_by_agents.is_(True),
            )
            .order_by(AgentBusEvent.created_at, AgentBusEvent.event_id)
            .limit(limit)
        )
    )
    policy = role_policy_for(actor.role_preset)
    if policy is None or not policy.can_read:
        return None
    records: list[SafePlantContextRecord] = []
    try:
        for row in rows:
            envelope = BusEventEnvelopeV1.from_untrusted(
                {
                    "schema_version": 1,
                    "event_id": str(row.event_id),
                    "event_type": row.event_type,
                    "created_at": timestamp_text(row.created_at),
                    "farm_id": str(row.farm_id),
                    "plant_id": str(row.plant_id),
                    "actor_ref": row.actor_ref,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "payload": row.payload,
                    "source_refs": row.source_refs,
                    "consumable_by_agents": row.consumable_by_agents,
                    "authorization_scope": row.authorization_scope,
                }
            )
            if envelope.payload.get("record_type") == "decision_record":
                from ..companion_governance import CompanionGovernanceService

                summary = CompanionGovernanceService(
                    session
                ).get_approved_governance_summary(
                    actor,
                    plant_id=plant_id,
                    decision_record_id=uuid.UUID(envelope.source_id),
                )
                if summary is None:
                    continue
                records.append(
                    SafePlantContextRecord(
                        source_ref=f"agent_bus_event:{envelope.event_id}",
                        payload=summary.as_value(),
                    )
                )
                continue
            records.append(
                SafePlantContextRecord(
                    source_ref=f"agent_bus_event:{envelope.event_id}",
                    payload={
                        "record_type": "agent_bus_event",
                        "event_id": str(envelope.event_id),
                        "event_type": envelope.event_type,
                        "source_type": envelope.source_type,
                        "source_id": envelope.source_id,
                        "payload": _copy_safe_mapping(envelope.payload),
                        "source_refs": list(envelope.source_refs),
                        "consumable_by_agents": True,
                    },
                )
            )
    except (AgentChatContractError, TypeError, ValueError):
        return None
    can_approve_actions = policy.can_approve_actions
    if actor.role_preset is RolePreset.ENGINEER:
        from .models import PlantAccessGrant

        grant = session.scalar(
            select(PlantAccessGrant).where(
                PlantAccessGrant.grant_id == auth.grant_id,
                PlantAccessGrant.status == "active",
            )
        )
        if grant is None:
            return None
        can_approve_actions = grant.plant_approve_actions is True
    return AuthorizedPlantContext(
        authorization_scope=AuthorizationScope(
            farm_id=auth.farm_id,
            plant_id=auth.plant_id,
            role_preset=actor.role_preset,
            operation_kind=OperationKind.NORMAL_READ,
            plant_status=PlantStatus.ACTIVE,
            can_read=True,
            can_comment=policy.can_comment,
            can_operate=policy.can_operate,
            can_create_domain_tasks=policy.can_create_domain_tasks,
            can_manage_access=policy.can_manage_access,
            can_approve_actions=can_approve_actions,
            source=PermissionSource(auth.permission_source),
            grant_id=auth.grant_id,
        ),
        records=tuple(records),
    )


__all__ = [
    "AuthorizationScope",
    "AuthorizedPlantContext",
    "ContextSourceKind",
    "PlantContextCandidate",
    "SafePlantContextRecord",
    "build_authorized_plant_context",
    "build_current_agent_bus_context",
    "plant_permission_allows",
]
