"""Deterministic Plant roster-introduction metadata."""

from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.models import Plant
from .roster import ROSTER_VERSION, canonical_roster


INTRODUCTION_NAMESPACE_V1 = uuid.UUID("ddbb4fc1-7253-5953-a427-9693caeafd80")


@dataclass(frozen=True, slots=True)
class AgentIntroductionV1:
    introduction_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    roster_version: int
    agent_id: str
    display_name: str
    competence_summary: str
    introduction_text: str
    schema_version: int = 1
    visible_to_agents: bool = False
    consumable_by_agents: bool = False

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.roster_version != ROSTER_VERSION
            or not isinstance(self.introduction_id, uuid.UUID)
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or not all(
                isinstance(value, str) and bool(value)
                for value in (
                    self.agent_id,
                    self.display_name,
                    self.competence_summary,
                    self.introduction_text,
                )
            )
            or self.visible_to_agents is not False
            or self.consumable_by_agents is not False
        ):
            raise ValueError("Invalid agent introduction.")


def eligible_roster_for_plant(
    session: Session, *, farm_id: uuid.UUID, plant_id: uuid.UUID
):
    """Derive eligibility from current persisted Plant state, never a registry."""

    plant = session.scalar(
        select(Plant).where(
            Plant.plant_id == plant_id,
            Plant.farm_id == farm_id,
            Plant.status == "active",
        )
    )
    return canonical_roster() if plant is not None else ()


def build_introductions(
    *, farm_id: uuid.UUID, plant_id: uuid.UUID, roster_version: int = ROSTER_VERSION
) -> tuple[AgentIntroductionV1, ...]:
    roster = canonical_roster(roster_version)
    return tuple(
        AgentIntroductionV1(
            introduction_id=uuid.uuid5(
                INTRODUCTION_NAMESPACE_V1,
                f"introduction:v1:{str(plant_id)}:{item.agent_id}:{roster_version}",
            ),
            farm_id=farm_id,
            plant_id=plant_id,
            roster_version=roster_version,
            agent_id=item.agent_id,
            display_name=item.display_name,
            competence_summary=item.competence_summary,
            introduction_text=item.introduction_text,
        )
        for item in roster
    )


__all__ = [
    "AgentIntroductionV1",
    "INTRODUCTION_NAMESPACE_V1",
    "build_introductions",
    "eligible_roster_for_plant",
]
