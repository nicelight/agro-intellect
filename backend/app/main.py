from __future__ import annotations

from typing import Final

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .access_admin.dependencies import install_protected_route_error_handler
from .access_admin.errors import install_error_handlers
from .api import (
    admin_router,
    companion_router,
    feed_router,
    history_router,
    operations_router,
    photos_router,
    plant_state_router,
    plants_router,
    session_router,
)
from .api.companion import FT013RawPathCanonicalityMiddleware
from .agent_runtime import ProviderExecutorBindings
from .api.task_follow_up import (
    FT012RawPathCanonicalityMiddleware,
    router as task_follow_up_router,
)
from .config import AppSettings
from .database import DatabaseHandle, build_database


def create_app(
    settings: AppSettings | None = None,
    database: DatabaseHandle | None = None,
    readiness_check_database: bool = False,
    provider_bindings: ProviderExecutorBindings | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_database = database or build_database(resolved_settings)

    app = FastAPI(title=resolved_settings.app_name)
    app.add_middleware(FT012RawPathCanonicalityMiddleware)
    app.add_middleware(FT013RawPathCanonicalityMiddleware)
    app.state.settings = resolved_settings
    app.state.database = resolved_database
    app.state.readiness_check_database = readiness_check_database
    app.state.provider_bindings = provider_bindings or ProviderExecutorBindings()
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
    app.include_router(task_follow_up_router)
    app.include_router(companion_router)

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
