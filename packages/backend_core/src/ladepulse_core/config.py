from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://ladepulse:ladepulse@db:5432/ladepulse"
    database_url_sync: str = "postgresql+psycopg://ladepulse:ladepulse@db:5432/ladepulse"
    redis_url: str = "redis://redis:6379/0"
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "ladepulse-local"
    s3_secret_key: str = "ladepulse-local-secret"
    s3_bucket: str = "raw-payloads"
    s3_region: str = "eu-central-1"
    raw_payload_retention_enabled: bool = True
    demo_seed: int = 20260729
    demo_reference_time: datetime = datetime(2026, 7, 29, 12, tzinfo=UTC)
    api_base_url: str = "http://localhost:8000"
    map_style_url: str = "https://demotiles.maplibre.org/style.json"
    bnetza_csv_url: str = (
        "https://data.bundesnetzagentur.de/Bundesnetzagentur/DE/Fachthemen/"
        "ElektrizitaetundGas/E-Mobilitaet/"
        "Ladesaeulenregister_BNetzA_2026-07-28.csv"
    )
    mobilithek_publication_url: str | None = None
    mobilithek_client_certificate_path: str | None = None
    mobilithek_client_key_path: str | None = None
    log_level: str = "INFO"

    @field_validator("demo_reference_time")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("DEMO_REFERENCE_TIME must include a timezone")
        return value.astimezone(UTC)

    @property
    def psycopg_dsn(self) -> str:
        return self.database_url_sync.replace("postgresql+psycopg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
