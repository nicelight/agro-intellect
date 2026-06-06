"""Plant API routes — list Plants for the single Farm.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header

from backend.app.access import InMemoryAccessRepository
from backend.app.api.schemas.plants import PlantListResponse, PlantResponse
from backend.app.context import ActorContext
from backend.app.context.resolver import require_actor_context
from backend.app.plants import InMemoryPlantRepository

router = APIRouter(prefix="/api/v1/plants")

_ACCESS_REPO: InMemoryAccessRepository | None = None
_PLANT_REPO: InMemoryPlantRepository | None = None


def _get_access_repo() -> InMemoryAccessRepository:
    if _ACCESS_REPO is not None:
        return _ACCESS_REPO
    from backend.app.access.repository import InMemoryAccessRepository

    return InMemoryAccessRepository()


def _get_plant_repo() -> InMemoryPlantRepository:
    if _PLANT_REPO is not None:
        return _PLANT_REPO
    return InMemoryPlantRepository()


def _resolve_session(
    authorization: str = Header(None, alias="Authorization"),
) -> ActorContext:
    repo = _get_access_repo()
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    return require_actor_context(repo, session_secret, request_ref=f"req_{uuid4().hex}")


@router.get("", response_model=PlantListResponse)
def list_plants(ctx: ActorContext = Depends(_resolve_session)):
    if ctx.farm_id is None:
        from backend.app.api.errors import AppError, ErrorCode

        raise AppError(
            code=ErrorCode.PERMISSION_DENIED,
            message="No Farm scope available.",
            next_actions=["authenticate"],
        )

    plant_repo = _get_plant_repo()
    plants = plant_repo.get_active_plants_by_farm(ctx.farm_id)

    return PlantListResponse(
        plants=[
            PlantResponse(
                plant_id=p.plant_id,
                farm_id=p.farm_id,
                canonical_label=p.canonical_label,
                display_name=p.display_name,
                state=p.state.value,
                created_by_actor_ref=p.created_by_actor_ref,
                created_at=p.created_at.isoformat() if p.created_at else None,
                archived_at=p.archived_at.isoformat() if p.archived_at else None,
                archived_by_actor_ref=p.archived_by_actor_ref,
                archive_reason=p.archive_reason,
                restored_at=p.restored_at.isoformat() if p.restored_at else None,
                restored_by_actor_ref=p.restored_by_actor_ref,
            )
            for p in plants
        ],
        total=len(plants),
    )
