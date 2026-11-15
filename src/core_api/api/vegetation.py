"""Farm-scoped regional greenness simulation, separate from the yield stub."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from core_api.api.deps import get_current_user, get_vegetation_service
from core_api.domain.auth import CurrentUser
from core_api.domain.recommendations import ScenarioInput
from core_api.services.vegetation import VegetationService

router = APIRouter(prefix="/v1/farms", tags=["farms"])


@router.post(
    "/{farm_id}/vegetation/simulate",
    description=(
        "Conditional regional NDVI outlook, not parcel yield or an ENSO forecast. "
        "The original 5% improvement goal was not reached. Returns 503 when trained inference "
        "is unavailable; no cached or fixed-rule fallback."
    ),
)
def simulate_vegetation(
    farm_id: uuid.UUID,
    scenario: ScenarioInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[VegetationService, Depends(get_vegetation_service)],
) -> dict[str, Any]:
    return service.simulate(user, farm_id, scenario)
