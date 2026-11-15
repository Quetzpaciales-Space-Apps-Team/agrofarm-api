"""Regional vegetation requires ownership, ordered real-model output and failed-goal disclosure."""

import copy
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_vegetation_service
from core_api.clients.vegetation import HttpVegetationClient, validate_outlook
from core_api.config import Settings
from core_api.domain.auth import CurrentUser
from core_api.domain.farms import FarmCreateInput
from core_api.domain.problem import ProblemError
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.vegetation import VegetationService
from tests.unit.test_farms import VALID_POLYGON, InMemoryFarmRepository, _auth_header

RESULT: dict[str, Any] = {
    "target": "seasonal_peak_ndvi_anomaly_pct",
    "unit": "%",
    "baseline": {"p10": -10, "p50": 0, "p90": 10},
    "scenario": {"p10": -12, "p50": -3, "p90": 8},
    "attributions": [{"feature": "rain_anom_pct", "contribution": -3}],
    "explained_median_delta": -3,
    "out_of_range_inputs": [],
    "reference_cell": {"cell_id": "test", "distance_km": 1, "resolution_degrees": 0.05},
    "validation": {"acceptance_rule_met": False, "skill_improvement_pct": 4.41},
    "limitations": ["Not parcel yield"],
    "needs_local_review": True,
    "provenance": {
        "model_version": "ndvi-vegetation-outlook-0.1.0",
        "evaluation_verdict": "no_skill_over_climatology",
    },
}


class Client:
    calls = 0

    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        assert "centroid_lat" in payload
        assert "scenario" in payload
        return copy.deepcopy(RESULT)


def test_farm_scope_and_authenticated_real_outlook(settings: Settings) -> None:
    farms = FarmService(InMemoryFarmRepository())
    owner = CurrentUser(uuid.uuid4(), "farmer")
    farm = farms.create_farm(owner, FarmCreateInput(name="Test", boundary=VALID_POLYGON))
    ml = Client()
    app = create_app(settings)
    app.dependency_overrides[get_vegetation_service] = lambda: VegetationService(farms, ml)
    client = TestClient(app)
    path = f"/v1/farms/{farm.id}/vegetation/simulate"
    assert client.post(path, json={}).status_code == 401
    assert (
        client.post(path, json={}, headers=_auth_header(uuid.uuid4(), settings)).status_code == 404
    )
    assert ml.calls == 0
    headers = _auth_header(owner.id, settings)
    response = client.post(path, json={"rainfall_change_pct": -30}, headers=headers)
    assert response.status_code == 200
    assert response.json()["validation"]["acceptance_rule_met"] is False
    assert response.json()["provenance"]["input_hash"]
    assert response.json()["disclaimer"]
    assert client.post(path, json={"rainfall_change_pct": 101}, headers=headers).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"target": "yield"},
        {"scenario": {"p10": 4, "p50": 3, "p90": 2}},
        {"validation": {"acceptance_rule_met": True}},
        {"limitations": []},
        {"needs_local_review": False},
        {"attributions": [{"contribution": float("nan")}]},
    ],
)
def test_rejects_false_confidence_and_invalid_quantiles(change: dict[str, Any]) -> None:
    with pytest.raises(ProblemError):
        validate_outlook({**copy.deepcopy(RESULT), **change})


def test_service_identity_and_no_fallback() -> None:
    with patch("core_api.clients.ml.HttpMLClient._post_json", return_value=RESULT) as post:
        client = HttpVegetationClient(
            "https://ml.example.test", token_provider=lambda: "service-token"
        )
        assert client.simulate({}) == RESULT
        post.assert_called_once_with("/v1/vegetation/simulate", {})
    with (
        patch(
            "core_api.clients.ml.HttpMLClient._post_json",
            side_effect=ProblemError(503, "unavailable", "Unavailable"),
        ),
        pytest.raises(ProblemError),
    ):
        client.simulate({})
