"""Post-commit deterministic Plant roster-introduction handoff."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access_admin.models import Plant
from .roster import ROSTER_VERSION, canonical_roster


INTRODUCTION_NAMESPACE_V1 = uuid.UUID("ddbb4fc1-7253-5953-a427-9693caeafd80")


@dataclass(frozen=True, slots=True)
class PlantAgentBootstrapCommandV1:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    requested_at: datetime
    creator_account_id: uuid.UUID
    roster_version: int = ROSTER_VERSION
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            self.schema_version != 1
            or self.roster_version != ROSTER_VERSION
            or not isinstance(self.farm_id, uuid.UUID)
            or not isinstance(self.plant_id, uuid.UUID)
            or not isinstance(self.creator_account_id, uuid.UUID)
            or not isinstance(self.requested_at, datetime)
            or self.requested_at.tzinfo is None
            or self.requested_at.utcoffset() is None
        ):
            raise ValueError("Invalid Plant agent bootstrap command.")


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


@dataclass(frozen=True, slots=True)
class AgentIntroductionBatchV1:
    batch_id: uuid.UUID
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    roster_version: int
    introductions: tuple[AgentIntroductionV1, ...]
    schema_version: int = 1
    source_type: Literal["system"] = "system"
    source_id: Literal["agent_roster_v1"] = "agent_roster_v1"

    def __post_init__(self) -> None:
        introductions = tuple(self.introductions)
        expected_ids = tuple(item.agent_id for item in canonical_roster())
        if (
            self.schema_version != 1
            or self.roster_version != ROSTER_VERSION
            or self.source_type != "system"
            or self.source_id != "agent_roster_v1"
            or len(introductions) != 8
            or tuple(item.agent_id for item in introductions) != expected_ids
            or any(
                item.farm_id != self.farm_id
                or item.plant_id != self.plant_id
                or item.roster_version != self.roster_version
                for item in introductions
            )
        ):
            raise ValueError("Invalid agent introduction batch.")
        object.__setattr__(self, "introductions", introductions)


@dataclass(frozen=True, slots=True)
class AgentIntroductionBatchResultV1:
    batch_id: uuid.UUID
    status: Literal["accepted", "duplicate", "rejected", "failed"]
    durable: bool
    accepted_count: int
    reason_code: str | None
    schema_version: int = 1

    def __post_init__(self) -> None:
        valid = (
            self.schema_version == 1
            and isinstance(self.batch_id, uuid.UUID)
            and (
                (
                    self.status in {"accepted", "duplicate"}
                    and self.durable is True
                    and self.accepted_count == 8
                    and self.reason_code is None
                )
                or (
                    self.status == "rejected"
                    and self.durable is False
                    and self.accepted_count == 0
                    and self.reason_code
                    in {"plant_not_publishable", "batch_invalid", "content_conflict"}
                )
                or (
                    self.status == "failed"
                    and self.durable is False
                    and self.accepted_count == 0
                    and self.reason_code == "persistence_failed"
                )
            )
        )
        if not valid:
            raise ValueError("Invalid closed introduction sink result.")


class AgentIntroductionSink(Protocol):
    def store_batch(
        self, batch: AgentIntroductionBatchV1
    ) -> AgentIntroductionBatchResultV1: ...


class UnavailableAgentIntroductionSink:
    """Truthful production placeholder until FT-008 supplies durable storage."""

    def store_batch(
        self, batch: AgentIntroductionBatchV1
    ) -> AgentIntroductionBatchResultV1:
        return AgentIntroductionBatchResultV1(
            batch_id=batch.batch_id,
            status="failed",
            durable=False,
            accepted_count=0,
            reason_code="persistence_failed",
        )


class PlantAgentBootstrapService:
    def __init__(self, session: Session, sink: AgentIntroductionSink) -> None:
        self._session = session
        self._sink = sink

    def run(
        self, command: PlantAgentBootstrapCommandV1
    ) -> AgentIntroductionBatchResultV1 | None:
        plant = self._session.scalar(
            select(Plant).where(
                Plant.plant_id == command.plant_id,
                Plant.farm_id == command.farm_id,
                Plant.status == "active",
            )
        )
        if plant is None:
            return None
        batch = build_introduction_batch(
            farm_id=command.farm_id,
            plant_id=command.plant_id,
            roster_version=command.roster_version,
        )
        result = self._sink.store_batch(batch)
        if not isinstance(result, AgentIntroductionBatchResultV1):
            raise ValueError("Introduction sink returned an invalid result.")
        if result.batch_id != batch.batch_id:
            raise ValueError("Introduction sink returned a mismatched batch id.")
        return result


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


def build_introduction_batch(
    *, farm_id: uuid.UUID, plant_id: uuid.UUID, roster_version: int = ROSTER_VERSION
) -> AgentIntroductionBatchV1:
    roster = canonical_roster(roster_version)
    batch_id = uuid.uuid5(
        INTRODUCTION_NAMESPACE_V1,
        f"batch:v1:{str(plant_id)}:{roster_version}",
    )
    introductions = tuple(
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
    return AgentIntroductionBatchV1(
        batch_id=batch_id,
        farm_id=farm_id,
        plant_id=plant_id,
        roster_version=roster_version,
        introductions=introductions,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "AgentIntroductionBatchResultV1",
    "AgentIntroductionBatchV1",
    "AgentIntroductionSink",
    "AgentIntroductionV1",
    "INTRODUCTION_NAMESPACE_V1",
    "PlantAgentBootstrapCommandV1",
    "PlantAgentBootstrapService",
    "UnavailableAgentIntroductionSink",
    "build_introduction_batch",
    "eligible_roster_for_plant",
]
