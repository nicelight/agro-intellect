from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from .authorization import lock_current_plant_authorization
from .contracts import UIFeedEventV1, timestamp_text
from .models import UIFeedEvent


class PlantFeedErrorCode(StrEnum):
    AUTH_PLANT_FORBIDDEN = "AUTH_PLANT_FORBIDDEN"
    FEED_CURSOR_INVALID = "FEED_CURSOR_INVALID"
    FEED_LIMIT_INVALID = "FEED_LIMIT_INVALID"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    FEED_PERSISTENCE_FAILED = "FEED_PERSISTENCE_FAILED"


class PlantFeedError(Exception):
    def __init__(self, code: PlantFeedErrorCode): self.code = code


@dataclass(frozen=True, slots=True)
class PlantFeedPage:
    items: tuple[UIFeedEventV1, ...]
    next_cursor: str | None


class PlantFeedService:
    def __init__(self, session: Session) -> None: self._session = session

    def list_feed(self, actor: ActorContext, *, plant_id: uuid.UUID, cursor: str | None, limit: int) -> PlantFeedPage:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise PlantFeedError(PlantFeedErrorCode.FEED_LIMIT_INVALID)
        auth = lock_current_plant_authorization(self._session, actor, plant_id, allow_archived=True)
        if auth is None: raise PlantFeedError(PlantFeedErrorCode.AUTH_PLANT_FORBIDDEN)
        after = _decode_cursor(cursor) if cursor is not None else None
        query = select(UIFeedEvent).where(UIFeedEvent.plant_id == plant_id, UIFeedEvent.farm_id == actor.farm_id)
        if after is not None:
            created_at, event_id = after
            query = query.where(or_(UIFeedEvent.created_at > created_at, and_(UIFeedEvent.created_at == created_at, UIFeedEvent.ui_event_id > event_id)))
        rows = [
            row
            for row in self._session.scalars(
                query.order_by(UIFeedEvent.created_at, UIFeedEvent.ui_event_id)
            )
            if actor.role_preset.value in row.visible_to_roles
        ]
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = tuple(UIFeedEventV1.from_untrusted(_row_value(row)) for row in rows)
        next_cursor = _encode_cursor(rows[-1].created_at, rows[-1].ui_event_id) if has_more and rows else None
        return PlantFeedPage(items, next_cursor)


def _row_value(row: UIFeedEvent) -> dict[str, object]:
    return {"schema_version": 1, "ui_event_id": str(row.ui_event_id), "created_at": timestamp_text(row.created_at), "farm_id": str(row.farm_id), "plant_id": str(row.plant_id), "source_type": row.source_type, "source_id": row.source_id, "source_refs": row.source_refs, "display_kind": row.display_kind, "display_payload": row.display_payload, "visible_to_roles": row.visible_to_roles, "visible_to_agents": row.visible_to_agents, "consumable_by_agents": row.consumable_by_agents}


def _encode_cursor(created_at: datetime, event_id: uuid.UUID) -> str:
    raw = json.dumps({"v": 1, "created_at": timestamp_text(created_at), "ui_event_id": str(event_id)}, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, uuid.UUID]:
    try:
        if not value or "=" in value: raise ValueError
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw)
        if not isinstance(payload, dict) or list(payload) != ["v", "created_at", "ui_event_id"] or payload["v"] != 1: raise ValueError
        created = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
        event_id = uuid.UUID(payload["ui_event_id"])
        if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created) or str(event_id) != payload["ui_event_id"] or _encode_cursor(created, event_id) != value: raise ValueError
        return created, event_id
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        raise PlantFeedError(PlantFeedErrorCode.FEED_CURSOR_INVALID) from None


__all__ = ["PlantFeedError", "PlantFeedErrorCode", "PlantFeedPage", "PlantFeedService"]
