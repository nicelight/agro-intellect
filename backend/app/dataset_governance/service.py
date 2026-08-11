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
    AssociateFollowUpEvidenceCommandV1,
    AssociateFollowUpEvidenceResultV1,
    CandidateOrigin,
    CandidateStatus,
    CandidateTransition,
    ConfirmationSource,
    CuratorDecision,
    DatasetGovernanceError,
    DatasetGovernanceErrorCode,
    DatasetGovernanceValidationError,
    QualityTier,
    RecordDatasetEvidenceCommandV1,
    RecordDatasetEvidenceResultV1,
    SourceKind,
    TransitionDatasetCandidateCommandV1,
    TransitionDatasetCandidateResultV1,
)
from .models import DatasetCandidate
from .repository import CurrentDatasetScope, DatasetGovernanceRepository

_INITIAL_EVIDENCE_KIND = {
    SourceKind.PHOTO_CATALOG_ITEM: "photo",
    SourceKind.DAILY_CHECK_IN: "observation",
    SourceKind.MANUAL_MEASUREMENT: "measurement",
    SourceKind.FOLLOW_UP_OUTCOME: "follow_up_outcome",
}

_REVIEW_SOURCES = frozenset(
    {
        ConfirmationSource.HUMAN_REVIEW,
        ConfirmationSource.EXPERT_REVIEW,
        ConfirmationSource.BATCH_REVIEW,
    }
)

#: FT-014 transition table: (from_status, transition) -> legal to_status.
_TRANSITION_TABLE: dict[tuple[CandidateStatus, CandidateTransition], CandidateStatus] = {
    (CandidateStatus.CANDIDATE, CandidateTransition.REQUEST_REVIEW): CandidateStatus.NEEDS_REVIEW,
    (CandidateStatus.CANDIDATE, CandidateTransition.CONFIRM): CandidateStatus.CONFIRMED,
    (CandidateStatus.NEEDS_REVIEW, CandidateTransition.CONFIRM): CandidateStatus.CONFIRMED,
    (CandidateStatus.CANDIDATE, CandidateTransition.REJECT): CandidateStatus.REJECTED,
    (CandidateStatus.NEEDS_REVIEW, CandidateTransition.REJECT): CandidateStatus.REJECTED,
    (CandidateStatus.CANDIDATE, CandidateTransition.EXCLUDE): CandidateStatus.EXCLUDED,
    (CandidateStatus.NEEDS_REVIEW, CandidateTransition.EXCLUDE): CandidateStatus.EXCLUDED,
    (CandidateStatus.CONFIRMED, CandidateTransition.EXCLUDE): CandidateStatus.EXCLUDED,
}

