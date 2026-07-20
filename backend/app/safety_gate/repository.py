"""First-write-wins repository for authoritative Safety classifications."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from ..agent_chat.models import UIFeedEvent
from ..plant_operations.models import ManualMeasurement
from ..plant_operations.repository import PlantOperationsRepository
from .models import SafetyActionDecision, SafetyClassification


@dataclass(frozen=True, slots=True)
class ClassificationWriteResult:
    status: str
    row: SafetyClassification

    def __post_init__(self) -> None:
        if self.status not in {"inserted", "identical", "conflict"} or not isinstance(
            self.row, SafetyClassification
        ):
            raise ValueError("Invalid classification write result.")


@dataclass(frozen=True, slots=True)
class DecisionWriteResult:
    status: str
    row: SafetyActionDecision

    def __post_init__(self) -> None:
        if self.status not in {"inserted", "identical", "conflict"} or not isinstance(
            self.row, SafetyActionDecision
        ):
            raise ValueError("Invalid Safety decision write result.")


class CurrentGuardLockUnavailable(RuntimeError):
    """A concurrent authority mutation owns a later guard row."""


class SafetyClassificationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self,
        message_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> SafetyClassification | None:
        statement = (
            select(SafetyClassification)
            .where(SafetyClassification.message_id == message_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def lock_current_guard_rows(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> None:
        """Serialize current authority and Plant state with classification write."""

        local_session = select(LocalSession).where(
            LocalSession.session_id == actor.session_id
        )
        plant = select(Plant).where(
            Plant.plant_id == plant_id,
            Plant.farm_id == actor.farm_id,
        )
        later_guard_rows = (
            select(Account).where(Account.account_id == actor.account_id),
            select(FarmMembership).where(
                FarmMembership.membership_id == actor.membership_id,
                FarmMembership.farm_id == actor.farm_id,
            ),
            select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == actor.membership_id,
                PlantAccessGrant.plant_id == plant_id,
            ),
        )
        # LocalSession is the sole safe pre-Plant lock: Farm lifecycle/access
        # mutations never acquire it. Established target-row order is Plant
        # before Account/Membership/Grant.
        for statement in (local_session, plant):
            self._session.scalar(
                statement.with_for_update().execution_options(populate_existing=True)
            )
        # Some actor-owned commands use identity-before-Plant. Do not wait on
        # those later rows while holding Plant; the service restarts only this
        # write transaction and repeats the current guard.
        for statement in later_guard_rows:
            try:
                self._session.scalar(
                    statement.with_for_update(nowait=True).execution_options(
                        populate_existing=True
                    )
                )
            except OperationalError as error:
                if getattr(error.orig, "sqlstate", None) == "55P03":
                    raise CurrentGuardLockUnavailable from None
                raise

    def persist_first(
        self,
        candidate: SafetyClassification,
    ) -> ClassificationWriteResult:
        if not isinstance(candidate, SafetyClassification):
            raise TypeError("Invalid classification row.")
        existing = self.get(candidate.message_id, for_update=True)
        if existing is not None:
            return ClassificationWriteResult(
                "identical" if _same_authority(existing, candidate) else "conflict",
                existing,
            )

        try:
            with self._session.begin_nested():
                self._session.add(candidate)
                self._session.flush()
        except IntegrityError:
            existing = self.get(candidate.message_id, for_update=True)
            if existing is None:
                raise
            return ClassificationWriteResult(
                "identical" if _same_authority(existing, candidate) else "conflict",
                existing,
            )
        return ClassificationWriteResult("inserted", candidate)


class SafetyActionDecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._classification = SafetyClassificationRepository(session)
        self._operations = PlantOperationsRepository(session)

    def get_classification(
        self,
        message_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> SafetyClassification | None:
        return self._classification.get(message_id, for_update=for_update)

    def lock_current_guard_rows(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> None:
        self._classification.lock_current_guard_rows(actor, plant_id=plant_id)

    def get_decision(
        self,
        classification_message_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> SafetyActionDecision | None:
        statement = (
            select(SafetyActionDecision)
            .where(
                SafetyActionDecision.classification_message_id
                == classification_message_id
            )
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_projection(self, decision_id: uuid.UUID) -> UIFeedEvent | None:
        return self._session.scalar(
            select(UIFeedEvent)
            .where(UIFeedEvent.ui_event_id == decision_id)
            .execution_options(populate_existing=True)
        )

    def current_grant(
        self,
        actor: ActorContext,
        *,
        plant_id: uuid.UUID,
    ) -> PlantAccessGrant | None:
        return self._session.scalar(
            select(PlantAccessGrant)
            .where(
                PlantAccessGrant.membership_id == actor.membership_id,
                PlantAccessGrant.plant_id == plant_id,
            )
            .execution_options(populate_existing=True)
        )

    def latest_ph_measurement(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> ManualMeasurement | None:
        return self._operations.latest_ph_measurement(
            farm_id=farm_id,
            plant_id=plant_id,
        )

    def latest_ec_measurement(
        self,
        *,
        farm_id: uuid.UUID,
        plant_id: uuid.UUID,
    ) -> ManualMeasurement | None:
        return self._operations.latest_ec_measurement(
            farm_id=farm_id,
            plant_id=plant_id,
        )

    def persist_first(
        self,
        decision: SafetyActionDecision,
        projection: UIFeedEvent,
    ) -> DecisionWriteResult:
        if not isinstance(decision, SafetyActionDecision) or not isinstance(
            projection, UIFeedEvent
        ):
            raise TypeError("Invalid Safety decision transaction rows.")
        if projection.ui_event_id != decision.decision_id:
            raise ValueError("Safety decision projection identity mismatch.")

        existing = self.get_decision(
            decision.classification_message_id,
            for_update=True,
        )
        if existing is not None:
            return DecisionWriteResult(
                "identical" if existing.decision_id == decision.decision_id else "conflict",
                existing,
            )
        try:
            with self._session.begin_nested():
                self._session.add(decision)
                self._session.add(projection)
                self._session.flush()
        except IntegrityError:
            existing = self.get_decision(
                decision.classification_message_id,
                for_update=True,
            )
            if existing is None:
                raise
            return DecisionWriteResult(
                "identical" if existing.decision_id == decision.decision_id else "conflict",
                existing,
            )
        return DecisionWriteResult("inserted", decision)


def _same_authority(
    existing: SafetyClassification,
    candidate: SafetyClassification,
) -> bool:
    return (
        existing.message_id == candidate.message_id
        and existing.input_sha256 == candidate.input_sha256
        and existing.result_sha256 == candidate.result_sha256
    )


__all__ = [
    "ClassificationWriteResult",
    "CurrentGuardLockUnavailable",
    "DecisionWriteResult",
    "SafetyActionDecisionRepository",
    "SafetyClassificationRepository",
]
