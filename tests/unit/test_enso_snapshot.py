"""GET /v1/climate/enso serves the real NOAA CPC series in every mode, not a few examples."""

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_farm_service, get_readiness_service, get_simulation_service
from core_api.clients.ml import FixtureMLClient
from core_api.config import Settings
from core_api.domain.auth import encode_access_token
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.recommendations import SimulationAndRecommendationService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_farms import InMemoryFarmRepository
from tests.unit.test_simulation_and_recommendations import InMemoryRecommendationRepository

SNAPSHOT: dict[str, Any] = json.loads(
    (
        Path(__file__).resolve().parents[2] / "src" / "core_api" / "demo_snapshots" / "enso.json"
    ).read_text(encoding="utf-8")
)
ITEMS: list[dict[str, Any]] = SNAPSHOT["items"]


def _phase(roni: float, threshold: float) -> str:
    return "el_nino" if roni >= threshold else "la_nina" if roni <= -threshold else "neutral"


def _month_number(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def test_the_snapshot_has_every_month_from_1950_with_no_gap_or_repeat() -> None:
    months = [item["month"] for item in ITEMS]
    assert months[0] == "1950-01"
    assert months[-1] >= "2026-09"
    assert [_month_number(m) for m in months] == list(
        range(_month_number(months[0]), _month_number(months[-1]) + 1)
    )


def test_every_phase_follows_the_threshold_applied_to_roni() -> None:
    threshold = SNAPSHOT["threshold_c"]
    assert threshold == 0.5
    assert all(item["phase"] == _phase(item["roni"], threshold) for item in ITEMS)


def test_known_noaa_values_are_in_the_snapshot() -> None:
    by_month = {item["month"]: item for item in ITEMS}
    assert by_month["2015-12"]["oni"] == pytest.approx(2.59)  # the strong 2015-16 El Nino
    assert by_month["2015-12"]["phase"] == "el_nino"
    assert by_month["2010-12"]["phase"] == "la_nina"
    assert by_month["1950-01"]["phase"] == "la_nina"


def test_the_source_says_what_the_data_is_and_that_it_is_stored() -> None:
    source = SNAPSHOT["source"]
    assert "NOAA CPC" in source
    assert "cached_demo" in source
    assert "1950-01" in source and ITEMS[-1]["month"] in source


def _client(settings: Settings) -> tuple[TestClient, dict[str, str]]:
    farm_repo = InMemoryFarmRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_simulation_service] = lambda: SimulationAndRecommendationService(
        farm_repo, InMemoryRecommendationRepository(), FixtureMLClient()
    )
    token = encode_access_token(
        user_id=uuid.uuid4(),
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return TestClient(app, raise_server_exceptions=False), {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("demo_mode", [True, False])
def test_both_modes_serve_the_full_series_and_filter_by_month(demo_mode: bool) -> None:
    client, headers = _client(Settings(database_url=TEST_DATABASE_URL, demo_mode=demo_mode))

    full = client.get("/v1/climate/enso", headers=headers).json()
    window = client.get("/v1/climate/enso?start=2024-01-01&end=2025-12-31", headers=headers).json()

    assert len(full["items"]) == len(ITEMS)
    assert full["source"] == SNAPSHOT["source"]
    assert [item["month"] for item in window["items"]] == [
        f"{year}-{month:02d}" for year in (2024, 2025) for month in range(1, 13)
    ]
