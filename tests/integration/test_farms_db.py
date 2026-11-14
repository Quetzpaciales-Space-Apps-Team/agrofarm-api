"""PostgreSQL integration tests for SqlAlchemyFarmRepository."""

import os
import uuid

import pytest

from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import SqlAlchemyFarmRepository

pytestmark = pytest.mark.integration

BOUNDARY = {
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


def test_farm_and_priorities_roundtrip() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url, "DATABASE_URL must be set for integration tests"
    engine = create_db_engine(url)
    repo = SqlAlchemyFarmRepository(engine)
    owner_id = uuid.uuid4()

    created = repo.create(
        owner_id=owner_id,
        name="Integration Farm",
        boundary=BOUNDARY,
        area_ha=119.4,
        centroid_lat=14.59,
        centroid_lon=-90.53,
        current_rotation=["maize", "fallow"],
    )
    assert repo.get(created.id) is not None

    items, next_cursor = repo.list_by_owner(owner_id, limit=10, cursor=None)
    assert len(items) == 1
    assert next_cursor is None

    updated = repo.update(
        created.id,
        name="Integration Farm v2",
        boundary=None,
        area_ha=None,
        centroid_lat=None,
        centroid_lon=None,
        current_rotation=None,
    )
    assert updated is not None and updated.name == "Integration Farm v2"

    saved_prio = repo.put_priorities(
        created.id,
        weights={
            "water_use": 0.8,
            "income": 0.6,
            "soil_structure": 0.5,
            "forage_value": 0.2,
            "nitrogen_fixing": 0.7,
            "erosion_reduction": 0.9,
            "market_suitability": 0.5,
        },
        constraints={"water_availability": "low", "equipment": ["hand_tools"]},
    )
    assert saved_prio["weights"]["water_use"] == 0.8
    assert repo.get_priorities(created.id) == saved_prio

    assert repo.delete(created.id) is True
    assert repo.get(created.id) is None
