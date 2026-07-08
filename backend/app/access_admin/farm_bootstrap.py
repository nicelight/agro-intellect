from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import uuid

from sqlalchemy.orm import Session

from .farm_repository import FarmRepository
from .models import Farm, Plant


CANONICAL_FARM_KEY = "local_farm"
CANONICAL_FARM_DISPLAY_NAME = "Local Farm"
CANONICAL_PLANT_KEY = "tomato_001"
CANONICAL_PLANT_DISPLAY_NAME = "Tomato 001"
BOOTSTRAP_REQUEST_ID = "bootstrap-farm-local"


class CanonicalFarmBootstrapError(RuntimeError):
    """Safe actionable bootstrap failure suitable for CLI output."""


@dataclass(frozen=True, slots=True)
class CanonicalFarmBootstrapResult:
    farm_id: uuid.UUID
    plant_id: uuid.UUID
    farm_created: bool
    plant_created: bool


RepositoryFactory = Callable[[Session], FarmRepository]


def bootstrap_canonical_farm(
    session: Session,
    *,
    repository_factory: RepositoryFactory = FarmRepository,
) -> CanonicalFarmBootstrapResult:
    """Create missing canonical authority in one transaction, or change nothing."""

    try:
        with session.begin():
            repository = repository_factory(session)
            farms = repository.lock_farms()
            membership_farm_ids = repository.membership_farm_ids()

            if len(farms) > 1:
                raise CanonicalFarmBootstrapError(
                    "Canonical Farm bootstrap found multiple Farm records; "
                    "repair them manually before retrying."
                )

            farm_created = False
            if farms:
                farm = farms[0]
                if farm.farm_key != CANONICAL_FARM_KEY:
                    raise CanonicalFarmBootstrapError(
                        "Canonical Farm bootstrap found a conflicting Farm key; "
                        "repair it manually before retrying."
                    )
                if membership_farm_ids - {farm.farm_id}:
                    raise CanonicalFarmBootstrapError(
                        "Canonical Farm bootstrap found inconsistent membership "
                        "Farm references; repair them manually before retrying."
                    )
            else:
                if membership_farm_ids:
                    raise CanonicalFarmBootstrapError(
                        "Canonical Farm bootstrap found membership Farm references "
                        "without a matching Farm; repair them manually before retrying."
                    )
                farm = Farm(
                    farm_key=CANONICAL_FARM_KEY,
                    display_name=CANONICAL_FARM_DISPLAY_NAME,
                )
                repository.add_farm(farm)
                repository.flush()
                farm_created = True
                repository.add_system_audit(
                    farm_id=farm.farm_id,
                    action_type="farm_created",
                    target_type="farm",
                    target_id=farm.farm_id,
                    plant_id=None,
                    request_id=BOOTSTRAP_REQUEST_ID,
                    after_summary={
                        "farm_id": str(farm.farm_id),
                        "farm_key": farm.farm_key,
                        "display_name": farm.display_name,
                    },
                )

            plant = repository.lock_canonical_plant()
            plant_created = False
            if plant is not None:
                if plant.farm_id != farm.farm_id:
                    raise CanonicalFarmBootstrapError(
                        "Canonical Farm bootstrap found a conflicting tomato_001 "
                        "identity; repair it manually before retrying."
                    )
            else:
                plant = Plant(
                    farm_id=farm.farm_id,
                    plant_key=CANONICAL_PLANT_KEY,
                    display_name=CANONICAL_PLANT_DISPLAY_NAME,
                    status="active",
                )
                repository.add_plant(plant)
                repository.flush()
                plant_created = True
                repository.add_system_audit(
                    farm_id=farm.farm_id,
                    action_type="plant_created",
                    target_type="plant",
                    target_id=plant.plant_id,
                    plant_id=plant.plant_id,
                    request_id=BOOTSTRAP_REQUEST_ID,
                    after_summary={
                        "farm_id": str(farm.farm_id),
                        "plant_id": str(plant.plant_id),
                        "plant_key": plant.plant_key,
                        "display_name": plant.display_name,
                        "status": plant.status,
                    },
                )

            repository.flush()
            return CanonicalFarmBootstrapResult(
                farm_id=farm.farm_id,
                plant_id=plant.plant_id,
                farm_created=farm_created,
                plant_created=plant_created,
            )
    except CanonicalFarmBootstrapError:
        raise
    except Exception:
        raise CanonicalFarmBootstrapError(
            "Canonical Farm bootstrap failed without committed changes. "
            "Check the local migration state and database service."
        ) from None


__all__ = [
    "BOOTSTRAP_REQUEST_ID",
    "CANONICAL_FARM_DISPLAY_NAME",
    "CANONICAL_FARM_KEY",
    "CANONICAL_PLANT_DISPLAY_NAME",
    "CANONICAL_PLANT_KEY",
    "CanonicalFarmBootstrapError",
    "CanonicalFarmBootstrapResult",
    "bootstrap_canonical_farm",
]
