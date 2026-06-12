"""Application configuration loaded from environment variables.

All settings are validated at startup. Never hardcode secrets here.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings.

    Values come from environment variables (or a local .env file in dev).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Taiwan Alpha Radar"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    # --- Database ---
    database_url: str = (
        "postgresql+psycopg://radar:radar@localhost:5432/taiwan_alpha_radar"
    )

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # --- Scheduler ---
    enable_scheduler: bool = True
    # Daily run at 18:00 Asia/Taipei (after market close + settlement).
    daily_job_hour: int = 18
    daily_job_minute: int = 0
    scheduler_timezone: str = "Asia/Taipei"

    # --- AI ---
    # "openai" | "anthropic" | "mock"
    ai_provider: str = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # --- Seeding ---
    auto_seed_on_startup: bool = True
    seed_days_of_history: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (single source of truth)."""
    return Settings()


settings = get_settings()
