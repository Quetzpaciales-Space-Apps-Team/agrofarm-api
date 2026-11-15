"""Dependency injection wiring. Tests replace these providers."""

from pathlib import Path
from typing import Annotated

from fastapi import Header, Request

from core_api.clients.demo import DemoMLClient
from core_api.clients.ml import FixtureMLClient, GoogleIdTokenProvider, HttpMLClient, MLClient
from core_api.config import Settings
from core_api.domain.auth import CurrentUser, decode_access_token
from core_api.domain.problem import ProblemError
from core_api.repositories.auth import SqlAlchemyAuthRepository
from core_api.repositories.farms import SqlAlchemyFarmRepository
from core_api.repositories.recommendations import SqlAlchemyRecommendationRepository
from core_api.repositories.uploads import SqlAlchemyUploadRepository
from core_api.services.auth import AuthService
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from core_api.services.uploads import UploadService


def get_readiness_service(request: Request) -> ReadinessService:
    return ReadinessService(request.app.state.probes)


def get_auth_service(request: Request) -> AuthService:
    settings: Settings = request.app.state.settings
    return AuthService(
        SqlAlchemyAuthRepository(request.app.state.engine),
        jwt_secret=settings.jwt_secret.get_secret_value(),
        jwt_issuer=settings.jwt_issuer,
        jwt_audience=settings.jwt_audience,
        access_ttl_seconds=settings.access_token_ttl_seconds,
        refresh_ttl_seconds=settings.refresh_token_ttl_seconds,
    )


def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ProblemError(401, "unauthenticated", "Missing bearer token")
    token = authorization[7:].strip()
    if not token:
        raise ProblemError(401, "unauthenticated", "Missing bearer token")
    settings: Settings = request.app.state.settings
    return decode_access_token(
        token,
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


def get_farm_service(request: Request) -> FarmService:
    return FarmService(SqlAlchemyFarmRepository(request.app.state.engine))


def get_upload_service(request: Request) -> UploadService:
    settings: Settings = request.app.state.settings
    return UploadService(
        SqlAlchemyFarmRepository(request.app.state.engine),
        SqlAlchemyUploadRepository(request.app.state.engine),
        raw_dir=Path(settings.raw_uploads_dir),
    )


def get_ml_client(settings: Settings) -> MLClient:
    if settings.demo_mode:
        return DemoMLClient()
    if settings.ml_mode == "http":
        provider = (
            GoogleIdTokenProvider(settings.ml_service_url)
            if settings.ml_auth == "google_id_token"
            else None
        )
        return HttpMLClient(
            settings.ml_service_url,
            timeout_seconds=settings.ml_timeout_seconds,
            token_provider=provider,
        )
    return FixtureMLClient()


def get_simulation_service(request: Request) -> SimulationAndRecommendationService:
    settings: Settings = request.app.state.settings
    return SimulationAndRecommendationService(
        SqlAlchemyFarmRepository(request.app.state.engine),
        SqlAlchemyRecommendationRepository(request.app.state.engine),
        get_ml_client(settings),
        demo_mode=settings.demo_mode,
    )
