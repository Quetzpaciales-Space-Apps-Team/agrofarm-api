from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agrofarm_api.config import Settings
from agrofarm_api.main import create_app

TEST_DATABASE_URL = 'postgresql+psycopg://agrofarm:agrofarm@localhost:5432/agrofarm'


class FakeDatabase:
    def __init__(self, up: bool) -> None:
        self.up = up

    def ping(self) -> bool:
        return self.up


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL,
        cors_origins=['http://localhost:5173'],
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    from agrofarm_api.api.dependencies import get_database

    app = create_app(settings)
    app.dependency_overrides[get_database] = lambda: FakeDatabase(up=True)
    with TestClient(app) as test_client:
        yield test_client
