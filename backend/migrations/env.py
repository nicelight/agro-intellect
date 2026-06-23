from __future__ import annotations

from pathlib import Path

from alembic import context
from alembic.config import Config
from sqlalchemy import engine_from_config, pool

from backend.app.config import AppSettings
from backend.app.database import DatabaseHandle, build_database

MIGRATIONS_DIR = Path(__file__).resolve().parent
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
target_metadata = None


def build_alembic_config(settings: AppSettings | None = None) -> Config:
    resolved_settings = settings or AppSettings.from_env()
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("path_separator", "os")
    config.set_main_option("version_locations", str(VERSIONS_DIR))
    config.set_main_option("sqlalchemy.url", resolved_settings.database_url)
    config.set_main_option(
        "sqlalchemy.echo",
        str(resolved_settings.database_echo).lower(),
    )
    return config


def build_migration_database(settings: AppSettings | None = None) -> DatabaseHandle:
    return build_database(settings or AppSettings.from_env())


def run_migrations_offline() -> None:
    url = context.config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = context.config.get_section(context.config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = context.config.get_main_option("sqlalchemy.url")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if hasattr(context, "config"):
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


__all__ = [
    "MIGRATIONS_DIR",
    "VERSIONS_DIR",
    "build_alembic_config",
    "build_migration_database",
    "run_migrations_offline",
    "run_migrations_online",
]
