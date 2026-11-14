from fastapi.testclient import TestClient

from agrofarm_api.api.dependencies import get_database
from agrofarm_api.config import Settings
from agrofarm_api.main import create_app
from tests.conftest import FakeDatabase


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_readyz_returns_200_when_database_is_up(client: TestClient) -> None:
    response = client.get('/readyz')
    assert response.status_code == 200
    assert response.json() == {'status': 'ready'}


def test_readyz_returns_503_problem_when_database_is_down(settings: Settings) -> None:
    app = create_app(settings)
    app.dependency_overrides[get_database] = lambda: FakeDatabase(up=False)
    with TestClient(app) as client:
        response = client.get('/readyz')
    assert response.status_code == 503
    assert response.headers['content-type'].startswith('application/problem+json')
    assert response.json()['code'] == 'dependency_unavailable'
