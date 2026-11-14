"""The contract (docs/contract/openapi.yaml) is the source of truth. These tests keep the
file valid, its examples honest, and the running service in line with it."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from core_api.contract import load_contract

CONTRACT = load_contract()
METHODS = ("get", "post", "put", "patch", "delete")
OPERATIONS = [
    (method, path, operation)
    for path, item in CONTRACT["paths"].items()
    for method, operation in item.items()
    if method in METHODS
]
STUBS = [(m, p, op) for m, p, op in OPERATIONS if op.get("x-stub")]
REQUIRED_V1_PATHS = {
    "/v1/auth/register", "/v1/auth/login", "/v1/auth/refresh", "/v1/auth/logout", "/v1/me",
    "/v1/farms", "/v1/farms/{farm_id}", "/v1/farms/{farm_id}/uploads",
    "/v1/farms/{farm_id}/priorities", "/v1/farms/{farm_id}/insights", "/v1/layers",
    "/v1/climate/enso", "/v1/scenarios/simulate", "/v1/farms/{farm_id}/recommendations",
    "/v1/search",
}  # fmt: skip
FARM_ID = "6f1c2f0a-9a0e-4d53-8a55-0d6d7a1b2c33"


def resolve(node: Any) -> Any:
    """Inline local $ref pointers so plain JSON Schema validation works."""
    if isinstance(node, dict):
        if "$ref" in node:
            target: Any = CONTRACT
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            return resolve(target)
        return {key: resolve(value) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve(item) for item in node]
    return node


def success(operation: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    status = min(int(code) for code in operation["responses"] if code.startswith("2"))
    return status, resolve(operation["responses"][str(status)])


def example_of(operation: dict[str, Any]) -> Any:
    _, response = success(operation)
    return response["content"]["application/json"]["example"]


def ids(operations: list[tuple[str, str, dict[str, Any]]]) -> list[str]:
    return [f"{method.upper()} {path}" for method, path, _ in operations]


def test_contract_is_a_valid_openapi_document() -> None:
    validate(CONTRACT)


def test_contract_covers_every_v1_path_of_the_plan() -> None:
    assert set(CONTRACT["paths"]) >= REQUIRED_V1_PATHS


@pytest.mark.parametrize(("method", "path", "operation"), OPERATIONS, ids=ids(OPERATIONS))
def test_every_success_response_has_an_example_that_matches_its_schema(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    status, response = success(operation)
    if status == 204:
        assert "content" not in response
        return
    media = response["content"]["application/json"]
    Draft202012Validator(media["schema"]).validate(media["example"])


@pytest.mark.parametrize(("method", "path", "operation"), OPERATIONS, ids=ids(OPERATIONS))
def test_every_request_example_matches_its_schema(
    method: str, path: str, operation: dict[str, Any]
) -> None:
    media = resolve(operation.get("requestBody", {})).get("content", {}).get("application/json")
    if media is None:
        return
    Draft202012Validator(media["schema"]).validate(media["example"])


def test_service_serves_the_contract_at_openapi_json(healthy_client: TestClient) -> None:
    served = healthy_client.get("/openapi.json").json()

    assert served["info"]["version"] == CONTRACT["info"]["version"]
    assert set(served["paths"]) == set(CONTRACT["paths"])


@pytest.mark.parametrize(("method", "path", "operation"), STUBS, ids=ids(STUBS))
def test_stub_endpoint_returns_the_example_of_the_contract(
    method: str, path: str, operation: dict[str, Any], healthy_client: TestClient
) -> None:
    status, _ = success(operation)

    response = healthy_client.request(method.upper(), path.replace("{farm_id}", FARM_ID))

    assert response.status_code == status
    if status == 204:
        assert response.content == b""
    else:
        assert response.json() == example_of(operation)


def test_stub_responses_say_they_are_stubs(healthy_client: TestClient) -> None:
    assert healthy_client.get("/v1/layers").headers["x-stub"] == "true"
    assert "x-stub" not in healthy_client.get("/healthz").headers


def test_problem_responses_match_the_problem_schema(healthy_client: TestClient) -> None:
    response = healthy_client.get("/v1/does-not-exist")

    Draft202012Validator(resolve(CONTRACT["components"]["schemas"]["Problem"])).validate(
        response.json()
    )


# Domain safety (AGENTS.md G10): the examples the frontend builds against must already
# carry everything a real answer must carry.
def test_recommendation_example_has_three_strategies_and_exactly_one_current() -> None:
    operation = CONTRACT["paths"]["/v1/farms/{farm_id}/recommendations"]["post"]
    strategies = example_of(operation)["strategies"]

    assert len(strategies) >= 3
    assert sum(1 for strategy in strategies if strategy["is_current"]) == 1


def test_every_strategy_example_explains_itself() -> None:
    operation = CONTRACT["paths"]["/v1/farms/{farm_id}/recommendations"]["post"]

    for strategy in example_of(operation)["strategies"]:
        for block in ("why", "evidence", "benefits", "gaps", "risks"):
            assert strategy[block], f"{strategy['id']} has no {block}"
        assert strategy["uncertainty"]["low"] <= strategy["uncertainty"]["high"]


def test_strategy_schema_rejects_a_strategy_without_gaps_or_risks() -> None:
    schema = resolve(CONTRACT["components"]["schemas"]["Strategy"])
    operation = CONTRACT["paths"]["/v1/farms/{farm_id}/recommendations"]["post"]
    strategy = dict(example_of(operation)["strategies"][0])

    for block in ("gaps", "risks"):
        broken = {**strategy, block: []}
        assert not Draft202012Validator(schema).is_valid(broken)


def test_simulation_example_has_ordered_quantiles_and_provenance() -> None:
    example = example_of(CONTRACT["paths"]["/v1/scenarios/simulate"]["post"])

    for key in ("baseline", "scenario"):
        assert example[key]["p10"] <= example[key]["p50"] <= example[key]["p90"]
    assert example["provenance"]["model_version"]
