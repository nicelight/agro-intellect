"""Sole Dataset Candidate creation seam for FT-014.

``DatasetGovernanceService.record_dataset_evidence`` is the only production
path that creates a ``dataset_candidates`` row. It runs inside the caller-owned
unit of work: candidate insert and the caller's source mutation commit or roll
back together. Callers pass only service-side identities; the seam revalidates
the current session/account/membership/active-Plant/grant before writing and
appends exactly one redacted ``dataset_candidate_created`` Timeline ref.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..timeline import TimelineAppendError, TimelineEvent, TimelineJsonlAppender
from .contracts import (
    CandidateOrigin,
    CandidateStatus,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceValidationError,
    QualityTier,
    RecordDatasetEvidenceCommandV1,
    RecordDatasetEvidenceResultV1,
    SourceKind,
)
from .models import DatasetCandidate
from .repository import CurrentDatasetScope, DatasetGovernanceRepository

_INITIAL_EVIDENCE_KIND = {
    SourceKind.PHOTO_CATALOG_ITEM: "photo",
    SourceKind.DAILY_CHECK_IN: "observation",
    SourceKind.MANUAL_MEASUREMENT: "measurement",
    SourceKind.FOLLOW_UP_OUTCOME: "follow_up_outcome",
}


class DatasetGovernanceService:
    def __init__(
        self,
        session: Session,
        *,
        timeline_appender: Callable[[TimelineEvent], dict[str, object]] | None = None,
        repository: DatasetGovernanceRepository | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or DatasetGovernanceRepository(session)
        self._timeline = timeline_appender or TimelineJsonlAppender()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def record_dataset_evidence(
        self,
        command: RecordDatasetEvidenceCommandV1,
    ) -> RecordDatasetEvidenceResultV1:
        if not isinstance(command, RecordDatasetEvidenceCommandV1):
            raise DatasetGovernanceValidationError()
        try:
            scope = self._require_create_scope(command)
            existing = self._repository.candidate_by_source_identity(
                plant_id=command.plant_id,
                source_kind=command.source_kind.value,
                source_ref=command.source_ref,
                for_update=True,
            )
            if existing is not None:
                return RecordDatasetEvidenceResultV1(
                    result="duplicate",
                    candidate_id=existing.candidate_id,
                    candidate_ref=f"dataset_candidate:{existing.candidate_id}",
                    event_ref=existing.event_refs[-1],
                )

            candidate_id = uuid.uuid4()
            now = self._clock()
            evidence_kind = _INITIAL_EVIDENCE_KIND[command.source_kind]
            event_ref = self._append_created(
                scope,
                candidate_id=candidate_id,
                source_kind=command.source_kind,
                source_ref=command.source_ref,
                evidence_kind=evidence_kind,
                actor=command.actor_context,
            )
            candidate = DatasetCandidate(
                candidate_id=candidate_id,
                farm_id=scope.farm_id,
                plant_id=command.plant_id,
                candidate_status=CandidateStatus.CANDIDATE.value,
                candidate_origin=CandidateOrigin.RAW.value,
                quality_tier=QualityTier.STANDARD.value,
                split=None,
                confirmation_source=None,
                evidence_refs=[
                    {"kind": evidence_kind, "ref": str(command.source_ref)}
                ],
                source_kind=command.source_kind.value,
                source_ref=command.source_ref,
                curator_decision=None,
                curator_notes_ref=None,
                curator_run_id=None,
                curator_command_sha256=None,
                curator_recorded_at=None,
                corrected=False,
                follow_up_seen=(
                    command.source_kind is SourceKind.FOLLOW_UP_OUTCOME
                ),
                can_train_on=False,
                record_version=1,
                event_refs=[event_ref],
                created_at=now,
                updated_at=now,
            )
            self._session.add(candidate)
            self._session.flush()
            return RecordDatasetEvidenceResultV1(
                result="created",
                candidate_id=candidate_id,
                candidate_ref=f"dataset_candidate:{candidate_id}",
                event_ref=event_ref,
            )
        except DatasetGovernanceError:
            raise
        except TimelineAppendError:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.AUDIT_FAILED
            ) from None
        except IntegrityError:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CANDIDATE_CONFLICT
            ) from None
        except (SQLAlchemyError, TypeError, ValueError):
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.PERSISTENCE_FAILED
            ) from None

    def _require_create_scope(
        self,
        command: RecordDatasetEvidenceCommandV1,
    ) -> CurrentDatasetScope:
        scope = self._repository.current_scope(
            command.actor_context,
            plant_id=command.plant_id,
            for_update=True,
        )
        if scope is None or scope.plant_status != "active" or not scope.can_operate:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN
            )
        return scope

    def _append_created(
        self,
        scope: CurrentDatasetScope,
        *,
        candidate_id: uuid.UUID,
        source_kind: SourceKind,
        source_ref: uuid.UUID,
        evidence_kind: str,
        actor,
    ) -> Mapping[str, object]:
        refs = [
            f"dataset_candidate:{candidate_id}",
            f"{source_kind.value}:{source_ref}",
        ]
        return self._timeline(
            TimelineEvent(
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                actor_ref={
                    "account_id": str(actor.account_id),
                    "membership_id": str(actor.membership_id),
                    "role_preset": scope.role_preset,
                },
                event_type="dataset_candidate_created",
                source_type="dataset_candidate",
                source_id=candidate_id,
                source_refs={"record_refs": refs},
                payload_summary={
                    "source_kind": source_kind.value,
                    "candidate_origin": CandidateOrigin.RAW.value,
                    "candidate_status": CandidateStatus.CANDIDATE.value,
                    "evidence_ref_count": 1,
                    "quality_tier": QualityTier.STANDARD.value,
                    "can_train_on": False,
                },
            )
        )


__all__ = ["DatasetGovernanceService"]
