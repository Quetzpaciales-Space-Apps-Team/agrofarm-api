from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_readiness_service
from core_api.config import Settings
from core_api.main import create_app
from core_api.services.readiness import ReadinessService

TEST_DATABASE_URL = "postgresql+psycopg://user:not-a-real-password@db.invalid:5432/app"


class FakeProbe:
    """Stands in for a repository that checks one dependency."""

    def __init__(self, name: str, healthy: bool) -> None:
        self.name = name
        self.healthy = healthy

    def ping(self) -> bool:
        return self.healthy


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url=TEST_DATABASE_URL, cors_allowed_origins=["http://localhost:5173"])


@pytest.fixture
def healthy_client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def unhealthy_client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=False)]
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
