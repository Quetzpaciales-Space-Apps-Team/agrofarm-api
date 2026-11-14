from pathlib import Path
from typing import Any

import schemathesis
import yaml
from fastapi.testclient import TestClient
from hypothesis import HealthCheck
from hypothesis import settings as hypothesis_settings
from schemathesis.core.transport import Response as SchemathesisResponse

from agrofarm_api.api.dependencies import get_database
from agrofarm_api.config import Settings
from agrofarm_api.main import create_app
from tests.conftest import TEST_DATABASE_URL, FakeDatabase

CONTRACT_PATH = Path(__file__).resolve().parents[2] / "docs" / "contract" / "openapi.yaml"

_stub_app = create_app(
    Settings(
        database_url=TEST_DATABASE_URL,
        cors_origins=["http://localhost:5173"],
    )
)
_stub_app.dependency_overrides[get_database] = lambda: FakeDatabase(up=True)
schema = schemathesis.openapi.from_asgi("/openapi.json", _stub_app)


def test_openapi_json_equals_committed_contract(client: TestClient) -> None:
    committed: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json() == committed


def test_contract_has_all_required_v1_paths() -> None:
    committed: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    paths = set(committed["paths"].keys())
    expected = {
        "/healthz",
        "/readyz",
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/auth/refresh",
        "/v1/auth/logout",
        "/v1/me",
        "/v1/farms",
        "/v1/farms/{id}",
        "/v1/farms/{id}/uploads",
        "/v1/farms/{id}/priorities",
        "/v1/farms/{id}/insights",
        "/v1/layers",
        "/v1/climate/enso",
        "/v1/scenarios/simulate",
        "/v1/farms/{id}/recommendations",
        "/v1/search",
    }
    assert expected <= paths


