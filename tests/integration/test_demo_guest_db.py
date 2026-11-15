"""PostgreSQL integration tests for demo guest provisioning and 24h purge."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from core_api.config import Settings
from core_api.main import create_app
from core_api.purge_demo_guests import purge_demo_guests
from core_api.repositories.auth import UserRow
from core_api.repositories.database import create_db_engine
from core_api.repositories.farms import FarmRow

pytestmark = pytest.mark.integration


def test_demo_guest_persists_and_purges_after_24_hours() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url

    app = create_app(Settings(database_url=url, demo_mode=True))
    with TestClient(app) as client:
        resp = client.post("/v1/auth/demo")
        assert resp.status_code == 201
        payload = resp.json()
        farm_id = uuid.UUID(payload["farm_id"])
        me = client.get(
            "/v1/me",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
        )
        assert me.status_code == 200
        user_id = uuid.UUID(me.json()["id"])

    engine = create_db_engine(url)
    # Freshly created demo guest should not be purged with 24h cutoff.
    assert purge_demo_guests(database_url=url, max_age_hours=24) == 0

    # Backdate created_at by 25 hours and verify purge deletes user + cloned farm.
    with Session(engine) as session:
        session.execute(
            update(UserRow)
            .where(UserRow.id == user_id)
            .values(created_at=datetime.now(UTC) - timedelta(hours=25))
        )
        session.commit()

    removed = purge_demo_guests(database_url=url, max_age_hours=24)
    assert removed >= 1

    with Session(engine) as session:
        assert session.get(UserRow, user_id) is None
        assert session.get(FarmRow, farm_id) is None
