"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All values are loaded from environment variables.
    Defaults are provided only for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["local", "development", "production"] = "local"
    app_name: str = "deadlock-ai-platform"
    app_version: str = "0.1.0"

    # API Server
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = (
        "postgresql+asyncpg://deadlock_ai:deadlock_ai_local@localhost:5433/deadlock_ai"
    )
    database_sync_url: str = (
        "postgresql+psycopg2://deadlock_ai:deadlock_ai_local@localhost:5433/deadlock_ai"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    auth_secret: str = "local-dev-secret-change-in-production"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Object Storage (R2)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "deadlock-ai-uploads"
    r2_public_url: str = ""

    # Replay parser spike
    replay_parser_command: str | None = None
    replay_parser_timeout_seconds: int = 60
    replay_parser_max_events: int = 500
    local_replay_sample_path: str | None = None
    allow_local_replay_paths: bool = False

    # AI Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    litellm_api_key: str = ""

    # Observability
    glitchtip_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


settings = get_settings()
