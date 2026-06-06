"""Farm read service — single local Farm workspace.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from __future__ import annotations

from backend.app.access import Farm, InMemoryAccessRepository


def get_single_farm(repo: InMemoryAccessRepository) -> Farm | None:
    """Return the single active Farm or None."""
    return repo.get_single_farm()


def require_single_farm(repo: InMemoryAccessRepository) -> Farm:
    """Return the single active Farm or raise."""
    farm = repo.get_single_farm()
    if farm is None:
        from backend.app.api.errors import AppError, ErrorCode

        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="No local Farm workspace found.",
            next_actions=["initialize_farm"],
        )
    return farm
