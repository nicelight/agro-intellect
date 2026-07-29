from __future__ import annotations

from pathlib import Path
import uuid

import pytest

from backend.app.access_admin.models import Plant
from backend.app.agent_runtime import (
    AgentIntroductionV1,
    build_introductions,
    eligible_roster_for_plant,
)
from tests.backend.plant_operations.conftest import (
    create_active_plant,
    create_actor,
    seed_farm,
)


def test_uuidv5_names_order_and_metadata_are_exact_and_retry_stable():
    farm_id = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    plant_id = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    first = build_introductions(farm_id=farm_id, plant_id=plant_id)
    second = build_introductions(farm_id=farm_id, plant_id=plant_id)
    namespace = uuid.UUID("ddbb4fc1-7253-5953-a427-9693caeafd80")

    assert first == second
    assert tuple(item.agent_id for item in first) == (
        "companion",
        "vision_observation",
        "plant_state",
        "hydroponics_advisor",
        "task_follow_up",
        "safety_gate",
        "dataset_governance",
        "training_data_curator",
    )
    for item in first:
        assert item.introduction_id == uuid.uuid5(
            namespace,
            f"introduction:v1:{plant_id}:{item.agent_id}:1",
        )
        assert item.farm_id == farm_id
        assert item.plant_id == plant_id
        assert item.roster_version == 1
        assert item.visible_to_agents is False
        assert item.consumable_by_agents is False


def test_introduction_metadata_rejects_agent_consumability():
    with pytest.raises(ValueError):
        AgentIntroductionV1(
            introduction_id=uuid.uuid4(),
            farm_id=uuid.uuid4(),
            plant_id=uuid.uuid4(),
            roster_version=1,
            agent_id="companion",
            display_name="Companion Agent",
            competence_summary="coordination",
            introduction_text="hello",
            consumable_by_agents=True,
        )


def test_roster_eligibility_is_derived_from_current_active_plant(ft004_database):
    farm = seed_farm(ft004_database)
    boss, _ = create_actor(ft004_database, farm, "boss")
    plant = create_active_plant(
        ft004_database,
        boss,
        plant_key="derived_roster",
    )
    with ft004_database.session() as session:
        assert len(
            eligible_roster_for_plant(
                session,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
            )
        ) == 8
    with ft004_database.session() as session, session.begin():
        session.get(Plant, plant.plant_id).status = "archived"
    with ft004_database.session() as session:
        assert (
            eligible_roster_for_plant(
                session,
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
            )
            == ()
        )


def test_agent_runtime_contains_metadata_only_and_no_persistence_lifecycle():
    source = Path("backend/app/agent_runtime/bootstrap.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "PlantAgentBootstrap",
        "AgentIntroductionBatch",
        "AgentIntroductionSink",
        "content_digest",
        "store_batch",
    )
    assert all(name not in source for name in forbidden)
