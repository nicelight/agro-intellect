"""Farm API routes — single local workspace read.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header

from backend.app.access import InMemoryAccessRepository
from backend.app.api.errors import AppError, ErrorCode
from backend.app.api.schemas.farm import FarmResponse
from backend.app.context import ActorContext
from backend.app.context.resolver import require_actor_context
from backend.app.farm import require_single_farm

router = APIRouter(prefix="/api/v1/farm")

_TEST_REPO: InMemoryAccessRepository | None = None


def _get_repo() -> InMemoryAccessRepository:
    if _TEST_REPO is not None:
        return _TEST_REPO
    from backend.app.access.repository import InMemoryAccessRepository

    return InMemoryAccessRepository()


def _resolve_session(
    authorization: str = Header(None, alias="Authorization"),
) -> ActorContext:
    repo = _get_repo()
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    return require_actor_context(repo, session_secret, request_ref=f"req_{uuid4().hex}")


@router.get("", response_model=FarmResponse)
def read_farm(ctx: ActorContext = Depends(_resolve_session)):
    repo = _get_repo()
    farm = require_single_farm(repo)
    return FarmResponse(
        farm_id=farm.farm_id,
        display_name=farm.display_name,
        status=farm.status.value,
        sync_status=farm.sync_status.value,
        created_at=farm.created_at.isoformat() if farm.created_at else None,
        updated_at=farm.updated_at.isoformat() if farm.updated_at else None,
    )
