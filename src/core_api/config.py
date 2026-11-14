"""Settings come from the environment and are validated at startup."""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Contains the database password, so it is a secret and has no default:
    # the app refuses to start without it.
    database_url: SecretStr
    environment: str = "local"
    cors_allowed_origins: list[str] = []
    log_level: str = "INFO"

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS needs an explicit allowlist. '*' is not allowed.")
        return origins
