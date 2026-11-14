from fastapi.testclient import TestClient

from agrofarm_api.config import Settings
from agrofarm_api.main import create_app


def test_allowed_origin_gets_cors_headers(client: TestClient) -> None:
    response = client.get('/healthz', headers={'Origin': 'http://localhost:5173'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert response.headers['access-control-allow-credentials'] == 'true'


def test_unknown_origin_gets_no_cors_headers(client: TestClient) -> None:
    response = client.get('/healthz', headers={'Origin': 'https://evil.example.com'})
    assert 'access-control-allow-origin' not in response.headers


def test_empty_allowlist_allows_no_origin(settings: Settings) -> None:
    app = create_app(settings.model_copy(update={'cors_origins': []}))
    with TestClient(app) as c:
        response = c.get('/healthz', headers={'Origin': 'http://localhost:5173'})
    assert 'access-control-allow-origin' not in response.headers
