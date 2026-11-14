"""Unit and HTTP boundary tests for ENSO, scenario simulation, ML client, and recommendations."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_farm_service, get_readiness_service, get_simulation_service
from core_api.clients.ml import FixtureMLClient, HttpMLClient
from core_api.config import Settings
from core_api.domain.auth import encode_access_token
from core_api.domain.recommendations import RecommendationRecord
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_farms import VALID_POLYGON, InMemoryFarmRepository


class InMemoryRecommendationRepository:
    def __init__(self) -> None:
        self.records: dict[uuid.UUID, RecommendationRecord] = {}

    def save(
        self,
        *,
        rec_id: uuid.UUID,
        farm_id: uuid.UUID,
        model_version: str,
        data_versions: dict[str, str],
        input_hash: str,
        payload: dict[str, Any],
    ) -> RecommendationRecord:
        rec = RecommendationRecord(
            id=rec_id,
            farm_id=farm_id,
            model_version=model_version,
            data_versions=data_versions,
            input_hash=input_hash,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self.records[rec_id] = rec
        return rec


def _auth_header(user_id: uuid.UUID, settings: Settings) -> dict[str, str]:
    token = encode_access_token(
        user_id=user_id,
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sim_client(
    settings: Settings,
) -> Iterator[tuple[TestClient, Settings, InMemoryRecommendationRepository]]:
    farm_repo = InMemoryFarmRepository()
    rec_repo = InMemoryRecommendationRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, rec_repo, FixtureMLClient()
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, settings, rec_repo


def test_enso_series_and_filtering(
    sim_client: tuple[TestClient, Settings, InMemoryRecommendationRepository],
) -> None:
    client, settings, _ = sim_client
    headers = _auth_header(uuid.uuid4(), settings)
    res = client.get("/v1/climate/enso?start=2024-01-01&end=2025-12-31", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["threshold_c"] == 0.5
    assert all("2024-01" <= item["month"] <= "2025-12" for item in body["items"])


def test_simulate_and_recommendations_flow(
    sim_client: tuple[TestClient, Settings, InMemoryRecommendationRepository],
) -> None:
    client, settings, rec_repo = sim_client
    headers_a = _auth_header(uuid.uuid4(), settings)
    headers_b = _auth_header(uuid.uuid4(), settings)

    farm_id = client.post(
        "/v1/farms",
        headers=headers_a,
        json={
            "name": "Sim Farm",
            "boundary": VALID_POLYGON,
            "current_rotation": ["maize", "fallow"],
        },
    ).json()["id"]

    sim_res = client.post(
        "/v1/scenarios/simulate",
        headers=headers_a,
        json={
            "farm_id": farm_id,
            "crop": "maize",
            "scenario": {
                "rainfall_change_pct": -20,
                "temperature_change_c": 1.0,
                "enso_phase": "el_nino",
            },
        },
    )
    assert sim_res.status_code == 200
    sim_body = sim_res.json()
    assert sim_body["scenario"]["p10"] <= sim_body["scenario"]["p50"] <= sim_body["scenario"]["p90"]
    assert sim_body["provenance"]["model_version"] == "fixture-0.1.0"

    rec_res = client.post(
        f"/v1/farms/{farm_id}/recommendations",
        headers=headers_a,
        json={
            "scenario": {
                "rainfall_change_pct": -20,
                "temperature_change_c": 1.0,
                "enso_phase": "el_nino",
            }
        },
    )
    assert rec_res.status_code == 201
    rec_body = rec_res.json()
    assert len(rec_body["strategies"]) >= 3
    assert any(s["is_current"] for s in rec_body["strategies"])
    for strat in rec_body["strategies"]:
        assert strat["why"] and strat["evidence"] and strat["benefits"]
        assert strat["gaps"] and strat["risks"] and strat["scores"]
    assert len(rec_repo.records) == 1

    # IDOR check
    assert (
        client.post(f"/v1/farms/{farm_id}/recommendations", headers=headers_b, json={}).status_code
        == 404
    )


def test_http_ml_client_down_returns_503_never_invented_numbers() -> None:
    farm_repo = InMemoryFarmRepository()
    rec_repo = InMemoryRecommendationRepository()
    app = create_app(Settings(database_url=TEST_DATABASE_URL))
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, rec_repo, HttpMLClient("http://127.0.0.1:1", timeout_seconds=0.1)
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = _auth_header(uuid.uuid4(), app.state.settings)
        farm_id = client.post(
            "/v1/farms", headers=headers, json={"name": "Down Farm", "boundary": VALID_POLYGON}
        ).json()["id"]
        res = client.post(
            "/v1/scenarios/simulate",
            headers=headers,
            json={"farm_id": farm_id, "crop": "maize", "scenario": {}},
        )
        assert res.status_code == 503
        assert res.json()["code"] == "service_unavailable"


def test_incomplete_ml_strategy_rejected() -> None:
    class BadMLClient(FixtureMLClient):
        def score_rotations(self, payload: dict[str, Any]) -> dict[str, Any]:
            data = super().score_rotations(payload)
            del data["strategies"][0]["gaps"]
            return data

    farm_repo = InMemoryFarmRepository()
    rec_repo = InMemoryRecommendationRepository()
    app = create_app(Settings(database_url=TEST_DATABASE_URL))
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, rec_repo, BadMLClient()
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = _auth_header(uuid.uuid4(), app.state.settings)
        farm_id = client.post(
            "/v1/farms", headers=headers, json={"name": "BadML Farm", "boundary": VALID_POLYGON}
        ).json()["id"]
        res = client.post(f"/v1/farms/{farm_id}/recommendations", headers=headers, json={})
        assert res.status_code == 503
        assert res.json()["code"] == "invalid_ml_response"
