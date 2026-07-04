from __future__ import annotations

from typing import Final

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .access_admin.errors import install_error_handlers
from .api import session_router
from .config import AppSettings
from .database import DatabaseHandle, build_database


def create_app(
    settings: AppSettings | None = None,
    database: DatabaseHandle | None = None,
    readiness_check_database: bool = False,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_database = database or build_database(resolved_settings)
    app = FastAPI(title=resolved_settings.app_name)
    app.state.settings = resolved_settings
    app.state.database = resolved_database
    app.state.readiness_check_database = readiness_check_database
    install_error_handlers(app)
    app.include_router(session_router)

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
