"""In-memory Plant repository with tomato_001 seed.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from __future__ import annotations

from datetime import datetime

from backend.app.plants.models import Plant, PlantAccessGrant, PlantAccessGrantStatus, PlantStatus


TOMATO_001_PLANT_ID = "tomato_001"
TOMATO_001_FARM_ID = "farm_local"


class InMemoryPlantRepository:
    def __init__(self, *, auto_seed: bool = True) -> None:
        self.plants: dict[str, Plant] = {}
        self.grants: dict[str, PlantAccessGrant] = {}
        if auto_seed:
            self._seed_tomato_001()

    def _seed_tomato_001(self) -> None:
        from backend.app.plants.models import utc_now

        plant = Plant(
            plant_id=TOMATO_001_PLANT_ID,
            farm_id=TOMATO_001_FARM_ID,
            canonical_label="Tomato 001",
            display_name="Tomato 001",
            state=PlantStatus.ACTIVE,
            created_by_actor_ref="system_seed",
            created_at=utc_now(),
        )
        self.plants[TOMATO_001_PLANT_ID] = plant

    def add_plant(self, plant: Plant) -> Plant:
        self.plants[plant.plant_id] = plant
        return plant

    def get_plant(self, plant_id: str) -> Plant | None:
        return self.plants.get(plant_id)

    def get_plants_by_farm(self, farm_id: str) -> list[Plant]:
        return [p for p in self.plants.values() if p.farm_id == farm_id]

    def get_active_plants_by_farm(self, farm_id: str) -> list[Plant]:
        return [
            p
            for p in self.plants.values()
            if p.farm_id == farm_id and p.state is PlantStatus.ACTIVE
        ]

    def get_plant_count(self) -> int:
        return len(self.plants)

    def add_grant(self, grant: PlantAccessGrant) -> PlantAccessGrant:
        self.grants[grant.grant_id] = grant
        return grant

    def get_grant(self, grant_id: str) -> PlantAccessGrant | None:
        return self.grants.get(grant_id)

    def get_grants_for_plant(self, plant_id: str) -> list[PlantAccessGrant]:
        return [g for g in self.grants.values() if g.plant_id == plant_id]

    def get_grants_for_account(self, account_id: str) -> list[PlantAccessGrant]:
        return [g for g in self.grants.values() if g.account_id == account_id]
