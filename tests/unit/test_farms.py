"""Unit and HTTP boundary tests for farms CRUD, polygon validation, priorities, and IDOR."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_farm_service, get_readiness_service
from core_api.config import Settings
from core_api.domain.auth import encode_access_token
from core_api.domain.farms import FarmRecord
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from tests.conftest import FakeProbe

VALID_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-90.535, 14.585],
            [-90.525, 14.585],
            [-90.525, 14.595],
            [-90.535, 14.595],
            [-90.535, 14.585],
        ]
    ],
}


class InMemoryFarmRepository:
    def __init__(self) -> None:
        self.farms: dict[uuid.UUID, FarmRecord] = {}
        self.priorities: dict[uuid.UUID, dict[str, Any]] = {}

    def list_by_owner(
        self, owner_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[FarmRecord], str | None]:
        offset = int(cursor) if cursor and cursor.isdigit() else 0
        owned = [f for f in self.farms.values() if f.owner_id == owner_id]
        owned.sort(key=lambda f: f.created_at, reverse=True)
        page = owned[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(owned) else None
        return page, next_cursor

    def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        boundary: dict[str, Any],
        area_ha: float,
        centroid_lat: float,
        centroid_lon: float,
        current_rotation: list[str],
    ) -> FarmRecord:
        record = FarmRecord(
            id=uuid.uuid4(),
            owner_id=owner_id,
            name=name,
            boundary=boundary,
            area_ha=area_ha,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            current_rotation=current_rotation,
            created_at=datetime.now(UTC),
        )
        self.farms[record.id] = record
        return record

    def get(self, farm_id: uuid.UUID) -> FarmRecord | None:
        return self.farms.get(farm_id)

    def update(
        self,
        farm_id: uuid.UUID,
        *,
        name: str | None,
        boundary: dict[str, Any] | None,
        area_ha: float | None,
        centroid_lat: float | None,
        centroid_lon: float | None,
        current_rotation: list[str] | None,
    ) -> FarmRecord | None:
        existing = self.farms.get(farm_id)
        if not existing:
            return None
        updated = FarmRecord(
            id=existing.id,
            owner_id=existing.owner_id,
            name=name if name is not None else existing.name,
            boundary=boundary if boundary is not None else existing.boundary,
            area_ha=area_ha if area_ha is not None else existing.area_ha,
            centroid_lat=centroid_lat if centroid_lat is not None else existing.centroid_lat,
            centroid_lon=centroid_lon if centroid_lon is not None else existing.centroid_lon,
            current_rotation=(
                current_rotation if current_rotation is not None else existing.current_rotation
            ),
            created_at=existing.created_at,
        )
        self.farms[farm_id] = updated
        return updated

    def delete(self, farm_id: uuid.UUID) -> bool:
        self.priorities.pop(farm_id, None)
        return self.farms.pop(farm_id, None) is not None

    def get_priorities(self, farm_id: uuid.UUID) -> dict[str, Any] | None:
        return self.priorities.get(farm_id)

    def put_priorities(
        self, farm_id: uuid.UUID, weights: dict[str, float], constraints: dict[str, Any]
    ) -> dict[str, Any]:
        val = {"weights": weights, "constraints": constraints}
        self.priorities[farm_id] = val
        return val


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
def farm_client(settings: Settings) -> Iterator[tuple[TestClient, Settings]]:
    repo = InMemoryFarmRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(repo)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, settings


def test_farms_require_authentication(farm_client: tuple[TestClient, Settings]) -> None:
    client, _ = farm_client
    assert client.get("/v1/farms").status_code == 401
    assert (
        client.post("/v1/farms", json={"name": "A", "boundary": VALID_POLYGON}).status_code == 401
    )
    assert client.get(f"/v1/farms/{uuid.uuid4()}").status_code == 401


def test_farm_crud_and_pagination(farm_client: tuple[TestClient, Settings]) -> None:
    client, settings = farm_client
    headers = _auth_header(uuid.uuid4(), settings)

    res1 = client.post(
        "/v1/farms",
        headers=headers,
        json={"name": "Farm 1", "boundary": VALID_POLYGON, "current_rotation": ["maize", "fallow"]},
    )
    assert res1.status_code == 201
    farm1 = res1.json()
    assert farm1["area_ha"] > 0

    res2 = client.post(
        "/v1/farms",
        headers=headers,
        json={"name": "Farm 2", "boundary": VALID_POLYGON},
    )
    assert res2.status_code == 201

    page1 = client.get("/v1/farms?limit=1", headers=headers)
    assert page1.status_code == 200
    body1 = page1.json()
    assert len(body1["items"]) == 1
    assert body1["next_cursor"] == "1"

    page2 = client.get(f"/v1/farms?limit=1&cursor={body1['next_cursor']}", headers=headers)
    assert page2.status_code == 200
    assert len(page2.json()["items"]) == 1
    assert page2.json()["next_cursor"] is None

    got = client.get(f"/v1/farms/{farm1['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Farm 1"

    patched = client.patch(
        f"/v1/farms/{farm1['id']}",
        headers=headers,
        json={"name": "Farm 1 Updated", "boundary": VALID_POLYGON},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Farm 1 Updated"

    deleted = client.delete(f"/v1/farms/{farm1['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/v1/farms/{farm1['id']}", headers=headers).status_code == 404


def test_invalid_polygon_rejected(farm_client: tuple[TestClient, Settings]) -> None:
    client, settings = farm_client
    headers = _auth_header(uuid.uuid4(), settings)
    bad_polygon = {
        "type": "Polygon",
        "coordinates": [[[-90.535, 14.585], [-90.525, 14.585], [-90.525, 95.0], [-90.535, 14.595]]],
    }
    res = client.post("/v1/farms", headers=headers, json={"name": "Bad", "boundary": bad_polygon})
    assert res.status_code == 422
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["errors"]


def test_idor_isolation_between_users(farm_client: tuple[TestClient, Settings]) -> None:
    client, settings = farm_client
    headers_a = _auth_header(uuid.uuid4(), settings)
    headers_b = _auth_header(uuid.uuid4(), settings)

    farm_id = client.post(
        "/v1/farms", headers=headers_a, json={"name": "A Farm", "boundary": VALID_POLYGON}
    ).json()["id"]

    assert client.get(f"/v1/farms/{farm_id}", headers=headers_b).status_code == 404
    assert (
        client.patch(f"/v1/farms/{farm_id}", headers=headers_b, json={"name": "Hacked"}).status_code
        == 404
    )
    assert client.delete(f"/v1/farms/{farm_id}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/farms/{farm_id}/priorities", headers=headers_b).status_code == 404


def test_priorities_get_put_and_validation(farm_client: tuple[TestClient, Settings]) -> None:
    client, settings = farm_client
    headers = _auth_header(uuid.uuid4(), settings)
    farm_id = client.post(
        "/v1/farms", headers=headers, json={"name": "P Farm", "boundary": VALID_POLYGON}
    ).json()["id"]

    default_res = client.get(f"/v1/farms/{farm_id}/priorities", headers=headers)
    assert default_res.status_code == 200
    assert default_res.json()["weights"]["water_use"] == 0.5

    valid_weights: dict[str, float] = {
        "water_use": 0.9,
        "income": 0.7,
        "soil_structure": 0.5,
        "forage_value": 0.1,
        "nitrogen_fixing": 0.6,
        "erosion_reduction": 0.8,
        "market_suitability": 0.4,
    }
    valid_payload: dict[str, Any] = {
        "weights": valid_weights,
        "constraints": {"water_availability": "low", "equipment": ["hand_tools"]},
    }
    put_res = client.put(f"/v1/farms/{farm_id}/priorities", headers=headers, json=valid_payload)
    assert put_res.status_code == 200
    assert put_res.json()["weights"]["water_use"] == 0.9

    bad_payload = {
        **valid_payload,
        "weights": {**valid_weights, "water_use": 1.5},
    }
    assert (
        client.put(f"/v1/farms/{farm_id}/priorities", headers=headers, json=bad_payload).status_code
        == 422
    )
