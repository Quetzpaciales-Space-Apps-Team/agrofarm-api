from fastapi import APIRouter
from fastapi.testclient import TestClient

from agrofarm_api.config import Settings
from agrofarm_api.main import create_app
from agrofarm_api.middleware.error_handler import ProblemError


def _client(settings: Settings) -> TestClient:
    app = create_app(settings)
    router = APIRouter()

    @router.get("/_test/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    @router.get("/_test/problem")
    def problem() -> None:
        raise ProblemError(status=409, code="conflict_example", title="Conflict", detail="nope")

    @router.get("/_test/int/{value}")
    def int_route(value: int) -> dict[str, int]:
        return {"value": value}

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_problem_error_shape(settings: Settings) -> None:
    response = _client(settings).get("/_test/problem", headers={"X-Request-Id": "r1"})
    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "conflict_example"
    assert body["status"] == 409
    assert body["title"] == "Conflict"
    assert body["detail"] == "nope"
    assert body["request_id"] == "r1"


def test_validation_error_is_problem_json(settings: Settings) -> None:
    response = _client(settings).get("/_test/int/abc")
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"


def test_unknown_route_is_problem_json(settings: Settings) -> None:
    response = _client(settings).get("/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "not_found"


def test_unhandled_exception_hides_details(settings: Settings) -> None:
    response = _client(settings).get("/_test/boom")
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "internal_error"
    assert "secret" not in response.text
    assert "X-Request-Id" in response.headers
