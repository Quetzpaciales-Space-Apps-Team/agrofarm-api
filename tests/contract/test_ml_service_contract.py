"""Contract tests between core-api HttpMLClient and expected ml-service OpenAPI."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator, RefResolver

from core_api.clients.ml import FixtureMLClient, HttpMLClient
from core_api.domain.problem import ProblemError
from core_api.domain.recommendations import (
    map_and_validate_recommendations,
    validate_simulation_response,
)

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "contract" / "ml-service-expected.yaml"
)


def _load_expected_contract() -> dict[str, Any]:
    return yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _validate_against(spec: dict[str, Any], schema_name: str, payload: dict[str, Any]) -> None:
    schema = spec["components"]["schemas"][schema_name]
    resolver = RefResolver.from_schema(spec)
    Draft202012Validator(schema, resolver=resolver).validate(payload)


def _httpx_post_adapter(
    transport: httpx.BaseTransport,
) -> Any:
    def _post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        try:
            with httpx.Client(transport=transport, timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                parsed: dict[str, Any] = resp.json()
                return parsed
        except httpx.TimeoutException as exc:
            raise TimeoutError(str(exc)) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise OSError(str(exc)) from exc

    return _post


def test_http_ml_client_matches_expected_contract() -> None:
    spec = _load_expected_contract()
    fixture = FixtureMLClient()

    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        if request.url.path == "/v1/simulate":
            _validate_against(spec, "SimulateRequest", body)
            return httpx.Response(200, json=fixture.simulate(body))
        if request.url.path == "/v1/rotations/score":
            _validate_against(spec, "RotationScoreRequest", body)
            return httpx.Response(200, json=fixture.score_rotations(body))
        return httpx.Response(404, json={"detail": "not found"})

    client = HttpMLClient(
        "http://ml-service.test", post_fn=_httpx_post_adapter(httpx.MockTransport(_handler))
    )

    farm_id = uuid.uuid4()
    sim_req = {
        "farm_id": str(farm_id),
        "centroid_lat": 14.59,
        "centroid_lon": -90.53,
        "crop": "maize",
        "scenario": {
            "rainfall_change_pct": -15.0,
            "temperature_change_c": 1.0,
            "enso_phase": "el_nino",
        },
    }
    sim_res = validate_simulation_response(client.simulate(sim_req))
    _validate_against(spec, "SimulateResponse", sim_res)

    rot_req = {
        "farm_id": str(farm_id),
        "centroid_lat": 14.59,
        "centroid_lon": -90.53,
        "current_rotation": ["maize", "fallow"],
        "priorities": {"weights": {"water_use": 0.8}, "constraints": {"water_availability": "low"}},
        "scenario": sim_req["scenario"],
    }
    rot_raw = client.score_rotations(rot_req)
    _validate_against(spec, "RotationScoreResponse", rot_raw)
    mapped = map_and_validate_recommendations(
        rec_id=uuid.uuid4(),
        farm_id=farm_id,
        raw=rot_raw,
    )
    assert len(mapped["strategies"]) >= 3
    assert any(s["is_current"] for s in mapped["strategies"])


def test_http_ml_client_raises_503_on_errors_and_timeouts() -> None:
    def _error_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "internal error"})

    err_client = HttpMLClient(
        "http://ml-service.test",
        post_fn=_httpx_post_adapter(httpx.MockTransport(_error_handler)),
    )
    with pytest.raises(ProblemError) as exc_info:
        err_client.simulate({"crop": "maize"})
    assert exc_info.value.status == 503

    def _timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    timeout_client = HttpMLClient(
        "http://ml-service.test",
        timeout_seconds=0.1,
        post_fn=_httpx_post_adapter(httpx.MockTransport(_timeout_handler)),
    )
    with pytest.raises(ProblemError) as timeout_exc:
        timeout_client.score_rotations({"farm_id": "123"})
    assert timeout_exc.value.status == 503


def test_http_ml_client_falls_back_to_fixture_when_configured() -> None:
    def _down_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = HttpMLClient(
        "http://ml-service.test",
        fallback=FixtureMLClient(),
        post_fn=_httpx_post_adapter(httpx.MockTransport(_down_handler)),
    )
    sim = client.simulate({"crop": "maize", "scenario": {"enso_phase": "el_nino"}})
    assert sim["provenance"]["model_version"] == "fixture-0.1.0"

    rot = client.score_rotations({"current_rotation": ["maize", "fallow"]})
    assert len(rot["strategies"]) >= 3
