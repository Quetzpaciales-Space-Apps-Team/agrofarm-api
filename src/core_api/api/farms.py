"""Farms and farmer priorities HTTP endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from core_api.api.deps import get_current_user, get_farm_service
from core_api.domain.auth import CurrentUser
from core_api.domain.farms import FarmCreateInput, FarmRecord, FarmUpdateInput, PrioritiesModel
from core_api.services.farms import FarmService

router = APIRouter(prefix="/v1/farms", tags=["farms"])


def _serialize_farm(farm: FarmRecord) -> dict[str, Any]:
    return {
        "id": str(farm.id),
        "name": farm.name,
        "boundary": farm.boundary,
        "area_ha": farm.area_ha,
        "current_rotation": farm.current_rotation,
        "created_at": farm.created_at.isoformat().replace("+00:00", "Z"),
    }


@router.get("")
def list_farms(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> dict[str, Any]:
    items, next_cursor = service.list_farms(user, limit=limit, cursor=cursor)
    return {"items": [_serialize_farm(f) for f in items], "next_cursor": next_cursor}


@router.post("", status_code=201)
def create_farm(
    payload: FarmCreateInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> dict[str, Any]:
    farm = service.create_farm(user, payload)
    return _serialize_farm(farm)


@router.get("/{farm_id}")
def get_farm(
    farm_id: uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> dict[str, Any]:
    return _serialize_farm(service.get_farm(user, farm_id))


@router.patch("/{farm_id}")
def update_farm(
    farm_id: uuid.UUID,
    payload: FarmUpdateInput,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> dict[str, Any]:
    return _serialize_farm(service.update_farm(user, farm_id, payload))


@router.delete("/{farm_id}", status_code=204)
def delete_farm(
    farm_id: uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> Response:
    service.delete_farm(user, farm_id)
    return Response(status_code=204)


@router.get("/{farm_id}/priorities")
def get_priorities(
    farm_id: uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> dict[str, Any]:
    return service.get_priorities(user, farm_id)


@router.put("/{farm_id}/priorities")
def put_priorities(
    farm_id: uuid.UUID,
    payload: PrioritiesModel,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[FarmService, Depends(get_farm_service)],
) -> dict[str, Any]:
    return service.put_priorities(user, farm_id, payload)
