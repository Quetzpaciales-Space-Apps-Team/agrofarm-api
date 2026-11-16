"""Service for ENSO climate series, scenario simulation, and rotation recommendations."""

import uuid
from datetime import date
from typing import Any

from core_api.clients.demo import load_demo_enso_snapshot, load_demo_nasa_power_snapshot
from core_api.clients.ml import MLClient
from core_api.domain.auth import CurrentUser
from core_api.domain.farms import default_priorities
from core_api.domain.problem import ProblemError
from core_api.domain.recommendations import (
    DISCLAIMER_TEXT,
    RecommendationRequestInput,
    SimulationRequestInput,
    compute_input_hash,
    map_and_validate_recommendations,
    validate_simulation_response,
)
from core_api.repositories.farms import FarmRepository
from core_api.repositories.recommendations import RecommendationRepository


class SimulationAndRecommendationService:
    def __init__(
        self,
        farm_repo: FarmRepository,
        rec_repo: RecommendationRepository,
        ml_client: MLClient,
        *,
        demo_mode: bool = False,
    ) -> None:
        self._farm_repo = farm_repo
        self._rec_repo = rec_repo
        self._ml_client = ml_client
        self._demo_mode = demo_mode

    def _require_farm(self, user: CurrentUser, farm_id: uuid.UUID) -> Any:
        farm = self._farm_repo.get(farm_id)
        if not farm or (farm.owner_id != user.id and user.role != "admin"):
            raise ProblemError(404, "not_found", "Farm not found")
        return farm

    def get_enso_series(self, start: date | None = None, end: date | None = None) -> dict[str, Any]:
        start_ym = start.strftime("%Y-%m") if start else None
        end_ym = end.strftime("%Y-%m") if end else None
        # One stored copy of the NOAA CPC tables serves every mode. It never invents months.
        snapshot = load_demo_enso_snapshot()
        raw_items: list[dict[str, Any]] = snapshot["items"]
        threshold_c = snapshot["threshold_c"]
        source = snapshot["source"]

        items = [
            item
            for item in raw_items
            if (start_ym is None or str(item["month"]) >= start_ym)
            and (end_ym is None or str(item["month"]) <= end_ym)
        ]
        return {
            "threshold_c": threshold_c,
            "items": items,
            "source": source,
            "disclaimer": DISCLAIMER_TEXT,
        }

    def get_nasa_power_series(
        self, start: str | None = None, end: str | None = None
    ) -> dict[str, Any]:
        """Monthly NASA POWER series, months `start` to `end` inclusive (`YYYY-MM`).

        The data is a static snapshot served in every mode. Values are never altered: a missing
        value stays `None`.
        """
        if start is not None and end is not None and start > end:
            raise ProblemError(
                422,
                "validation_error",
                "Request validation failed",
                "start must not be after end",
            )
        series = load_demo_nasa_power_snapshot()
        series["items"] = [
            item
            for item in series["items"]
            if (start is None or str(item["month"]) >= start)
            and (end is None or str(item["month"]) <= end)
        ]
        return series

    def simulate(self, user: CurrentUser, payload: SimulationRequestInput) -> dict[str, Any]:
        farm = self._require_farm(user, payload.farm_id)
        ml_payload = {
            "farm_id": str(farm.id),
            "centroid_lat": farm.centroid_lat,
            "centroid_lon": farm.centroid_lon,
            "crop": payload.crop,
            "scenario": payload.scenario.model_dump(),
        }
        raw = self._ml_client.simulate(ml_payload)
        return validate_simulation_response(raw, input_hash=compute_input_hash(ml_payload))

    def create_recommendations(
        self,
        user: CurrentUser,
        farm_id: uuid.UUID,
        payload: RecommendationRequestInput,
    ) -> dict[str, Any]:
        farm = self._require_farm(user, farm_id)
        priorities = self._farm_repo.get_priorities(farm_id) or default_priorities()
        ml_payload = {
            "farm_id": str(farm.id),
            "centroid_lat": farm.centroid_lat,
            "centroid_lon": farm.centroid_lon,
            "current_rotation": farm.current_rotation or ["maize", "fallow"],
            "priorities": priorities,
            "scenario": payload.scenario.model_dump(),
        }
        raw = self._ml_client.score_rotations(ml_payload)
        rec_id = uuid.uuid4()
        input_hash = compute_input_hash(ml_payload)
        mapped = map_and_validate_recommendations(
            rec_id=rec_id, farm_id=farm.id, raw=raw, input_hash=input_hash
        )
        prov = mapped["provenance"]
        self._rec_repo.save(
            rec_id=rec_id,
            farm_id=farm.id,
            model_version=str(prov["model_version"]),
            data_versions=dict(prov["data_versions"]),
            input_hash=input_hash,
            payload=mapped,
        )
        return mapped
