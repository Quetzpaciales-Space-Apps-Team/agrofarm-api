"""Real HTTP integration test against a locally running agrofarm-analytic ml-service.

Skips cleanly when ml-service is not reachable on ML_SERVICE_URL (default http://127.0.0.1:8081)
so CI without ml-service stays green, while executing end-to-end when ml-service is running.
"""

import os
import urllib.error
import urllib.request
import uuid

import pytest
from fastapi.testclient import TestClient

from core_api.clients.ml import HttpMLClient
from core_api.config import Settings
from core_api.main import create_app

pytestmark = pytest.mark.integration

ML_URL = os.environ.get("ML_SERVICE_URL", "http://127.0.0.1:8081")


def _ml_service_is_up(base_url: str) -> bool:
    if not base_url.startswith(("http://", "https://")):
        return False
    try:
        with urllib.request.urlopen(  # noqa: S310
            f"{base_url.rstrip('/')}/healthz", timeout=1.5
        ) as resp:
            return int(resp.status) == 200
    except (OSError, urllib.error.URLError):
        return False


@pytest.mark.skipif(
    not _ml_service_is_up(ML_URL),
    reason=f"ml-service not reachable at {ML_URL}",
)
def test_core_api_ml_mode_http_against_real_ml_service() -> None:
    db_url = os.environ.get("DATABASE_URL")
    assert db_url

    client_ml = HttpMLClient(base_url=ML_URL, timeout_seconds=5.0)
    sim_direct = client_ml.simulate(
        {
            "farm_id": str(uuid.uuid4()),
            "centroid_lat": 14.635,
            "centroid_lon": -90.513,
            "crop": "maize",
            "scenario": {
                "rainfall_change_pct": -15.0,
                "temperature_change_c": 1.2,
                "enso_phase": "el_nino",
            },
        }
    )
    assert sim_direct["crop"] == "maize"
    assert sim_direct["unit"] == "%"
    assert {"p10", "p50", "p90"} <= set(sim_direct["scenario"])

    settings = Settings(
        database_url=db_url,
        ml_mode="http",
        ml_service_url=ML_URL,
        demo_mode=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        email = f"ml-http-{uuid.uuid4()}@example.com"
        reg = client.post(
            "/v1/auth/register",
            json={"email": email, "name": "ML HTTP Tester", "password": "correct horse battery"},
        )
        assert reg.status_code == 201
        login = client.post(
            "/v1/auth/login",
            json={"email": email, "password": "correct horse battery"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        farm = client.post(
            "/v1/farms",
            headers=headers,
            json={
                "name": "ML Integration Parcel",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-90.5150, 14.6330],
                            [-90.5110, 14.6330],
                            [-90.5110, 14.6370],
                            [-90.5150, 14.6370],
                            [-90.5150, 14.6330],
                        ]
                    ],
                },
                "current_rotation": ["maize", "beans"],
            },
        )
        assert farm.status_code == 201
        farm_id = farm.json()["id"]

        sim = client.post(
            "/v1/scenarios/simulate",
            headers=headers,
            json={
                "farm_id": farm_id,
                "crop": "maize",
                "scenario": {
                    "rainfall_change_pct": -15.0,
                    "temperature_change_c": 1.2,
                    "enso_phase": "el_nino",
                },
            },
        )
        assert sim.status_code == 200
        assert sim.json()["unit"] == "%"

        rec = client.post(
            f"/v1/farms/{farm_id}/recommendations",
            headers=headers,
            json={
                "scenario": {
                    "rainfall_change_pct": -15.0,
                    "temperature_change_c": 1.2,
                    "enso_phase": "el_nino",
                }
            },
        )
        assert rec.status_code == 201
        body = rec.json()
        strategies = body["strategies"]
        assert len(strategies) >= 3
        assert any(s["is_current"] for s in strategies)
        for strategy in strategies:
            for field in (
                "why",
                "evidence",
                "benefits",
                "gaps",
                "risks",
                "needs_local_review",
                "uncertainty",
                "scores",
            ):
                assert field in strategy
        assert body["provenance"]["model_version"]
