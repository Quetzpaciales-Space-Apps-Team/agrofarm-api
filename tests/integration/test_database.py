import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from agrofarm_api.config import Settings
from agrofarm_api.main import create_app
from agrofarm_api.repositories.database import Database

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@pytest.fixture(scope="module", autouse=True)
def _require_db() -> None:
    if not DATABASE_URL:
        pytest.skip("DATABASE_URL is not set")


def test_ping_true_with_real_postgres() -> None:
    assert Database(DATABASE_URL).ping() is True


def test_ping_false_when_unreachable() -> None:
    assert Database("postgresql+psycopg://x:y@127.0.0.1:1/none").ping() is False


def test_readyz_with_real_postgres() -> None:
    app = create_app(Settings(database_url=DATABASE_URL))
    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 200


def test_only_required_extensions_are_enabled() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT extname FROM pg_extension"))}
    assert {"pg_trgm", "unaccent"} <= names
    assert "postgis" not in names


def test_alembic_baseline_applies() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
