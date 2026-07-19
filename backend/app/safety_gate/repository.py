"""First-write-wins repository for authoritative Safety classifications."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..access_admin.actor_context import ActorContext
from ..access_admin.models import (
    Account,
    FarmMembership,
    LocalSession,
    Plant,
    PlantAccessGrant,
)
from .models import SafetyClassification


@dataclass(frozen=True, slots=True)
class ClassificationWriteResult:
    status: str
    row: SafetyClassification

    def __post_init__(self) -> None:
        if self.status not in {"inserted", "identical", "conflict"} or not isinstance(
            self.row, SafetyClassification
        ):
            raise ValueError("Invalid classification write result.")


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

        statements = (
            select(LocalSession).where(LocalSession.session_id == actor.session_id),
            select(Account).where(Account.account_id == actor.account_id),
            select(FarmMembership).where(
                FarmMembership.membership_id == actor.membership_id,
                FarmMembership.farm_id == actor.farm_id,
            ),
            select(Plant).where(
                Plant.plant_id == plant_id,
                Plant.farm_id == actor.farm_id,
            ),
            select(PlantAccessGrant).where(
                PlantAccessGrant.membership_id == actor.membership_id,
                PlantAccessGrant.plant_id == plant_id,
            ),
        )
        for statement in statements:
            self._session.scalar(
                statement.with_for_update().execution_options(populate_existing=True)
            )

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


def _same_authority(
    existing: SafetyClassification,
    candidate: SafetyClassification,
) -> bool:
    return (
        existing.message_id == candidate.message_id
        and existing.input_sha256 == candidate.input_sha256
        and existing.result_sha256 == candidate.result_sha256
    )


__all__ = ["ClassificationWriteResult", "SafetyClassificationRepository"]
