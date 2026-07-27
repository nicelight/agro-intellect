from os import environ as os_environ
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field

from .core.redaction import redact_url_credentials


class AppSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = Field(default="agro-intellect")
    environment: str = Field(default="local")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost/agro_intellect"
    )
    database_echo: bool = Field(default=False)
    database_pool_pre_ping: bool = Field(default=True)
    local_data_root: Path = Field(default=Path("data"))
    local_artifact_root: Path = Field(default=Path("data/artifacts"))
    local_timeline_root: Path = Field(default=Path("data/timeline"))
    local_temp_root: Path = Field(default=Path("data/tmp"))
    local_smoke_root: Path = Field(default=Path("data/smoke"))
    sync_status: str = Field(default="local_only")

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
            local_data_root=source.get("LOCAL_DATA_ROOT", "data"),
            local_artifact_root=source.get("LOCAL_ARTIFACT_ROOT", "data/artifacts"),
            local_timeline_root=source.get("LOCAL_TIMELINE_ROOT", "data/timeline"),
            local_temp_root=source.get("LOCAL_TEMP_ROOT", "data/tmp"),
            local_smoke_root=source.get("LOCAL_SMOKE_ROOT", "data/smoke"),
            sync_status=source.get("SYNC_STATUS", "local_only"),
        )

    def redacted_for_log(self) -> dict[str, str]:
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "database_url": redact_url_credentials(self.database_url),
            "database_echo": str(self.database_echo).lower(),
            "database_pool_pre_ping": str(self.database_pool_pre_ping).lower(),
            "local_data_root": str(self.local_data_root),
            "local_artifact_root": str(self.local_artifact_root),
            "local_timeline_root": str(self.local_timeline_root),
            "local_temp_root": str(self.local_temp_root),
            "local_smoke_root": str(self.local_smoke_root),
            "sync_status": self.sync_status,
        }
