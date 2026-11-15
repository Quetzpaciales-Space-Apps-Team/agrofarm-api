"""core-api calls a private ml-service on Cloud Run with a Google-signed identity token."""

import io
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from core_api.api.deps import get_ml_client
from core_api.clients import ml
from core_api.clients.ml import GoogleIdTokenProvider, HttpMLClient
from core_api.config import Settings
from core_api.domain.problem import ProblemError
from tests.conftest import TEST_DATABASE_URL

ML_URL = "https://ml-service-staging.example.run.app"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class FakeMetadata:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail = False

    def __call__(self, audience: str) -> str:
        if self.fail:
            raise OSError("metadata server unreachable")
        self.calls.append(audience)
        return f"token-{len(self.calls)}"


def capture_requests(monkeypatch: pytest.MonkeyPatch) -> list[urllib.request.Request]:
    seen: list[urllib.request.Request] = []

    def fake_urlopen(req: urllib.request.Request, timeout: float) -> Any:
        seen.append(req)
        return io.BytesIO(json.dumps({"ok": True}).encode("utf-8"))

    monkeypatch.setattr(ml.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_token_is_requested_for_the_ml_service_url_and_cached() -> None:
    metadata, clock = FakeMetadata(), FakeClock()
    provider = GoogleIdTokenProvider(ML_URL, fetch=metadata, clock=clock)
    assert provider() == "token-1"
    clock.now += 60
    assert provider() == "token-1"
    assert metadata.calls == [ML_URL]


def test_token_is_refreshed_before_it_expires() -> None:
    metadata, clock = FakeMetadata(), FakeClock()
    provider = GoogleIdTokenProvider(ML_URL, fetch=metadata, clock=clock)
    provider()
    clock.now += GoogleIdTokenProvider.REFRESH_AFTER_SECONDS + 1
    assert provider() == "token-2"


def test_request_carries_the_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture_requests(monkeypatch)
    client = HttpMLClient(ML_URL, token_provider=lambda: "abc.def.ghi")
    assert client.simulate({"crop": "maize"}) == {"ok": True}
    assert seen[0].get_header("Authorization") == "Bearer abc.def.ghi"
    assert seen[0].full_url == f"{ML_URL}/v1/simulate"


def test_no_token_provider_sends_no_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture_requests(monkeypatch)
    HttpMLClient(ML_URL).simulate({"crop": "maize"})
    assert seen[0].get_header("Authorization") is None


def test_token_failure_is_a_503_and_never_an_unauthenticated_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = capture_requests(monkeypatch)
    metadata = FakeMetadata()
    metadata.fail = True
    provider = GoogleIdTokenProvider(ML_URL, fetch=metadata, clock=FakeClock())
    with pytest.raises(ProblemError) as raised:
        HttpMLClient(ML_URL, token_provider=provider).simulate({"crop": "maize"})
    assert raised.value.status == 503
    assert seen == []


def test_token_never_appears_in_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(req: urllib.request.Request, timeout: float) -> Any:
        raise urllib.error.URLError("forbidden")

    monkeypatch.setattr(ml.urllib.request, "urlopen", refuse)
    with pytest.raises(ProblemError) as raised:
        HttpMLClient(ML_URL, token_provider=lambda: "very-secret-token").simulate({})
    assert "very-secret-token" not in str(raised.value.__dict__)


def test_settings_select_the_token_provider() -> None:
    plain = Settings(database_url=TEST_DATABASE_URL, ml_mode="http", ml_service_url=ML_URL)
    signed = Settings(
        database_url=TEST_DATABASE_URL,
        ml_mode="http",
        ml_service_url=ML_URL,
        ml_auth="google_id_token",
    )
    plain_client, signed_client = get_ml_client(plain), get_ml_client(signed)
    assert isinstance(plain_client, HttpMLClient)
    assert isinstance(signed_client, HttpMLClient)
    assert plain_client.token_provider is None
    assert isinstance(signed_client.token_provider, GoogleIdTokenProvider)
    assert signed_client.token_provider.audience == ML_URL


def test_unknown_ml_auth_is_rejected() -> None:
    with pytest.raises(ValueError, match="ml_auth"):
        Settings(database_url=TEST_DATABASE_URL, ml_auth="basic")
