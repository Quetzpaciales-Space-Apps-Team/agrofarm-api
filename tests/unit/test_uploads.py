"""Unit and HTTP boundary tests for DEC-005 CSV/GeoJSON uploads, size limits, and IDOR."""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_farm_service, get_readiness_service, get_upload_service
from core_api.config import Settings
from core_api.domain.auth import encode_access_token
from core_api.domain.uploads import (
    RowErrorItem,
    UploadFormat,
    UploadRecord,
    UploadStatus,
    escape_csv_cell,
)
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.readiness import ReadinessService
from core_api.services.uploads import UploadService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_farms import VALID_POLYGON, InMemoryFarmRepository


class InMemoryUploadRepository:
    def __init__(self) -> None:
        self.uploads: dict[uuid.UUID, UploadRecord] = {}
        self.rows: dict[uuid.UUID, list[dict[str, Any]]] = {}

    def list_by_farm(
        self, farm_id: uuid.UUID, limit: int, cursor: str | None
    ) -> tuple[list[UploadRecord], str | None]:
        offset = int(cursor) if cursor and cursor.isdigit() else 0
        items = [u for u in self.uploads.values() if u.farm_id == farm_id]
        items.sort(key=lambda u: u.created_at, reverse=True)
        page = items[offset : offset + limit]
        next_cursor = str(offset + limit) if offset + limit < len(items) else None
        return page, next_cursor

    def create(
        self,
        *,
        upload_id: uuid.UUID,
        farm_id: uuid.UUID,
        filename: str,
        fmt: UploadFormat,
        status: UploadStatus,
        rows_total: int,
        rows_accepted: int,
        errors: list[RowErrorItem],
        raw_path: str,
        accepted_rows: list[dict[str, Any]],
    ) -> UploadRecord:
        rec = UploadRecord(
            id=upload_id,
            farm_id=farm_id,
            filename=filename,
            format=fmt,
            status=status,
            rows_total=rows_total,
            rows_accepted=rows_accepted,
            errors=errors,
            created_at=datetime.now(UTC),
        )
        self.uploads[upload_id] = rec
        self.rows[upload_id] = accepted_rows
        return rec


@pytest.fixture
def upload_client(tmp_path: Path) -> Iterator[tuple[TestClient, Settings]]:
    settings = Settings(
        database_url=TEST_DATABASE_URL,
        max_upload_bytes=1024,
        raw_uploads_dir=str(tmp_path / "raw"),
    )
    farm_repo = InMemoryFarmRepository()
    upload_repo = InMemoryUploadRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_farm_service] = lambda: FarmService(farm_repo)
    app.dependency_overrides[get_upload_service] = lambda: UploadService(
        farm_repo, upload_repo, raw_dir=tmp_path / "raw"
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, settings


def _auth_header(user_id: uuid.UUID, settings: Settings) -> dict[str, str]:
    token = encode_access_token(
        user_id=user_id,
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    return {"Authorization": f"Bearer {token}"}


def test_csv_upload_valid_and_row_errors(upload_client: tuple[TestClient, Settings]) -> None:
    client, settings = upload_client
    headers = _auth_header(uuid.uuid4(), settings)
    farm_id = client.post(
        "/v1/farms", headers=headers, json={"name": "Upload Farm", "boundary": VALID_POLYGON}
    ).json()["id"]

    csv_body = (
        b"parcel_id,season_year,crop,sowing_date,harvest_date,area_ha,latitude,longitude,yield_kg_ha\n"
        b"p1,2024,maize,2024-05-15,2024-10-20,2.5,14.5892,-90.5315,3200\n"
        b"p2,2024,beans,15/05/2024,2024-04-01,-1.0,95.0,-90.53,-10\n"
    )
    res = client.post(
        f"/v1/farms/{farm_id}/uploads",
        headers=headers,
        files={"file": ("records.csv", csv_body, "text/csv")},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "accepted_with_errors"
    assert body["rows_total"] == 2
    assert body["rows_accepted"] == 1
    assert any(e["row"] == 2 and e["column"] == "sowing_date" for e in body["errors"])

    listed = client.get(f"/v1/farms/{farm_id}/uploads", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


def test_geojson_upload_and_oversized_rejected(upload_client: tuple[TestClient, Settings]) -> None:
    client, settings = upload_client
    headers = _auth_header(uuid.uuid4(), settings)
    farm_id = client.post(
        "/v1/farms", headers=headers, json={"name": "Geo Farm", "boundary": VALID_POLYGON}
    ).json()["id"]

    geojson = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": VALID_POLYGON,
                    "properties": {
                        "parcel_id": "p1",
                        "season_year": 2025,
                        "crop": "maize",
                        "sowing_date": "2025-05-15",
                        "area_ha": 2.5,
                    },
                }
            ],
        }
    ).encode()
    res = client.post(
        f"/v1/farms/{farm_id}/uploads",
        headers=headers,
        files={"file": ("plot.geojson", geojson, "application/geo+json")},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "accepted"

    huge = b"a" * 2048
    too_big = client.post(
        f"/v1/farms/{farm_id}/uploads",
        headers=headers,
        files={"file": ("huge.csv", huge, "text/csv")},
    )
    assert too_big.status_code == 413


def test_upload_idor_and_csv_escape(upload_client: tuple[TestClient, Settings]) -> None:
    client, settings = upload_client
    headers_a = _auth_header(uuid.uuid4(), settings)
    headers_b = _auth_header(uuid.uuid4(), settings)
    farm_id = client.post(
        "/v1/farms", headers=headers_a, json={"name": "A Farm", "boundary": VALID_POLYGON}
    ).json()["id"]

    assert client.get(f"/v1/farms/{farm_id}/uploads", headers=headers_b).status_code == 404
    assert (
        client.post(
            f"/v1/farms/{farm_id}/uploads",
            headers=headers_b,
            files={"file": ("a.csv", b"parcel_id\n", "text/csv")},
        ).status_code
        == 404
    )
    assert escape_csv_cell("=CMD()") == "'=CMD()"
    assert escape_csv_cell("+123") == "'+123"
    assert escape_csv_cell("-99") == "'-99"
    assert escape_csv_cell("@SUM") == "'@SUM"
    assert escape_csv_cell("maize") == "maize"
