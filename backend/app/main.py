from __future__ import annotations

from typing import Final

from fastapi import FastAPI

from .config import AppSettings
from .database import DatabaseHandle, build_database


def create_app(
    settings: AppSettings | None = None,
    database: DatabaseHandle | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    resolved_database = database or build_database(resolved_settings)
    app = FastAPI(title=resolved_settings.app_name)
    app.state.settings = resolved_settings
    app.state.database = resolved_database

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    return app


app: Final[FastAPI] = create_app()
