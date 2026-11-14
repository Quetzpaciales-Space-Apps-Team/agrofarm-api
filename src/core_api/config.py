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

    jwt_secret: SecretStr = SecretStr("local-dev-jwt-secret-change-in-production")
    jwt_issuer: str = "agrofarm-core-api"
    jwt_audience: str = "agrofarm-clients"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 604800

    ml_mode: str = "fixture"
    ml_service_url: str = "http://localhost:8081"
    ml_timeout_seconds: float = 5.0
    demo_mode: bool = False

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS needs an explicit allowlist. '*' is not allowed.")
        return origins
