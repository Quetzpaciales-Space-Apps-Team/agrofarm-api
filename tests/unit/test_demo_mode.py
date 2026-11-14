"""Unit and HTTP boundary tests for DEMO_MODE=true offline snapshot behavior."""

import uuid

from fastapi.testclient import TestClient

from core_api.api.deps import (
    get_farm_service,
    get_ml_client,
    get_readiness_service,
    get_simulation_service,
)
from core_api.clients.demo import DemoMLClient
from core_api.config import Settings
from core_api.domain.auth import encode_access_token
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_farms import VALID_POLYGON, InMemoryFarmRepository
from tests.unit.test_simulation_and_recommendations import InMemoryRecommendationRepository


def test_get_ml_client_uses_demo_client_when_demo_mode_enabled() -> None:
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        ml_mode="http",
        demo_mode=True,
    )
    client = get_ml_client(settings)
    assert isinstance(client, DemoMLClient)


def test_demo_mode_endpoints_serve_cached_demo_snapshots() -> None:
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        demo_mode=True,
    )
    farm_repo = InMemoryFarmRepository()
    rec_repo = InMemoryRecommendationRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("db", True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo,
        rec_repo,
        DemoMLClient(),
        demo_mode=True,
    )

    user_id = uuid.uuid4()
    token = encode_access_token(
        user_id=user_id,
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        farm_res = client.post(
            "/v1/farms",
            json={
                "name": "Demo Farm",
                "boundary": VALID_POLYGON,
                "current_rotation": ["maize", "fallow"],
            },
            headers=headers,
        )
        assert farm_res.status_code == 201
        farm_id = farm_res.json()["id"]

        enso_res = client.get(
            "/v1/climate/enso?start=2024-01-01&end=2026-12-31",
            headers=headers,
        )
        assert enso_res.status_code == 200
        assert "cached_demo" in enso_res.json()["source"]
        assert all(item["month"] >= "2024-01" for item in enso_res.json()["items"])

        sim_res = client.post(
            "/v1/scenarios/simulate",
            json={
                "farm_id": farm_id,
                "crop": "beans",
                "scenario": {
                    "rainfall_change_pct": -15.0,
                    "temperature_change_c": 1.0,
                    "enso_phase": "el_nino",
                },
            },
            headers=headers,
        )
        assert sim_res.status_code == 200
        assert sim_res.json()["crop"] == "beans"
        assert sim_res.json()["provenance"]["data_versions"]["snapshot_mode"] == "cached_demo"

        rec_res = client.post(
            f"/v1/farms/{farm_id}/recommendations",
            json={
                "scenario": {
                    "rainfall_change_pct": -15.0,
                    "temperature_change_c": 1.0,
                    "enso_phase": "el_nino",
                },
            },
            headers=headers,
        )
        assert rec_res.status_code == 201
        body = rec_res.json()
        assert body["provenance"]["data_versions"]["snapshot_mode"] == "cached_demo"
        assert len(body["strategies"]) >= 3
        assert any(s["is_current"] for s in body["strategies"])
