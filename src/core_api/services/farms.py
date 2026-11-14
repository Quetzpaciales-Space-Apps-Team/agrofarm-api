"""Farm and farmer priorities service with ownership checks."""

import uuid
from typing import Any

from core_api.domain.auth import CurrentUser
from core_api.domain.farms import (
    FarmCreateInput,
    FarmRecord,
    FarmUpdateInput,
    PrioritiesModel,
    default_priorities,
    validate_polygon,
)
from core_api.domain.problem import ProblemError
from core_api.repositories.farms import FarmRepository


class FarmService:
    def __init__(self, repo: FarmRepository) -> None:
        self._repo = repo

    def list_farms(
        self, user: CurrentUser, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[FarmRecord], str | None]:
        return self._repo.list_by_owner(user.id, limit, cursor)

    def create_farm(self, user: CurrentUser, payload: FarmCreateInput) -> FarmRecord:
        area_ha, centroid_lat, centroid_lon = validate_polygon(payload.boundary)
        return self._repo.create(
            owner_id=user.id,
            name=payload.name,
            boundary=payload.boundary.model_dump(),
            area_ha=area_ha,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            current_rotation=payload.current_rotation,
        )

    def get_farm(self, user: CurrentUser, farm_id: uuid.UUID) -> FarmRecord:
        farm = self._repo.get(farm_id)
        if not farm or (farm.owner_id != user.id and user.role != "admin"):
            raise ProblemError(404, "not_found", "Farm not found")
        return farm

    def update_farm(
        self, user: CurrentUser, farm_id: uuid.UUID, payload: FarmUpdateInput
    ) -> FarmRecord:
        self.get_farm(user, farm_id)
        area_ha: float | None = None
        centroid_lat: float | None = None
        centroid_lon: float | None = None
        boundary_dict: dict[str, Any] | None = None
        if payload.boundary is not None:
            area_ha, centroid_lat, centroid_lon = validate_polygon(payload.boundary)
            boundary_dict = payload.boundary.model_dump()

        updated = self._repo.update(
            farm_id,
            name=payload.name,
            boundary=boundary_dict,
            area_ha=area_ha,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            current_rotation=payload.current_rotation,
        )
        if not updated:
            raise ProblemError(404, "not_found", "Farm not found")
        return updated

    def delete_farm(self, user: CurrentUser, farm_id: uuid.UUID) -> None:
        self.get_farm(user, farm_id)
        self._repo.delete(farm_id)

    def get_priorities(self, user: CurrentUser, farm_id: uuid.UUID) -> dict[str, Any]:
        self.get_farm(user, farm_id)
        stored = self._repo.get_priorities(farm_id)
        return stored if stored is not None else default_priorities()

    def put_priorities(
        self, user: CurrentUser, farm_id: uuid.UUID, payload: PrioritiesModel
    ) -> dict[str, Any]:
        self.get_farm(user, farm_id)
        return self._repo.put_priorities(
            farm_id,
            weights=payload.weights.model_dump(),
            constraints=payload.constraints.model_dump(),
        )
