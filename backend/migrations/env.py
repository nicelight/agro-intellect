from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from backend.app.config import AppSettings
from backend.app.database import DatabaseHandle, build_database

MIGRATIONS_DIR = Path(__file__).resolve().parent
VERSIONS_DIR = MIGRATIONS_DIR / "versions"


def build_alembic_config(settings: AppSettings | None = None) -> Config:
    resolved_settings = settings or AppSettings.from_env()
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("version_locations", str(VERSIONS_DIR))
    config.set_main_option("sqlalchemy.url", resolved_settings.database_url)
    config.set_main_option(
        "sqlalchemy.echo",
        str(resolved_settings.database_echo).lower(),
    )
    return config


def build_migration_database(settings: AppSettings | None = None) -> DatabaseHandle:
    return build_database(settings or AppSettings.from_env())


__all__ = [
    "MIGRATIONS_DIR",
    "VERSIONS_DIR",
    "build_alembic_config",
    "build_migration_database",
]
