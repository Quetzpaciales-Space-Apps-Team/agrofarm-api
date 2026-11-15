"""HTTP boundary tests for GET /v1/climate/nasa-power (static NASA POWER monthly snapshot)."""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from core_api.api.deps import get_farm_service, get_readiness_service, get_simulation_service
from core_api.clients.ml import FixtureMLClient
from core_api.config import Settings
from core_api.contract import load_contract
from core_api.domain.auth import encode_access_token
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from tests.conftest import FakeProbe
from tests.unit.test_farms import InMemoryFarmRepository
from tests.unit.test_simulation_and_recommendations import InMemoryRecommendationRepository

SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2] / "src" / "core_api" / "demo_snapshots" / "nasa_power.json"
)
SNAPSHOT: dict[str, Any] = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
URL = "/v1/climate/nasa-power"
VALUE_FIELDS = (
    "rainfall_mm",
    "temperature_mean_c",
    "temperature_min_c",
    "temperature_max_c",
    "relative_humidity_pct",
    "solar_radiation_mj_m2",
    "wind_speed_kmh",
)


def _headers(settings: Settings) -> dict[str, str]:
    token = encode_access_token(
        user_id=uuid.uuid4(),
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def power_client(settings: Settings) -> Iterator[tuple[TestClient, dict[str, str]]]:
    farm_repo = InMemoryFarmRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, InMemoryRecommendationRepository(), FixtureMLClient()
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, _headers(settings)


def test_full_series_is_the_snapshot_unchanged(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = power_client
    res = client.get(URL, headers=headers)
    assert res.status_code == 200
    assert res.json() == SNAPSHOT


def test_first_and_last_month_of_the_snapshot(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = power_client
    items = client.get(URL, headers=headers).json()["items"]
    assert len(items) == 372
    assert items[0]["month"] == "1995-01"
    assert items[-1]["month"] == "2025-12"


def test_start_and_end_are_inclusive(power_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = power_client
    items = client.get(f"{URL}?start=2020-03&end=2020-05", headers=headers).json()["items"]
    assert [item["month"] for item in items] == ["2020-03", "2020-04", "2020-05"]
    same = client.get(f"{URL}?start=2020-03&end=2020-03", headers=headers).json()["items"]
    assert [item["month"] for item in same] == ["2020-03"]


def test_only_start_or_only_end(power_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = power_client
    from_start = client.get(f"{URL}?start=2025-11", headers=headers).json()["items"]
    assert [item["month"] for item in from_start] == ["2025-11", "2025-12"]
    to_end = client.get(f"{URL}?end=1995-02", headers=headers).json()["items"]
    assert [item["month"] for item in to_end] == ["1995-01", "1995-02"]


def test_range_without_data_gives_empty_items(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = power_client
    res = client.get(f"{URL}?start=2030-01&end=2030-12", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["disclaimer"]


def test_start_after_end_is_422_problem(power_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = power_client
    res = client.get(f"{URL}?start=2021-02&end=2021-01", headers=headers)
    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    "query",
    ["start=2020", "start=2020-13", "start=2020-00", "end=2020-1", "start=2020-01-01", "end=abc"],
)
def test_bad_month_format_is_422(
    power_client: tuple[TestClient, dict[str, str]], query: str
) -> None:
    client, headers = power_client
    res = client.get(f"{URL}?{query}", headers=headers)
    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/problem+json")


def test_unauthenticated_is_rejected_like_enso(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, _ = power_client
    power = client.get(URL)
    enso = client.get("/v1/climate/enso")
    assert power.status_code == enso.status_code == 401
    assert power.headers["content-type"] == enso.headers["content-type"]
    assert power.json()["code"] == enso.json()["code"]


def test_response_matches_the_contract_schema(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = power_client
    contract = load_contract()
    schema: dict[str, Any] = {
        "$ref": "#/components/schemas/NasaPowerSeries",
        "components": contract["components"],
    }
    validator = Draft202012Validator(schema)
    validator.validate(client.get(URL, headers=headers).json())
    validator.validate(client.get(f"{URL}?start=2030-01", headers=headers).json())


def test_provenance_is_honest_about_being_a_grid_cell(
    power_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, headers = power_client
    body = client.get(URL, headers=headers).json()
    assert body["disclaimer"]
    assert "not a station" in body["resolution_note"]
    assert "50 km" in body["resolution_note"]
    assert body["location"] == {"latitude": 14.59, "longitude": -90.53}
    assert len(body["dataset_checksum_sha256"]) == 64


def test_missing_values_stay_null_and_are_never_zeroed(
    power_client: tuple[TestClient, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, headers = power_client
    gap = {"month": "2000-01", **{field: None for field in VALUE_FIELDS}}
    rows = [gap if row["month"] == "2000-01" else row for row in SNAPSHOT["items"]]
    patched = {**SNAPSHOT, "items": rows}
    monkeypatch.setattr(
        "core_api.services.recommendations.load_demo_nasa_power_snapshot", lambda: patched
    )
    items = client.get(f"{URL}?start=2000-01&end=2000-01", headers=headers).json()["items"]
    assert items == [gap]
    for field in VALUE_FIELDS:
        assert items[0][field] is None


def test_snapshot_has_no_sentinel_values() -> None:
    for item in SNAPSHOT["items"]:
        for field in VALUE_FIELDS:
            assert item[field] is None or item[field] != -999
