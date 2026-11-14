import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_api.config import Settings
from core_api.main import create_app

PROBLEM_JSON = "application/problem+json"


def test_request_id_is_generated_when_the_client_sends_none(healthy_client: TestClient) -> None:
    response = healthy_client.get("/healthz")

    assert len(response.headers["x-request-id"]) >= 16


def test_request_id_from_the_client_is_propagated(healthy_client: TestClient) -> None:
    response = healthy_client.get("/healthz", headers={"X-Request-Id": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


def test_request_id_with_unsafe_characters_is_replaced(healthy_client: TestClient) -> None:
    response = healthy_client.get("/healthz", headers={"X-Request-Id": "bad id\twith spaces"})

    assert response.headers["x-request-id"] != "bad id\twith spaces"


def test_unknown_route_returns_problem_json(healthy_client: TestClient) -> None:
    response = healthy_client.get("/v1/does-not-exist", headers={"X-Request-Id": "req-404"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    body = response.json()
    assert body["code"] == "not_found"
    assert body["request_id"] == "req-404"


def test_unhandled_error_returns_a_generic_problem_without_leaking_details(
    settings: Settings,
) -> None:
    app: FastAPI = create_app(settings)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    assert response.json()["code"] == "internal_error"
    assert "secret internal detail" not in response.text


def test_every_request_is_logged_as_json_with_its_request_id(
    healthy_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="core_api.access"):
        healthy_client.get("/healthz", headers={"X-Request-Id": "req-log"})

    entries = [json.loads(record.getMessage()) for record in caplog.records]
    assert any(
        entry["request_id"] == "req-log" and entry["path"] == "/healthz" and entry["status"] == 200
        for entry in entries
    )


def test_cors_allows_only_listed_origins(healthy_client: TestClient) -> None:
    allowed = healthy_client.get("/healthz", headers={"Origin": "http://localhost:5173"})
    denied = healthy_client.get("/healthz", headers={"Origin": "https://evil.example"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
