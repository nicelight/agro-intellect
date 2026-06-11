"""Tests: tomato_001 is present as the initial Plant seed.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
Verification: tomato_001 is present as initial Plant seed/migration target
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.access import (
    Account,
    AccountStatus,
    Farm,
    FarmMembership,
    FarmStatus,
    MembershipRole,
    MembershipStatus,
)
from backend.app.plants import (
    Plant,
    PlantStatus,
    TOMATO_001_FARM_ID,
    TOMATO_001_PLANT_ID,
)
from backend.tests.doubles import FakePlantRepository


NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


class TestTomato001Seed:
    async def test_tomato_001_present_after_seed(self):
        repo = FakePlantRepository(auto_seed=True)
        plant = await repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.plant_id == "tomato_001"
        assert plant.canonical_label == "Tomato 001"
        assert plant.display_name == "Tomato 001"
        assert plant.state is PlantStatus.ACTIVE
        assert plant.farm_id == "farm_local"

    async def test_tomato_001_absent_when_auto_seed_false(self):
        repo = FakePlantRepository(auto_seed=False)
        assert await repo.get_plant(TOMATO_001_PLANT_ID) is None

    async def test_plant_count_includes_tomato_001(self):
        repo = FakePlantRepository(auto_seed=True)
        assert await repo.get_plant_count() == 1
        plants = await repo.get_active_plants_by_farm("farm_local")
        assert plants[0].plant_id == "tomato_001"

    async def test_tomato_001_is_active(self):
        repo = FakePlantRepository(auto_seed=True)
        plant = await repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.is_active

    async def test_tomato_001_created_by_system_seed(self):
        repo = FakePlantRepository(auto_seed=True)
        plant = await repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.created_by_actor_ref == "system_seed"

    def test_tomato_001_in_migration_sql(self):
        migration_path = "backend/app/db/migrations/0003_plant_seed.sql"
        with open(migration_path) as f:
            content = f.read()
        assert "tomato_001" in content
        assert "INSERT INTO plants" in content
        assert "-- Seed tomato_001" in content

    async def test_can_add_second_plant_besides_tomato_001(self):
        repo = FakePlantRepository(auto_seed=True)
        plant2 = Plant(
            plant_id="plant_002",
            farm_id="farm_local",
            canonical_label="Test Plant 002",
            display_name="Test 002",
            state=PlantStatus.ACTIVE,
            created_by_actor_ref="acct_boss",
            created_at=NOW,
        )
        await repo.add_plant(plant2)
        assert await repo.get_plant_count() == 2
        assert await repo.get_plant("plant_002") is plant2
        assert await repo.get_plant("tomato_001") is not None
