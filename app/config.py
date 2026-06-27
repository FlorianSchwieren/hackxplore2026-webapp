from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_prefix: str = "/api/v1"
    environment: str = "development"
    dev_auth_disabled: bool = False

    supabase_url: str | None = None
    supabase_anon_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY"),
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"),
    )
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None
    database_url: str | None = None

    ingest_shared_secret: str = "change-me"

    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    karlsruhe_lat: float = 49.0069
    karlsruhe_lon: float = 8.4037

    outlier_raw_margin: int = 250
    smoothing_window: int = 5
    state_debounce_readings: int = 2
    ingest_dedupe_window_seconds: int = 5
    thriving_streak_threshold: int = 7
    rain_penalty_skip_precip_mm_24h: float = 5.0
    uncovered_absence_protects_streak: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
