"""Photos require farm access and a real ML result; no offline diagnosis fallback."""

import copy
import io
import json
import uuid
from email.message import Message
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_leaf_service
from core_api.clients.leaves import HttpLeafClient
from core_api.config import Settings
from core_api.domain.auth import CurrentUser
from core_api.domain.farms import FarmCreateInput
from core_api.domain.problem import ProblemError
from core_api.main import create_app
from core_api.services.farms import FarmService
from core_api.services.leaves import LeafAssessmentService
from tests.unit.test_farms import VALID_POLYGON, InMemoryFarmRepository, _auth_header

RESULT: dict[str, Any] = {
    "assessment": "possible_condition",
    "candidate": "common_rust",
    "scores": {
        "common_rust": 0.96,
        "corn_leaf_blight": 0.01,
        "gray_leaf_spot": 0.01,
        "healthy": 0.01,
        "insect_damage": 0.01,
    },
    "score_interpretation": "Model scores are not calibrated probabilities.",
    "needs_local_review": True,
    "guidance": {"status": "needs_local_review", "sources": []},
    "limits": ["No external field validation."],
    "provenance": {"model_version": "maize-leaf-lightgbm-0.1.0", "data_versions": {}},
}


class LeafClient:
    calls = 0

    def assess(self, data: bytes, content_type: str) -> dict[str, Any]:
        self.calls += 1
        return copy.deepcopy(RESULT)


def test_photos_require_auth_and_farm_ownership_before_ml_call(settings: Settings) -> None:
    farms = FarmService(InMemoryFarmRepository())
    owner = CurrentUser(uuid.uuid4(), "farmer")
    farm = farms.create_farm(owner, FarmCreateInput(name="Test", boundary=VALID_POLYGON))
    ml = LeafClient()
    service = LeafAssessmentService(farms, ml)
    app = create_app(settings)
    app.dependency_overrides[get_leaf_service] = lambda: service
    client = TestClient(app)
    path = f"/v1/farms/{farm.id}/leaves/assess"
    assert client.post(path, content=b"photo").status_code == 401
    other = {**_auth_header(uuid.uuid4(), settings), "Content-Type": "image/jpeg"}
    assert client.post(path, content=b"photo", headers=other).status_code == 404
    assert ml.calls == 0
    headers = {**_auth_header(owner.id, settings), "Content-Type": "image/jpeg"}
    result = client.post(path, content=b"photo", headers=headers)
    assert result.status_code == 200
    assert result.json()["needs_local_review"] is True
    assert result.json()["provenance"]["input_hash"]
    assert "disclaimer" in result.json()
    assert (
        client.post(
            path, content=b"text", headers={**headers, "Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.post(path, content=b"0" * (5 * 1024 * 1024 + 1), headers=headers).status_code == 413
    )


def test_http_client_uses_service_identity_not_guest_token() -> None:
    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(RESULT).encode()
        result = HttpLeafClient(
            "https://ml.example.test",
            token_provider=lambda: "service-token",
            request_id="request-1",
        ).assess(b"photo", "image/jpeg")
    request = urlopen.call_args.args[0]
    assert request.data == b"photo"
    assert request.get_header("Authorization") == "Bearer service-token"
    assert request.get_header("X-request-id") == "request-1"
    assert result == RESULT


@pytest.mark.parametrize("status", [400, 413, 415, 403, 503])
def test_http_errors_are_sanitized_without_a_cached_diagnosis(status: int) -> None:
    error = HTTPError(
        "https://ml.example.test", status, "private detail", Message(), io.BytesIO(b"secret")
    )
    with patch("urllib.request.urlopen", side_effect=error), pytest.raises(ProblemError) as caught:
        HttpLeafClient("https://ml.example.test").assess(b"photo", "image/png")
    assert caught.value.status == (status if status in {400, 413, 415} else 503)
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize(
    "change",
    [
        {"needs_local_review": False},
        {"scores": {}},
        {"candidate": "fall_armyworm"},
        {"guidance": {}},
        {"provenance": {}},
    ],
)
def test_invalid_or_overconfident_ml_response_is_rejected(change: dict[str, Any]) -> None:
    bad = {**copy.deepcopy(RESULT), **change}
    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(bad).encode()
        with pytest.raises(ProblemError) as caught:
            HttpLeafClient("https://ml.example.test").assess(b"photo", "image/jpeg")
    assert caught.value.status == 502
