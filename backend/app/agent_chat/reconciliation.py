from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select

from ..access_admin.models import Plant
from ..agent_runtime.bootstrap import AgentIntroductionSink, build_introduction_batch
from ..database import DatabaseHandle


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    scanned: int
    durable: int
    rejected: int
    failed: int


def reconcile_active_plants(
    database: DatabaseHandle, sink: AgentIntroductionSink
) -> ReconciliationResult:
    """Converge current active Plants without replaying historical state."""

    with database.session() as session:
        active = tuple(
            session.execute(
                select(Plant.farm_id, Plant.plant_id)
                .where(Plant.status == "active")
                .order_by(Plant.plant_id)
            )
        )

    durable = rejected = failed = 0
    for farm_id, plant_id in active:
        result = sink.store_batch(
            build_introduction_batch(
                farm_id=uuid.UUID(str(farm_id)),
                plant_id=uuid.UUID(str(plant_id)),
            )
        )
        if result.durable:
            durable += 1
        elif result.status == "rejected":
            rejected += 1
        else:
            failed += 1
    return ReconciliationResult(len(active), durable, rejected, failed)


__all__ = ["ReconciliationResult", "reconcile_active_plants"]
