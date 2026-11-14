"""Dependency injection wiring. Tests replace these providers."""

from typing import Annotated

from fastapi import Header, Request

from core_api.config import Settings
from core_api.domain.auth import CurrentUser, decode_access_token
from core_api.domain.problem import ProblemError
from core_api.repositories.farms import SqlAlchemyFarmRepository
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService


def get_readiness_service(request: Request) -> ReadinessService:
    return ReadinessService(request.app.state.probes)


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
