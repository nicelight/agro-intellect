from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ..access_admin.models import Plant
from ..agent_runtime.bootstrap import (
    AgentIntroductionBatchResultV1,
    AgentIntroductionBatchV1,
    build_introduction_batch,
)
from ..database import DatabaseHandle
from .models import AgentIntroductionBatch, UIFeedEvent


class PostgreSQLAgentIntroductionSink:
    """Atomic durable implementation of the FT-007 introduction sink port."""

    def __init__(self, database: DatabaseHandle) -> None:
        self._database = database

    def store_batch(
        self, batch: AgentIntroductionBatchV1
    ) -> AgentIntroductionBatchResultV1:
        if not _is_canonical_batch(batch):
            return _result(batch, "rejected", "batch_invalid")
        digest = _content_digest(batch)
        try:
            with self._database.session() as session:
                with session.begin():
                    plant = session.scalar(
                        select(Plant)
                        .where(
                            Plant.plant_id == batch.plant_id,
                            Plant.farm_id == batch.farm_id,
                            Plant.status == "active",
                        )
                        .with_for_update()
                    )
                    if plant is None:
                        return _result(
                            batch, "rejected", "plant_not_publishable"
                        )
                    existing = session.scalar(
                        select(AgentIntroductionBatch)
                        .where(
                            AgentIntroductionBatch.plant_id == batch.plant_id,
                            AgentIntroductionBatch.roster_version
                            == batch.roster_version,
                        )
                        .with_for_update()
                    )
                    if existing is not None:
                        if _existing_matches(session, existing, batch, digest):
                            return _result(batch, "duplicate")
                        return _result(batch, "rejected", "content_conflict")

                    existing_event_ids = set(
                        session.scalars(
                            select(UIFeedEvent.ui_event_id).where(
                                UIFeedEvent.ui_event_id.in_(
                                    [item.introduction_id for item in batch.introductions]
                                )
                            )
                        )
                    )
                    if existing_event_ids:
                        return _result(batch, "rejected", "content_conflict")

                    session.add(
                        AgentIntroductionBatch(
                            batch_id=batch.batch_id,
                            farm_id=batch.farm_id,
                            plant_id=batch.plant_id,
                            roster_version=batch.roster_version,
                            content_sha256=digest,
                        )
                    )
                    session.add_all(_event_from(item) for item in batch.introductions)
                    session.flush()
            return _result(batch, "accepted")
        except SQLAlchemyError:
            return _result(batch, "failed", "persistence_failed")


def _is_canonical_batch(batch: object) -> bool:
    if not isinstance(batch, AgentIntroductionBatchV1):
        return False
    try:
        expected = build_introduction_batch(
            farm_id=batch.farm_id,
            plant_id=batch.plant_id,
            roster_version=batch.roster_version,
        )
    except (TypeError, ValueError):
        return False
    return batch == expected


def _content_digest(batch: AgentIntroductionBatchV1) -> str:
    content = {
        "schema_version": batch.schema_version,
        "batch_id": str(batch.batch_id),
        "farm_id": str(batch.farm_id),
        "plant_id": str(batch.plant_id),
        "roster_version": batch.roster_version,
        "source_type": batch.source_type,
        "source_id": batch.source_id,
        "introductions": [_introduction_payload(item) for item in batch.introductions],
    }
    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _introduction_payload(item) -> dict[str, object]:
    return {
        "schema_version": item.schema_version,
        "introduction_id": str(item.introduction_id),
        "farm_id": str(item.farm_id),
        "plant_id": str(item.plant_id),
        "roster_version": item.roster_version,
        "agent_id": item.agent_id,
        "display_name": item.display_name,
        "competence_summary": item.competence_summary,
        "introduction_text": item.introduction_text,
        "visible_to_agents": item.visible_to_agents,
        "consumable_by_agents": item.consumable_by_agents,
    }


def _display_payload(item) -> dict[str, object]:
    return {
        "payload_kind": "agent_introduction",
        "agent_id": item.agent_id,
        "display_name": item.display_name,
        "competence_summary": item.competence_summary,
        "introduction_text": item.introduction_text,
        "roster_version": item.roster_version,
    }


def _event_from(item) -> UIFeedEvent:
    return UIFeedEvent(
        ui_event_id=item.introduction_id,
        farm_id=item.farm_id,
        plant_id=item.plant_id,
        source_type="system",
        source_id=str(item.introduction_id),
        source_refs=[
            f"agent_roster:{item.roster_version}",
            f"agent_introduction:{item.introduction_id}",
        ],
        display_kind="agent_introduction",
        display_payload=_display_payload(item),
        visible_to_roles=["boss", "engineer", "consultant"],
        visible_to_agents=False,
        consumable_by_agents=False,
        agent_id=item.agent_id,
        roster_version=item.roster_version,
    )


def _existing_matches(session, existing, batch, digest: str) -> bool:
    if (
        existing.batch_id != batch.batch_id
        or existing.farm_id != batch.farm_id
        or existing.content_sha256 != digest
    ):
        return False
    events = list(
        session.scalars(
            select(UIFeedEvent)
            .where(
                UIFeedEvent.plant_id == batch.plant_id,
                UIFeedEvent.roster_version == batch.roster_version,
                UIFeedEvent.display_kind == "agent_introduction",
            )
            .order_by(UIFeedEvent.agent_id)
        )
    )
    expected_by_id = {item.introduction_id: _event_from(item) for item in batch.introductions}
    if len(events) != len(expected_by_id):
        return False
    for event in events:
        expected = expected_by_id.get(event.ui_event_id)
        if expected is None or any(
            getattr(event, field) != getattr(expected, field)
            for field in (
                "farm_id",
                "plant_id",
                "source_type",
                "source_id",
                "source_refs",
                "display_kind",
                "display_payload",
                "visible_to_roles",
                "visible_to_agents",
                "consumable_by_agents",
                "agent_id",
                "roster_version",
            )
        ):
            return False
    return True


def _result(
    batch: AgentIntroductionBatchV1,
    status: str,
    reason_code: str | None = None,
) -> AgentIntroductionBatchResultV1:
    durable = status in {"accepted", "duplicate"}
    return AgentIntroductionBatchResultV1(
        batch_id=batch.batch_id,
        status=status,
        durable=durable,
        accepted_count=8 if durable else 0,
        reason_code=reason_code,
    )


__all__ = ["PostgreSQLAgentIntroductionSink"]
