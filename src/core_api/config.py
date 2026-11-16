"""Settings come from the environment and are validated at startup."""

import json
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_DEV_JWT_SECRET = "local-dev-jwt-secret-change-in-production"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Contains the database password, so it is a secret and has no default:
    # the app refuses to start without it.
    database_url: SecretStr
    environment: str = "local"
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )
    log_level: str = "INFO"

    jwt_secret: SecretStr = SecretStr(DEFAULT_DEV_JWT_SECRET)
    jwt_issuer: str = "agrofarm-core-api"
    jwt_audience: str = "agrofarm-clients"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 604800

    ml_mode: str = "fixture"
    ml_service_url: str = "http://localhost:8081"
    # "none" for local runs; "google_id_token" when ml-service is a private Cloud Run service.
    ml_auth: str = "none"
    ml_timeout_seconds: float = 5.0
    demo_mode: bool = False
    # "snapshot": demo mode serves the cached ML answers and never calls ml-service.
    # "live": with ML_MODE=http, demo mode calls ml-service and uses the cached answers only
    # when the call fails.
    demo_ml_source: Literal["snapshot", "live"] = "snapshot"
    demo_rate_limit_per_minute: int = 20
    demo_max_guests: int = 1000
    max_upload_bytes: int = 2 * 1024 * 1024
    raw_uploads_dir: str = "data/raw/uploads"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    raise ValueError("CORS origins JSON must be a list of strings.")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in stripped.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("CORS origins must be a list or comma-separated string.")

    @field_validator("ml_auth")
    @classmethod
    def _known_ml_auth(cls, value: str) -> str:
        if value not in ("none", "google_id_token"):
            raise ValueError("ml_auth must be 'none' or 'google_id_token'")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard_origin(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS needs an explicit allowlist. '*' is not allowed.")
        return origins

    @model_validator(mode="after")
    def _require_non_default_jwt_in_non_local(self) -> "Settings":
        if self.environment != "local":
            secret = self.jwt_secret.get_secret_value().strip()
            if not secret or secret == DEFAULT_DEV_JWT_SECRET:
                raise ValueError(
                    "JWT_SECRET must be explicitly set to a non-default value "
                    "when ENVIRONMENT != 'local'."
                )
        return self
