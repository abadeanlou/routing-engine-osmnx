# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables (.env file)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "Routing Engine API"
    APP_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"

    # Preloaded (public/demo) mode: build ONE fixed-area graph at startup,
    # cache it to disk, and refuse requests outside it. Leave PRELOAD_GRAPH
    # false for local dynamic mode (graph rebuilt per OD area on demand).
    PRELOAD_GRAPH: bool = False
    PRELOAD_LAT: float = 45.4642   # Milan Duomo
    PRELOAD_LON: float = 9.1900
    PRELOAD_RADIUS_M: float = 7_000.0
    GRAPH_CACHE_DIR: str = "cache"


settings = Settings()
