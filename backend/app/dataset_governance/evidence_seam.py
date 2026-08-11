"""Shared Dataset Evidence Creation seam invocation helper.

One generalized construction point for ``RecordDatasetEvidenceCommandV1`` so
all four source owners (Photo Intake, Plant Operations daily check-in and
manual measurement, Task & Follow-Up follow-up outcome) use the same seam
invocation shape. The helper consumes the owner's bound injectable
``dataset_governance`` service and keeps same-UoW semantics; when no bound
service is injected it falls back to a default ``DatasetGovernanceService``
bound to the caller's session and timeline appender.
"""

from __future__ import annotations

from collections.abc import Callable
import uuid

from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..timeline import TimelineEvent
from .contracts import (
    RecordDatasetEvidenceCommandV1,
    RecordDatasetEvidenceResultV1,
    SourceKind,
)
from .service import DatasetGovernanceService


def record_dataset_evidence(
    governance: DatasetGovernanceService | None,
    *,
    session: Session,
    timeline_appender: Callable[[TimelineEvent], dict[str, object]],
    actor: ActorContext,
    plant_id: uuid.UUID,
    source_kind: SourceKind,
    source_ref: uuid.UUID,
) -> RecordDatasetEvidenceResultV1:
    service = governance or DatasetGovernanceService(
        session,
        timeline_appender=timeline_appender,
    )
    return service.record_dataset_evidence(
        RecordDatasetEvidenceCommandV1(
            actor_context=actor,
            plant_id=plant_id,
            source_kind=source_kind,
            source_ref=source_ref,
        )
    )


__all__ = ["record_dataset_evidence"]
