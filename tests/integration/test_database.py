import os

import pytest
from fastapi.testclient import TestClient

from core_api.config import Settings
from core_api.main import create_app
from core_api.repositories.database import DatabaseProbe, create_db_engine

pytestmark = pytest.mark.integration


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("Integration tests need DATABASE_URL. Run them with `make test-integration`.")
    return url


def test_probe_answers_true_against_a_real_postgresql(database_url: str) -> None:
    engine = create_db_engine(database_url)

    assert DatabaseProbe(engine).ping() is True


def test_probe_answers_false_when_postgresql_is_unreachable() -> None:
    engine = create_db_engine("postgresql+psycopg://u:p@127.0.0.1:1/app", connect_timeout=1)

    assert DatabaseProbe(engine).ping() is False


def test_readyz_is_ready_with_the_real_database(database_url: str) -> None:
    with TestClient(create_app(Settings(database_url=database_url))) as client:
        response = client.get("/readyz")

    assert response.status_code == 200


def test_readyz_is_503_when_the_real_database_is_down() -> None:
    settings = Settings(database_url="postgresql+psycopg://u:p@127.0.0.1:1/app")
    with TestClient(create_app(settings)) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "failed"}


def test_search_extensions_exist_after_migrations(database_url: str) -> None:
    from sqlalchemy import text

    with create_db_engine(database_url).connect() as connection:
        names = set(connection.execute(text("SELECT extname FROM pg_extension")).scalars())

    assert {"pg_trgm", "unaccent"} <= names
