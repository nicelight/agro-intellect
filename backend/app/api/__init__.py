from .admin import router as admin_router
from .history import router as history_router
from .feed import router as feed_router
from .operations import router as operations_router
from .photos import router as photos_router
from .plant_state import router as plant_state_router
from .plants import router as plants_router
from .session import router as session_router

__all__ = [
    "admin_router",
    "history_router",
    "feed_router",
    "operations_router",
    "photos_router",
    "plant_state_router",
    "plants_router",
    "session_router",
]
