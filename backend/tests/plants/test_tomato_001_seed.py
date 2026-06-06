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
    InMemoryAccessRepository,
    MembershipRole,
    MembershipStatus,
)
from backend.app.plants import (
    InMemoryPlantRepository,
    Plant,
    PlantStatus,
    TOMATO_001_FARM_ID,
    TOMATO_001_PLANT_ID,
)


NOW = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)


class TestTomato001Seed:
    def test_tomato_001_present_after_seed(self):
        repo = InMemoryPlantRepository(auto_seed=True)
        plant = repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.plant_id == "tomato_001"
        assert plant.canonical_label == "Tomato 001"
        assert plant.display_name == "Tomato 001"
        assert plant.state is PlantStatus.ACTIVE
        assert plant.farm_id == "farm_local"

    def test_tomato_001_absent_when_auto_seed_false(self):
        repo = InMemoryPlantRepository(auto_seed=False)
        assert repo.get_plant(TOMATO_001_PLANT_ID) is None

    def test_plant_count_includes_tomato_001(self):
        repo = InMemoryPlantRepository(auto_seed=True)
        assert repo.get_plant_count() == 1
        assert repo.get_active_plants_by_farm("farm_local")[0].plant_id == "tomato_001"

    def test_tomato_001_is_active(self):
        repo = InMemoryPlantRepository(auto_seed=True)
        plant = repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.is_active

    def test_tomato_001_created_by_system_seed(self):
        repo = InMemoryPlantRepository(auto_seed=True)
        plant = repo.get_plant(TOMATO_001_PLANT_ID)
        assert plant is not None
        assert plant.created_by_actor_ref == "system_seed"

    def test_tomato_001_in_migration_sql(self):
        migration_path = "backend/app/db/migrations/0003_plant_seed.sql"
        with open(migration_path) as f:
            content = f.read()
        assert "tomato_001" in content
        assert "INSERT INTO plants" in content
        assert "-- Seed tomato_001" in content

    def test_can_add_second_plant_besides_tomato_001(self):
        repo = InMemoryPlantRepository(auto_seed=True)
        plant2 = Plant(
            plant_id="plant_002",
            farm_id="farm_local",
            canonical_label="Test Plant 002",
            display_name="Test 002",
            state=PlantStatus.ACTIVE,
            created_by_actor_ref="acct_boss",
            created_at=NOW,
        )
        repo.add_plant(plant2)
        assert repo.get_plant_count() == 2
        assert repo.get_plant("plant_002") is plant2
        assert repo.get_plant("tomato_001") is not None
