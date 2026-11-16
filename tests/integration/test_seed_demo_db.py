"""PostgreSQL integration test for idempotent demo seeding."""

import os
import uuid

import pytest

from core_api.repositories.database import create_db_engine
from core_api.repositories.recommendations import SqlAlchemyRecommendationRepository
from core_api.seed_demo import seed_demo

pytestmark = pytest.mark.integration


def test_seed_demo_is_idempotent() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url

    first = seed_demo(url)
    second = seed_demo(url)
    assert first == second

    engine = create_db_engine(url)
    rec = SqlAlchemyRecommendationRepository(engine).get(uuid.UUID(first["recommendation_id"]))
    assert rec is not None
    assert rec.data_versions.get("snapshot_mode") == "cached_demo"
