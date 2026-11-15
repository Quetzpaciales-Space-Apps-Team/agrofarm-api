"""Unit and HTTP boundary tests for passwordless demo guest authentication (BE-090)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import (
    get_auth_service,
    get_farm_service,
    get_readiness_service,
    get_simulation_service,
)
from core_api.clients.demo import DemoMLClient
from core_api.config import Settings
from core_api.main import create_app
from core_api.services.auth import AuthService
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_auth import InMemoryAuthRepository
from tests.unit.test_farms import InMemoryFarmRepository
from tests.unit.test_simulation_and_recommendations import InMemoryRecommendationRepository


def _build_demo_client(
    *,
    demo_mode: bool = True,
    demo_rate_limit_per_minute: int = 20,
    demo_max_guests: int = 200,
) -> Iterator[TestClient]:
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        demo_mode=demo_mode,
        demo_rate_limit_per_minute=demo_rate_limit_per_minute,
        demo_max_guests=demo_max_guests,
    )
    app = create_app(settings)
    auth_repo = InMemoryAuthRepository()
    farm_repo = InMemoryFarmRepository()
    rec_repo = InMemoryRecommendationRepository()
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        auth_repo,
        jwt_secret=settings.jwt_secret.get_secret_value(),
        jwt_issuer=settings.jwt_issuer,
        jwt_audience=settings.jwt_audience,
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, rec_repo, DemoMLClient()
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def demo_client() -> Iterator[TestClient]:
    yield from _build_demo_client(demo_mode=True)


def test_demo_endpoint_returns_404_when_demo_mode_disabled() -> None:
    for client in _build_demo_client(demo_mode=False):
        resp = client.post("/v1/auth/demo")
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("application/problem+json")


def test_demo_guest_can_run_full_decision_flow(demo_client: TestClient) -> None:
    resp = demo_client.post("/v1/auth/demo")
    assert resp.status_code == 201
    data: dict[str, Any] = resp.json()
    assert data["token_type"] == "bearer"
    assert data["is_demo_guest"] is True
    assert data["farm_id"]
    assert "refresh_token" in resp.cookies

    headers = {"Authorization": f"Bearer {data['access_token']}"}
    farm_id = data["farm_id"]

    me = demo_client.get("/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"].startswith("demo-guest-")
    assert me.json()["email"].endswith("@demo.agrofarm.invalid")

    farm = demo_client.get(f"/v1/farms/{farm_id}", headers=headers)
    assert farm.status_code == 200
    assert farm.json()["name"] == "Guatemala Pilot Farm (Provisional)"

    priorities = demo_client.get(f"/v1/farms/{farm_id}/priorities", headers=headers)
    assert priorities.status_code == 200

    enso = demo_client.get("/v1/climate/enso", headers=headers)
    assert enso.status_code == 200

    recs = demo_client.post(
        f"/v1/farms/{farm_id}/recommendations",
        headers=headers,
        json={
            "scenario": {
                "enso_phase": "el_nino",
                "rainfall_change_pct": -15.0,
                "temperature_change_c": 1.2,
            }
        },
    )
    assert recs.status_code == 201
    assert len(recs.json()["strategies"]) >= 3


def test_demo_guests_are_isolated_from_each_other(demo_client: TestClient) -> None:
    guest_a = demo_client.post("/v1/auth/demo", headers={"X-Forwarded-For": "10.0.0.1"}).json()
    guest_b = demo_client.post("/v1/auth/demo", headers={"X-Forwarded-For": "10.0.0.2"}).json()

    assert guest_a["farm_id"] != guest_b["farm_id"]

    headers_b = {"Authorization": f"Bearer {guest_b['access_token']}"}
    forbidden = demo_client.get(f"/v1/farms/{guest_a['farm_id']}", headers=headers_b)
    assert forbidden.status_code in {403, 404}

    farms_b = demo_client.get("/v1/farms", headers=headers_b)
    assert farms_b.status_code == 200
    assert [item["id"] for item in farms_b.json()["items"]] == [guest_b["farm_id"]]


def test_demo_endpoint_enforces_per_ip_rate_limit() -> None:
    for client in _build_demo_client(demo_mode=True, demo_rate_limit_per_minute=2):
        r1 = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.1"})
        r2 = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.1"})
        r3 = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.1"})
        other_ip = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.2"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r3.status_code == 429
        assert other_ip.status_code == 201


def test_demo_endpoint_enforces_max_active_guests() -> None:
    for client in _build_demo_client(demo_mode=True, demo_max_guests=1):
        r1 = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.10"})
        r2 = client.post("/v1/auth/demo", headers={"X-Forwarded-For": "198.51.100.11"})
        assert r1.status_code == 201
        assert r2.status_code == 503
