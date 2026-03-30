"""
Configuration centralisée via variables d'environnement.
Charge automatiquement le fichier .env grâce à pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────
    app_env: str = "development"
    secret_key: str = "change_me_in_prod"
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────────────
    database_url: str = "sqlite:///./devlife.db"

    # ── AWS ───────────────────────────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "eu-west-3"
    s3_bucket_raw: str = "devlife-hub-raw"
    s3_bucket_models: str = "devlife-hub-models"

    # ── MLflow ────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://localhost:5000"

    # ── Météo ─────────────────────────────────────────────
    openweather_api_key: str = ""
    location_lat: float = 46.1453  # Saint-Julien-en-Genevois
    location_lon: float = 6.0806
    location_name: str = "Saint-Julien-en-Genevois"

    # ── Telegram ──────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── Claude API ────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── Samsung Health ────────────────────────────────────
    samsung_health_export_dir: Path = Path("data/exports/samsung_health")

    # ── Prefect ───────────────────────────────────────────
    prefect_api_url: str = "http://localhost:4200/api"

    # France Travail (emploi) API
    france_travail_client_id: str = ""
    france_travail_client_secret: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Singleton — retourne toujours la même instance."""
    return Settings()


# Alias pratique pour les imports
settings = get_settings()