_ELIGIBLE_ASSOCIATION_STATUSES = frozenset(
    {CandidateStatus.CANDIDATE.value, CandidateStatus.NEEDS_REVIEW.value}
)


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

    def transition_candidate(
        self,
        command: TransitionDatasetCandidateCommandV1,
    ) -> TransitionDatasetCandidateResultV1:
        if not isinstance(command, TransitionDatasetCandidateCommandV1):
            raise DatasetGovernanceValidationError()
        try:
            candidate = self._repository.candidate(
                command.candidate_id,
                for_update=False,
            )
            if candidate is None:
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.CANDIDATE_NOT_FOUND
                )
            scope = self._require_transition_scope(
                command,
                plant_id=candidate.plant_id,
            )
            locked = self._repository.candidate(
                command.candidate_id,
                for_update=True,
            )
            if locked is None:
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.CANDIDATE_NOT_FOUND
                )
            if (
                locked.farm_id != scope.farm_id
                or locked.plant_id != candidate.plant_id
            ):
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.CANDIDATE_CONFLICT
                )
            if (
                locked.candidate_status != command.expected_status.value
                or locked.record_version != command.expected_record_version
            ):
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.CANDIDATE_CONFLICT
                )

            from_status = CandidateStatus(locked.candidate_status)
            to_status = self._legal_target(from_status, command.transition)
            self._guard_transition(locked, command)
            self._apply_transition(
                locked,
                command,
                from_status=from_status,
                to_status=to_status,
            )

            can_train_on = self._derive_can_train_on(locked)
            locked.can_train_on = can_train_on
            now = self._clock()
            locked.updated_at = now
            locked.record_version += 1
            event_ref = self._append_reviewed(
                scope,
                locked,
                from_status=from_status,
                to_status=to_status,
                confirmation_source=command.confirmation_source,
                quality_tier=locked.quality_tier,
                evidence_ref_count=len(locked.evidence_refs),
                can_train_on=can_train_on,
                actor=command.actor_context,
            )
            locked.event_refs = [*locked.event_refs, event_ref]
            self._session.flush()
            return TransitionDatasetCandidateResultV1(
                result="transitioned",
                candidate_id=locked.candidate_id,
                candidate_ref=f"dataset_candidate:{locked.candidate_id}",
                from_status=from_status.value,
                to_status=to_status.value,
                can_train_on=can_train_on,
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

    def associate_follow_up_evidence(
        self,
        command: AssociateFollowUpEvidenceCommandV1,
    ) -> AssociateFollowUpEvidenceResultV1:
        if not isinstance(command, AssociateFollowUpEvidenceCommandV1):
            raise DatasetGovernanceValidationError()
        try:
            scope = self._require_association_scope(command)
            persisted_refs = self._repository.lock_outcome_row(
                command.outcome_id,
                farm_id=scope.farm_id,
                plant_id=command.plant_id,
            )
            if persisted_refs is None:
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
                )
            if list(command.evidence_refs) != persisted_refs:
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
                )
            changed: list[uuid.UUID] = []
            unchanged_match_count = 0
            for ref in command.evidence_refs:
                source_kind, source_ref = self._repository.derive_source_identity(ref)
                if source_kind is None or source_ref is None:
                    continue
                if not self._repository.lock_source_row(
                    source_kind,
                    source_ref,
                    farm_id=scope.farm_id,
                    plant_id=command.plant_id,
                ):
                    raise DatasetGovernanceError(
                        DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
                    )
                candidate = self._repository.candidate_by_source_identity(
                    plant_id=command.plant_id,
                    source_kind=source_kind.value,
                    source_ref=source_ref,
                    for_update=True,
                )
                if candidate is None:
                    continue
                if (
                    candidate.farm_id != scope.farm_id
                    or candidate.plant_id != command.plant_id
                ):
                    raise DatasetGovernanceError(
                        DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
                    )
                outcome_ref = {
                    "kind": "follow_up_outcome",
                    "ref": str(command.outcome_id),
                }
                if candidate.candidate_status not in _ELIGIBLE_ASSOCIATION_STATUSES:
                    unchanged_match_count += 1
                    continue
                if outcome_ref in candidate.evidence_refs:
                    unchanged_match_count += 1
                    continue
                candidate.evidence_refs = [*candidate.evidence_refs, outcome_ref]
                candidate.follow_up_seen = True
                candidate.record_version += 1
                candidate.updated_at = self._clock()
                event_ref = self._append_evidence_linked(
                    scope,
                    candidate,
                    actor=command.actor_context,
                )
                candidate.event_refs = [*candidate.event_refs, event_ref]
                changed.append(candidate.candidate_id)
            self._session.flush()
            return AssociateFollowUpEvidenceResultV1(
                result="associated" if changed else "noop",
                changed_candidate_ids=tuple(changed),
                unchanged_match_count=unchanged_match_count,
            )
        except DatasetGovernanceError:
            raise
        except TimelineAppendError:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.AUDIT_FAILED
            ) from None
        except IntegrityError:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.EVIDENCE_ASSOCIATION_CONFLICT
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

    def _require_transition_scope(
        self,
        command: TransitionDatasetCandidateCommandV1,
        *,
        plant_id,
    ) -> CurrentDatasetScope:
        scope = self._repository.current_scope(
            command.actor_context,
            plant_id=plant_id,
            for_update=True,
        )
        if scope is None or scope.plant_status != "active" or not scope.can_operate:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONTEXT_FORBIDDEN
            )
        return scope

    def _require_association_scope(
        self,
        command: AssociateFollowUpEvidenceCommandV1,
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

    @staticmethod
    def _legal_target(
        from_status: CandidateStatus,
        transition: CandidateTransition,
    ) -> CandidateStatus:
        target = _TRANSITION_TABLE.get((from_status, transition))
        if target is None:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
            )
        return target

    @staticmethod
    def _derive_can_train_on(candidate: DatasetCandidate) -> bool:
        return bool(
            candidate.candidate_status == CandidateStatus.CONFIRMED.value
            and candidate.evidence_refs
            and candidate.confirmation_source is not None
        )

    def _guard_transition(
        self,
        candidate: DatasetCandidate,
        command: TransitionDatasetCandidateCommandV1,
    ) -> None:
        if command.transition is not CandidateTransition.CONFIRM:
            return
        if candidate.candidate_origin == CandidateOrigin.AGENT_LABELED.value:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
            )
        resolved = self._repository.evidence_refs_resolve(
            farm_id=candidate.farm_id,
            plant_id=candidate.plant_id,
            evidence_refs=candidate.evidence_refs,
        )
        if not resolved:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.EVIDENCE_INVALID
            )
        if command.confirmation_source is ConfirmationSource.CURATOR_AUTO:
            self._guard_curator_auto(candidate, command)
        elif command.quality_tier is QualityTier.GOLD:
            if command.confirmation_source not in _REVIEW_SOURCES:
                raise DatasetGovernanceError(
                    DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
                )

    def _guard_curator_auto(
        self,
        candidate: DatasetCandidate,
        command: TransitionDatasetCandidateCommandV1,
    ) -> None:
        if command.quality_tier is QualityTier.GOLD:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.TRANSITION_FORBIDDEN
            )
        if candidate.quality_tier != QualityTier.STANDARD.value:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )
        if candidate.follow_up_seen is not True:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )
        kinds = {item.get("kind") for item in candidate.evidence_refs}
        if len(candidate.evidence_refs) < 2 or len(kinds) < 2:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )
        if "follow_up_outcome" not in kinds:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )
        if candidate.curator_decision != CuratorDecision.SELECTED.value:
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )
        if (
            candidate.curator_run_id != command.curator_run_id
            or candidate.curator_command_sha256 != command.curator_command_sha256
        ):
            raise DatasetGovernanceError(
                DatasetGovernanceErrorCode.CONFIRMATION_POLICY_VIOLATION
            )

    @staticmethod
    def _apply_transition(
        candidate: DatasetCandidate,
        command: TransitionDatasetCandidateCommandV1,
        *,
        from_status: CandidateStatus,
        to_status: CandidateStatus,
    ) -> None:
        candidate.candidate_status = to_status.value
        if to_status is CandidateStatus.CONFIRMED:
            candidate.confirmation_source = command.confirmation_source.value
            candidate.quality_tier = (
                command.quality_tier.value
                if command.quality_tier is not None
                else QualityTier.STANDARD.value
            )
        elif to_status is CandidateStatus.EXCLUDED:
            if candidate.quality_tier == QualityTier.GOLD.value:
                candidate.quality_tier = QualityTier.STANDARD.value

    def _append_reviewed(
        self,
        scope: CurrentDatasetScope,
        candidate: DatasetCandidate,
        *,
        from_status: CandidateStatus,
        to_status: CandidateStatus,
        confirmation_source: ConfirmationSource | None,
        quality_tier: str,
        evidence_ref_count: int,
        can_train_on: bool,
        actor,
    ) -> Mapping[str, object]:
        return self._timeline(
            TimelineEvent(
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                actor_ref={
                    "account_id": str(actor.account_id),
                    "membership_id": str(actor.membership_id),
                    "role_preset": scope.role_preset,
                },
                event_type="dataset_candidate_reviewed",
                source_type="dataset_candidate",
                source_id=candidate.candidate_id,
                source_refs={
                    "record_refs": [f"dataset_candidate:{candidate.candidate_id}"]
                },
                payload_summary={
                    "from_status": from_status.value,
                    "to_status": to_status.value,
                    "confirmation_source": (
                        confirmation_source.value
                        if confirmation_source is not None
                        else None
                    ),
                    "quality_tier": quality_tier,
                    "evidence_ref_count": evidence_ref_count,
                    "can_train_on": can_train_on,
                },
            )
        )

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

    def _append_evidence_linked(
        self,
        scope: CurrentDatasetScope,
        candidate: DatasetCandidate,
        *,
        actor,
    ) -> Mapping[str, object]:
        distinct_kinds = {
            item.get("kind") for item in candidate.evidence_refs
        }
        return self._timeline(
            TimelineEvent(
                farm_id=scope.farm_id,
                plant_id=scope.plant_id,
                actor_ref={
                    "account_id": str(actor.account_id),
                    "membership_id": str(actor.membership_id),
                    "role_preset": scope.role_preset,
                },
                event_type="dataset_candidate_evidence_linked",
                source_type="dataset_candidate",
                source_id=candidate.candidate_id,
                source_refs={
                    "record_refs": [f"dataset_candidate:{candidate.candidate_id}"]
                },
                payload_summary={
                    "added_evidence_kind": "follow_up_outcome",
                    "candidate_status": candidate.candidate_status,
                    "evidence_ref_count": len(candidate.evidence_refs),
                    "distinct_evidence_kind_count": len(distinct_kinds),
                    "follow_up_seen": True,
                    "can_train_on": False,
                },
            )
        )


__all__ = ["DatasetGovernanceService"]
