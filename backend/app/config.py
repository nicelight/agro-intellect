from typing import Mapping
from os import environ as os_environ

from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = Field(default="agro-intellect")
    environment: str = Field(default="local")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost/agro_intellect"
    )
    database_echo: bool = Field(default=False)
    database_pool_pre_ping: bool = Field(default=True)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "AppSettings":
        source = os_environ if environ is None else environ
        return cls(
            app_name=source.get("APP_NAME", "agro-intellect"),
            environment=source.get("APP_ENV", "local"),
            database_url=source.get(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost/agro_intellect",
            ),
            database_echo=source.get("DATABASE_ECHO", "false"),
            database_pool_pre_ping=source.get("DATABASE_POOL_PRE_PING", "true"),
        )
