from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FLEETFUEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FleetFuel API"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool = False
    cors_origins: list[str] = []
    database_url: str | None = None
    jwt_secret: str | None = None
    attachment_directory: str = "private_uploads"
    max_attachment_bytes: int = 5_000_000
    unusual_spend_multiplier: Decimal = Decimal("2.5")
    mail_host: str | None = None
    mail_port: int = 587
    mail_username: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    password_reset_url: str | None = None

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, database_url: str | None) -> str | None:
        if database_url and database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url and database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    @property
    def docs_enabled(self) -> bool:
        return self.environment != "production" or self.enable_docs

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("FLEETFUEL_CORS_ORIGINS must not contain a wildcard")
        if self.environment == "production":
            if not self.database_url:
                raise ValueError("FLEETFUEL_DATABASE_URL is required in production")
            if (
                not self.jwt_secret
                or len(self.jwt_secret) < 32
                or self.jwt_secret.startswith("generate-a-random-value")
                or "change-me" in self.jwt_secret
            ):
                raise ValueError(
                    "FLEETFUEL_JWT_SECRET must be at least 32 characters in production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
