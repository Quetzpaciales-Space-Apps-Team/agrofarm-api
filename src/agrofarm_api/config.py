"""Application settings read from environment variables and validated at startup."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    cors_origins: list[str] = []
    log_level: str = "INFO"
    environment: str = "local"

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("wildcard CORS origin is not allowed with credentials")
        return value
