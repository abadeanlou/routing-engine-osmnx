# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables (.env file).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "Routing Engine API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # Place string for OSMnx, e.g. "Milan, Italy"
    OSM_PLACE: str = "Milan, Italy"


settings = Settings()
