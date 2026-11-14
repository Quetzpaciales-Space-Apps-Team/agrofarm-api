import logging
import uuid

import pytest
from fastapi.testclient import TestClient


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get('/healthz', headers={'X-Request-Id': 'abc-123'})
    assert response.headers['X-Request-Id'] == 'abc-123'


def test_request_id_is_generated_when_missing(client: TestClient) -> None:
    generated = client.get('/healthz').headers['X-Request-Id']
    assert str(uuid.UUID(generated)) == generated


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    unsafe = 'bad id with spaces' + 'x' * 200
    value = client.get('/healthz', headers={'X-Request-Id': unsafe}).headers['X-Request-Id']
    assert value != unsafe
    uuid.UUID(value)


def test_log_line_contains_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger='agrofarm_api.access'):
        client.get('/healthz', headers={'X-Request-Id': 'log-me'})
    records = [r for r in caplog.records if r.name == 'agrofarm_api.access']
    assert records
    assert all(getattr(r, 'request_id', None) == 'log-me' for r in records)
