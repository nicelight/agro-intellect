from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from backend.app.access_admin.models import Plant
from backend.app.agent_runtime import (
    AgentIntroductionBatchResultV1,
    PlantAgentBootstrapCommandV1,
    PlantAgentBootstrapService,
    build_introduction_batch,
    eligible_roster_for_plant,
)
from tests.backend.plant_operations.conftest import create_active_plant, create_actor, seed_farm


class RecordingSink:
    def __init__(self, status="accepted") -> None:
        self.status = status
        self.batches = []

    def store_batch(self, batch):
        self.batches.append(batch)
        if self.status in {"accepted", "duplicate"}:
            return AgentIntroductionBatchResultV1(
                batch_id=batch.batch_id,
                status=self.status,
                durable=True,
                accepted_count=8,
                reason_code=None,
            )
        if self.status == "rejected":
            return AgentIntroductionBatchResultV1(
                batch_id=batch.batch_id,
                status="rejected",
                durable=False,
                accepted_count=0,
                reason_code="content_conflict",
            )
        return AgentIntroductionBatchResultV1(
            batch_id=batch.batch_id,
            status="failed",
            durable=False,
            accepted_count=0,
            reason_code="persistence_failed",
        )


def test_uuidv5_names_and_ordered_batch_are_exact_and_retry_stable():
    farm_id = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    plant_id = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    first = build_introduction_batch(farm_id=farm_id, plant_id=plant_id)
    second = build_introduction_batch(farm_id=farm_id, plant_id=plant_id)
    namespace = uuid.UUID("ddbb4fc1-7253-5953-a427-9693caeafd80")
    assert first == second
    assert first.batch_id == uuid.uuid5(namespace, f"batch:v1:{plant_id}:1")
    assert tuple(item.agent_id for item in first.introductions) == (
        "companion",
        "vision_observation",
        "plant_state",
        "hydroponics_advisor",
        "task_follow_up",
        "safety_gate",
        "dataset_governance",
        "training_data_curator",
    )
    for item in first.introductions:
        assert item.introduction_id == uuid.uuid5(
            namespace, f"introduction:v1:{plant_id}:{item.agent_id}:1"
        )
        assert item.visible_to_agents is False
        assert item.consumable_by_agents is False


@pytest.mark.parametrize("status", ["accepted", "duplicate", "rejected", "failed"])
def test_bootstrap_reloads_active_plant_and_calls_sink_once(ft004_database, status):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    plant = create_active_plant(ft004_database, boss, plant_key=f"bootstrap_{status}")
    sink = RecordingSink(status)
    command = PlantAgentBootstrapCommandV1(
        farm_id=farm.farm_id,
        plant_id=plant.plant_id,
        creator_account_id=boss.account_id,
        requested_at=datetime.now(timezone.utc),
    )
    with ft004_database.session() as session:
        result = PlantAgentBootstrapService(session, sink).run(command)
    assert result is not None and result.status == status
    assert len(sink.batches) == 1
    assert len(sink.batches[0].introductions) == 8


def test_bootstrap_wrong_farm_or_missing_plant_makes_no_sink_call(ft004_database):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    plant = create_active_plant(ft004_database, boss, plant_key="bootstrap_missing")
    sink = RecordingSink()
    command = PlantAgentBootstrapCommandV1(
        farm_id=uuid.uuid4(),
        plant_id=plant.plant_id,
        creator_account_id=boss.account_id,
        requested_at=datetime.now(timezone.utc),
    )
    with ft004_database.session() as session:
        assert PlantAgentBootstrapService(session, sink).run(command) is None
    assert sink.batches == []


def test_roster_eligibility_is_derived_from_current_active_plant(ft004_database):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    plant = create_active_plant(ft004_database, boss, plant_key="derived_roster")
    with ft004_database.session() as session:
        assert len(
            eligible_roster_for_plant(
                session, farm_id=farm.farm_id, plant_id=plant.plant_id
            )
        ) == 8
    with ft004_database.session() as session, session.begin():
        row = session.get(Plant, plant.plant_id)
        row.status = "archived"
    with ft004_database.session() as session:
        assert eligible_roster_for_plant(
            session, farm_id=farm.farm_id, plant_id=plant.plant_id
        ) == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "accepted", "durable": True, "accepted_count": 7, "reason_code": None},
        {"status": "failed", "durable": False, "accepted_count": 1, "reason_code": "persistence_failed"},
        {"status": "rejected", "durable": False, "accepted_count": 0, "reason_code": "unknown"},
    ],
)
def test_partial_or_unknown_sink_results_are_unrepresentable(kwargs):
    with pytest.raises(ValueError):
        AgentIntroductionBatchResultV1(batch_id=uuid.uuid4(), **kwargs)
