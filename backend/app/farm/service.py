from __future__ import annotations

from backend.app.access import Farm
from backend.app.access.db_repository import DbAccessRepository


async def get_single_farm(repo: DbAccessRepository) -> Farm | None:
    return await repo.get_single_farm()


async def require_single_farm(repo: DbAccessRepository) -> Farm:
    farm = await repo.get_single_farm()
    if farm is None:
        from backend.app.api.errors import AppError, ErrorCode

        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="No local Farm workspace found.",
            next_actions=["initialize_farm"],
        )
    return farm