def test_v1_stub_endpoints_return_x_stub_header_and_guatemala_data(client: TestClient) -> None:
    # Auth
    reg = client.post(
        "/v1/auth/register",
        json={
            "email": "farmer@example.gt",
            "password": "secure-password-123",
            "full_name": "Maria Ixchel",
            "role": "farmer",
        },
    )
    assert reg.status_code == 201
    assert reg.headers["X-Stub"] == "true"
    assert reg.json()["user"]["email"] == "farmer@example.gt"

    login = client.post(
        "/v1/auth/login",
        json={"email": "farmer@example.gt", "password": "secure-password-123"},
    )
    assert login.status_code == 200
    assert login.headers["X-Stub"] == "true"

    refresh = client.post("/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.headers["X-Stub"] == "true"

    logout = client.post("/v1/auth/logout")
    assert logout.status_code == 204
    assert logout.headers["X-Stub"] == "true"

    me = client.get("/v1/me")
    assert me.status_code == 200
    assert me.headers["X-Stub"] == "true"

    # Farms (INSIVUMEH reference point in Guatemala City)
    farms = client.get("/v1/farms")
    assert farms.status_code == 200
    assert farms.headers["X-Stub"] == "true"
    farm_list = farms.json()
    assert len(farm_list["items"]) >= 1
    first_farm = farm_list["items"][0]
    assert first_farm["department"] == "Guatemala"
    assert 14.5 <= first_farm["reference_point"]["latitude"] <= 14.7
    assert -90.6 <= first_farm["reference_point"]["longitude"] <= -90.4
    farm_id = first_farm["id"]

    created_farm = client.post(
        "/v1/farms",
        json={
            "name": "Parcela San Jose",
            "department": "Sacatepequez",
            "municipality": "Antigua Guatemala",
            "reference_point": {"latitude": 14.5586, "longitude": -90.7295},
            "area_ha": 3.5,
            "current_rotation": ["maize", "black_bean"],
        },
    )
    assert created_farm.status_code == 201
    assert created_farm.headers["X-Stub"] == "true"

    single_farm = client.get(f"/v1/farms/{farm_id}")
    assert single_farm.status_code == 200
    assert single_farm.headers["X-Stub"] == "true"

    patched_farm = client.patch(
        f"/v1/farms/{farm_id}",
        json={"name": "Finca Experimental INSIVUMEH Actualizada"},
    )
    assert patched_farm.status_code == 200
    assert patched_farm.headers["X-Stub"] == "true"

    deleted_farm = client.delete(f"/v1/farms/{farm_id}")
    assert deleted_farm.status_code == 204
    assert deleted_farm.headers["X-Stub"] == "true"

    # Uploads
    uploads = client.get(f"/v1/farms/{farm_id}/uploads")
    assert uploads.status_code == 200
    assert uploads.headers["X-Stub"] == "true"

    created_upload = client.post(
        f"/v1/farms/{farm_id}/uploads",
        json={
            "filename": "parcel_history_2024.csv",
            "format": "csv",
            "content": "year,season,crop,yield_kg_ha\n2024,primera,maize,3400\n",
        },
    )
    assert created_upload.status_code == 201
    assert created_upload.headers["X-Stub"] == "true"

    # Priorities
    priorities = client.get(f"/v1/farms/{farm_id}/priorities")
    assert priorities.status_code == 200
    assert priorities.headers["X-Stub"] == "true"

    updated_priorities = client.put(
        f"/v1/farms/{farm_id}/priorities",
        json={
            "weights": {
                "yield_stability": 0.35,
                "soil_health": 0.25,
                "water_efficiency": 0.20,
                "income_diversification": 0.10,
                "low_input_cost": 0.10,
            },
            "irrigation_available": False,
            "max_fallow_days": 45,
            "excluded_crops": [],
        },
    )
    assert updated_priorities.status_code == 200
    assert updated_priorities.headers["X-Stub"] == "true"

    # Insights
    insights = client.get(f"/v1/farms/{farm_id}/insights")
    assert insights.status_code == 200
    assert insights.headers["X-Stub"] == "true"
    insights_body = insights.json()
    assert insights_body["bare_field_periods"]
    assert insights_body["vulnerable_seasons"]
    assert "disclaimer" in insights_body
    assert "provenance" in insights_body

    # Layers
    layers = client.get("/v1/layers")
    assert layers.status_code == 200
    assert layers.headers["X-Stub"] == "true"
    assert len(layers.json()["items"]) >= 3

    # ENSO
    enso = client.get("/v1/climate/enso")
    assert enso.status_code == 200
    assert enso.headers["X-Stub"] == "true"
    enso_body = enso.json()
    assert enso_body["threshold_c"] == 0.5
    assert len(enso_body["items"]) >= 3

    # Scenarios simulate
    sim = client.post(
        "/v1/scenarios/simulate",
        json={
            "farm_id": farm_id,
            "crop_id": "maize",
            "rainfall_change_pct": -15.0,
            "temperature_change_c": 1.2,
            "enso_phase": "el_nino",
        },
    )
    assert sim.status_code == 200
    assert sim.headers["X-Stub"] == "true"
    sim_body = sim.json()
    assert sim_body["scenario"]["p10"] <= sim_body["scenario"]["p50"] <= sim_body["scenario"]["p90"]
    assert "provenance" in sim_body
    assert "disclaimer" in sim_body

    # Recommendations (Rule G10: >=3 strategies including current rotation, required fields)
    rec = client.post(
        f"/v1/farms/{farm_id}/recommendations",
        json={"enso_phase": "la_nina", "rainfall_change_pct": 10.0, "temperature_change_c": 0.5},
    )
    assert rec.status_code == 200
    assert rec.headers["X-Stub"] == "true"
    rec_body = rec.json()
    strategies = rec_body["strategies"]
    assert len(strategies) >= 3
    assert any(s["is_current_rotation"] for s in strategies)
    for strategy in strategies:
        assert strategy["why"]
        assert strategy["evidence"]
        assert strategy["benefits"]
        assert strategy["gaps"]
        assert strategy["risks"]
        assert isinstance(strategy["needs_local_review"], bool)
        u = strategy["uncertainty"]
        assert u["p10"] <= u["p50"] <= u["p90"]
        assert "overall" in strategy["scores"]
    assert "provenance" in rec_body
    assert "support" in rec_body["disclaimer"].lower()

    # Search
    search = client.get("/v1/search", params={"q": "maiz", "type": "crop"})
    assert search.status_code == 200
    assert search.headers["X-Stub"] == "true"
    search_items = search.json()["items"]
    assert len(search_items) >= 1
    assert len(search_items) <= 20


@schema.parametrize()
@hypothesis_settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow],
)
def test_openapi_conformance_with_schemathesis(case: schemathesis.Case[Any]) -> None:
    response: SchemathesisResponse = case.call()
    case.validate_response(response)
