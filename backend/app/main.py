from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import Final

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .access_admin.dependencies import install_protected_route_error_handler
from .access_admin.errors import install_error_handlers
from .api import (
    admin_router,
    feed_router,
    history_router,
    operations_router,
    photos_router,
    plant_state_router,
    plants_router,
    session_router,
)
from .config import AppSettings
from .database import DatabaseHandle, build_database
from .agent_chat import PostgreSQLAgentIntroductionSink, reconcile_active_plants
from .agent_runtime.bootstrap import (
    AgentIntroductionSink,
)


_logger = logging.getLogger(__name__)


def create_app(
    settings: AppSettings | None = None,
    database: DatabaseHandle | None = None,
    readiness_check_database: bool = False,
    agent_introduction_sink: AgentIntroductionSink | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_database = database or build_database(resolved_settings)
    resolved_sink = agent_introduction_sink or PostgreSQLAgentIntroductionSink(
        resolved_database
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            reconcile_active_plants(resolved_database, resolved_sink)
        except Exception:
            _logger.warning("AGENT_INTRODUCTION_RECONCILIATION_FAILED")
        yield

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.database = resolved_database
    app.state.readiness_check_database = readiness_check_database
    app.state.agent_introduction_sink = resolved_sink
    install_error_handlers(app)
    install_protected_route_error_handler(app)
    app.include_router(session_router)
    app.include_router(admin_router)
    app.include_router(plants_router)
    app.include_router(operations_router)
    app.include_router(photos_router)
    app.include_router(history_router)
    app.include_router(feed_router)
    app.include_router(plant_state_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        if app.state.readiness_check_database:
            try:
                resolved_database.ping()
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "checks": {"database": "failed"}},
                )
            return {"status": "ready", "checks": {"database": "ok"}}
        return {"status": "ready"}

    return app


app: Final[FastAPI] = create_app()
