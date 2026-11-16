from fastapi.testclient import TestClient

PROBLEM_JSON = "application/problem+json"


def test_healthz_reports_alive_without_touching_dependencies(unhealthy_client: TestClient) -> None:
    response = unhealthy_client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_ready_when_every_dependency_answers(healthy_client: TestClient) -> None:
    response = healthy_client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok"}}


def test_readyz_fails_with_a_problem_response_when_the_database_is_down(
    unhealthy_client: TestClient,
) -> None:
    response = unhealthy_client.get("/readyz")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith(PROBLEM_JSON)
    body = response.json()
    assert body["code"] == "not_ready"
    assert body["status"] == 503
    assert body["checks"] == {"database": "failed"}
