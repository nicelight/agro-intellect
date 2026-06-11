from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.access.db_repository import DbAccessRepository
from backend.app.api.deps import get_db
from backend.app.api.errors import AppError, ErrorCode
from backend.app.api.schemas.farm import FarmResponse
from backend.app.context.models import ActorContext
from backend.app.context.resolver import require_actor_context
from backend.app.farm import require_single_farm

router = APIRouter(prefix="/api/v1/farm")

_TEST_REPO = None


def _get_repo(session: AsyncSession) -> Any:
    if _TEST_REPO is not None:
        return _TEST_REPO
    return DbAccessRepository(session)


async def _resolve_session(
    authorization: str = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> ActorContext:
    repo = _get_repo(session)
    session_secret = None
    if authorization and authorization.startswith("Bearer "):
        session_secret = authorization[len("Bearer "):]
    return await require_actor_context(repo, session_secret, request_ref=f"req_{uuid4().hex}")


@router.get("", response_model=FarmResponse)
async def read_farm(
    ctx: ActorContext = Depends(_resolve_session),
    session: AsyncSession = Depends(get_db),
):
    repo = _get_repo(session)
    farm = await require_single_farm(repo)
    return FarmResponse(
        farm_id=farm.farm_id,
        display_name=farm.display_name,
        status=farm.status.value,
        sync_status=farm.sync_status.value,
        created_at=farm.created_at.isoformat() if farm.created_at else None,
        updated_at=farm.updated_at.isoformat() if farm.updated_at else None,
    )
