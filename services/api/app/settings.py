from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str | None = Field(default=None, alias="SUPABASE_JWT_SECRET")

    # API
    host: str = Field(default="0.0.0.0", alias="GAMEPULSE_API_HOST")
    port: int = Field(default=8000, alias="GAMEPULSE_API_PORT")
    log_level: str = Field(default="INFO", alias="GAMEPULSE_API_LOG_LEVEL")
    cors_origins: str = Field(default="*", alias="GAMEPULSE_API_CORS_ORIGINS")
    rate_limit_per_min: int = Field(default=600, alias="GAMEPULSE_API_RATE_LIMIT_PER_MIN")

    environment: str = Field(default="dev", alias="GAMEPULSE_ENV")
    analytics_refresh_interval_s: int = Field(
        default=600, alias="GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
