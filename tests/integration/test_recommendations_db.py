"""PostgreSQL integration test for SqlAlchemyRecommendationRepository."""

import os
import uuid

import pytest

from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import SqlAlchemyFarmRepository
from core_api.repositories.recommendations import SqlAlchemyRecommendationRepository
from tests.integration.test_farms_db import BOUNDARY

pytestmark = pytest.mark.integration


def test_recommendation_repository_roundtrip() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url
    engine = create_db_engine(url)
    farm_repo = SqlAlchemyFarmRepository(engine)
    rec_repo = SqlAlchemyRecommendationRepository(engine)

    farm = farm_repo.create(
        owner_id=uuid.uuid4(),
        name="Rec DB Farm",
        boundary=BOUNDARY,
        area_ha=10.0,
        centroid_lat=14.59,
        centroid_lon=-90.53,
        current_rotation=["maize", "fallow"],
    )
    rec = rec_repo.save(
        rec_id=uuid.uuid4(),
        farm_id=farm.id,
        model_version="fixture-0.1.0",
        data_versions={"enso_monthly": "2026-11"},
        input_hash="abc123",
        payload={"strategies": []},
    )
    assert rec.model_version == "fixture-0.1.0"
    farm_repo.delete(farm.id)
