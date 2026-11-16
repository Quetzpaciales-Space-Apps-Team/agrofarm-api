"""ENSO and NASA POWER climate series, scenario simulation, and recommendation endpoints."""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query

from core_api.api.deps import get_current_user, get_simulation_service
from core_api.domain.auth import CurrentUser
from core_api.domain.recommendations import RecommendationRequestInput, SimulationRequestInput
from core_api.services.recommendations import SimulationAndRecommendationService

router = APIRouter(prefix="/v1", tags=["simulation"])


@router.get("/climate/enso", tags=["data"])
def get_enso(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[SimulationAndRecommendationService, Depends(get_simulation_service)],
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> dict[str, Any]:
    return service.get_enso_series(start=start, end=end)


_MONTH_PATTERN = r"^[0-9]{4}-(0[1-9]|1[0-2])$"


@router.get("/climate/nasa-power", tags=["data"])
def get_nasa_power(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[SimulationAndRecommendationService, Depends(get_simulation_service)],
    start: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
    end: Annotated[str | None, Query(pattern=_MONTH_PATTERN)] = None,
) -> dict[str, Any]:
    return service.get_nasa_power_series(start=start, end=end)


@router.post("/scenarios/simulate")
def simulate_scenario(
    payload: SimulationRequestInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[SimulationAndRecommendationService, Depends(get_simulation_service)],
) -> dict[str, Any]:
    return service.simulate(user, payload)


@router.post("/farms/{farm_id}/recommendations", status_code=201, tags=["recommendations"])
def create_recommendations(
    farm_id: uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[SimulationAndRecommendationService, Depends(get_simulation_service)],
    payload: Annotated[RecommendationRequestInput | None, Body()] = None,
) -> dict[str, Any]:
    return service.create_recommendations(user, farm_id, payload or RecommendationRequestInput())
