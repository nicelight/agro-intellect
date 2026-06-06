"""Farm workspace domain.

@docs .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
"""

from backend.app.farm.service import get_single_farm, require_single_farm

__all__ = [
    "get_single_farm",
    "require_single_farm",
]
