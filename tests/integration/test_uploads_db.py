"""PostgreSQL integration tests for SqlAlchemyUploadRepository."""

import os
import uuid

import pytest

from core_api.domain.uploads import RowErrorItem
from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import SqlAlchemyFarmRepository
from core_api.repositories.uploads import SqlAlchemyUploadRepository
from tests.integration.test_farms_db import BOUNDARY

pytestmark = pytest.mark.integration


def test_upload_repository_roundtrip() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url
    engine = create_db_engine(url)
    farm_repo = SqlAlchemyFarmRepository(engine)
    upload_repo = SqlAlchemyUploadRepository(engine)

    farm = farm_repo.create(
        owner_id=uuid.uuid4(),
        name="Upload DB Farm",
        boundary=BOUNDARY,
        area_ha=10.0,
        centroid_lat=14.59,
        centroid_lon=-90.53,
        current_rotation=["maize"],
    )
    created = upload_repo.create(
        upload_id=uuid.uuid4(),
        farm_id=farm.id,
        filename="test.csv",
        fmt="csv",
        status="accepted_with_errors",
        rows_total=2,
        rows_accepted=1,
        errors=[RowErrorItem(row=2, column="crop", message="Crop is required.")],
        raw_path="data/raw/uploads/test.csv",
        accepted_rows=[{"parcel_id": "p1", "crop": "maize"}],
    )
    assert created.rows_accepted == 1
    items, next_cursor = upload_repo.list_by_farm(farm.id, limit=10, cursor=None)
    assert len(items) == 1
    assert next_cursor is None
    farm_repo.delete(farm.id)
