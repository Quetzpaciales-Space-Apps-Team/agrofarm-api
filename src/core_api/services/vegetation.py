"""Farm ownership and provenance for the regional vegetation outlook."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from core_api.clients.vegetation import validate_outlook
from core_api.domain.auth import CurrentUser
from core_api.domain.recommendations import DISCLAIMER_TEXT, ScenarioInput
from core_api.services.farms import FarmService


class VegetationClient(Protocol):
    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class VegetationService:
    def __init__(self, farms: FarmService, client: VegetationClient):
        self.farms = farms
        self.client = client

    def simulate(
        self, user: CurrentUser, farm_id: uuid.UUID, scenario: ScenarioInput
    ) -> dict[str, Any]:
        farm = self.farms.get_farm(user, farm_id)
        payload = {
            "farm_id": str(farm_id),
            "centroid_lat": farm.centroid_lat,
            "centroid_lon": farm.centroid_lon,
            "scenario": scenario.model_dump(),
        }
        result = validate_outlook(self.client.simulate(payload))
        result["disclaimer"] = DISCLAIMER_TEXT
        result["provenance"] = {
            **result["provenance"],
            "model_name": "regional-vegetation-outlook",
            "generated_at": datetime.now(UTC).isoformat(),
            "input_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        }
        return result
