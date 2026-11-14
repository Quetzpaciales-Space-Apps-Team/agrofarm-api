"""Service for ENSO climate series, scenario simulation, and rotation recommendations."""

import uuid
from datetime import date
from typing import Any

from core_api.clients.demo import load_demo_enso_snapshot
from core_api.clients.ml import MLClient
from core_api.domain.auth import CurrentUser
from core_api.domain.farms import default_priorities
from core_api.domain.problem import ProblemError
from core_api.domain.recommendations import (
    RecommendationRequestInput,
    SimulationRequestInput,
    compute_input_hash,
    map_and_validate_recommendations,
    validate_simulation_response,
)
from core_api.repositories.farms import FarmRepository
from core_api.repositories.recommendations import RecommendationRepository

_ENSO_ITEMS: list[dict[str, Any]] = [
    {"month": "2023-07", "oni": 1.1, "roni": 0.9, "phase": "el_nino"},
    {"month": "2023-10", "oni": 1.8, "roni": 1.4, "phase": "el_nino"},
    {"month": "2023-12", "oni": 2.0, "roni": 1.5, "phase": "el_nino"},
    {"month": "2024-03", "oni": 1.1, "roni": 0.8, "phase": "el_nino"},
    {"month": "2024-06", "oni": 0.2, "roni": -0.3, "phase": "neutral"},
    {"month": "2024-09", "oni": -0.2, "roni": -0.4, "phase": "neutral"},
    {"month": "2025-01", "oni": -0.6, "roni": -1.1, "phase": "la_nina"},
    {"month": "2025-04", "oni": -0.3, "roni": -0.5, "phase": "la_nina"},
    {"month": "2025-10", "oni": 0.1, "roni": 0.0, "phase": "neutral"},
    {"month": "2026-06", "oni": 0.4, "roni": 0.3, "phase": "neutral"},
    {"month": "2026-10", "oni": 0.6, "roni": 0.5, "phase": "el_nino"},
]


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
        if self._demo_mode:
            snapshot = load_demo_enso_snapshot()
            raw_items: list[dict[str, Any]] = snapshot["items"]
            threshold_c = snapshot["threshold_c"]
            source = snapshot["source"]
        else:
            raw_items = _ENSO_ITEMS
            threshold_c = 0.5
            source = "NOAA CPC"

        items = [
            item
            for item in raw_items
            if (start_ym is None or str(item["month"]) >= start_ym)
            and (end_ym is None or str(item["month"]) <= end_ym)
        ]
        return {"threshold_c": threshold_c, "items": items, "source": source}

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
        return validate_simulation_response(raw)

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
        mapped = map_and_validate_recommendations(rec_id=rec_id, farm_id=farm.id, raw=raw)
        prov = mapped["provenance"]
        self._rec_repo.save(
            rec_id=rec_id,
            farm_id=farm.id,
            model_version=str(prov["model_version"]),
            data_versions=dict(prov["data_versions"]),
            input_hash=compute_input_hash(ml_payload),
            payload=mapped,
        )
        return mapped
