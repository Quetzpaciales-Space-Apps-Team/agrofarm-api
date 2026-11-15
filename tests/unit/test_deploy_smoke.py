"""Behavioral deployment checks use a guest session, never a registered account."""

import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

SPEC = importlib.util.spec_from_file_location(
    "smoke_demo", Path(__file__).resolve().parents[2] / "deploy" / "smoke_demo.py"
)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def responses() -> list[dict[str, Any]]:
    return [
        {"access_token": "guest-test-token", "farm_id": "guest-farm"},
        {
            "scenario": {"p10": -10, "p50": 0, "p90": 10},
            "provenance": {"model_version": "stub-0.1.0"},
        },
        {
            "scenario": {"p10": 8, "p50": 18, "p90": 28},
            "provenance": {"model_version": "stub-0.1.0"},
        },
        {
            "strategies": [{"is_current": True}, {"is_current": False}, {"is_current": False}],
            "provenance": {"model_version": "rules-0.1.0"},
        },
    ]


def test_demo_smoke_checks_two_scenarios_and_recommendations_without_registration() -> None:
    with patch.object(smoke, "post_json", side_effect=responses()) as post:
        smoke.check_demo("https://api.example.test")
    calls = post.call_args_list
    assert [c.args[0] for c in calls] == [
        "https://api.example.test/v1/auth/demo",
        "https://api.example.test/v1/scenarios/simulate",
        "https://api.example.test/v1/scenarios/simulate",
        "https://api.example.test/v1/farms/guest-farm/recommendations",
    ]
    assert calls[1].args[1]["scenario"] == {}
    assert calls[2].args[1]["scenario"] == {"rainfall_change_pct": 40}
    assert all(c.args[2] == "guest-test-token" for c in calls[1:])


@pytest.mark.parametrize("version", ["cached_demo-0.1.0", "fixture-0.1.0", ""])
@pytest.mark.parametrize("index", [1, 2, 3])
def test_demo_smoke_rejects_offline_or_missing_provenance(version: str, index: int) -> None:
    items = responses()
    items[index]["provenance"]["model_version"] = version
    with (
        patch.object(smoke, "post_json", side_effect=items),
        pytest.raises(RuntimeError, match="live ML provenance"),
    ):
        smoke.check_demo("https://api.example.test")


def test_demo_smoke_rejects_constant_scenario_results() -> None:
    items = responses()
    items[2]["scenario"] = items[1]["scenario"]
    with (
        patch.object(smoke, "post_json", side_effect=items),
        pytest.raises(RuntimeError, match="did not change"),
    ):
        smoke.check_demo("https://api.example.test")


@pytest.mark.parametrize("strategies", [[], [{"is_current": True}], [False, False, False]])
def test_demo_smoke_requires_three_strategies_including_current(strategies: list[Any]) -> None:
    items = responses()
    items[3]["strategies"] = strategies
    with (
        patch.object(smoke, "post_json", side_effect=items),
        pytest.raises(RuntimeError, match="strategies"),
    ):
        smoke.check_demo("https://api.example.test")


def test_post_json_sends_guest_token_only_in_header() -> None:
    with patch.object(smoke.urllib.request, "urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = b'{"ok":true}'
        result = smoke.post_json("https://api.example.test/v1/test", {"scenario": {}}, "guest")
    request = urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer guest"
    assert json.loads(request.data) == {"scenario": {}}
    assert urlopen.call_args.kwargs["timeout"] == 60
    assert result == {"ok": True}


def test_post_json_requires_https_before_sending_credentials() -> None:
    with (
        patch.object(smoke.urllib.request, "urlopen") as urlopen,
        pytest.raises(RuntimeError, match="HTTPS"),
    ):
        smoke.post_json("http://api.example.test", {}, "guest")
    urlopen.assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        None,
        RuntimeError("Simulation did not change"),
        ValueError("private response with guest-test-token"),
    ],
)
def test_cli_reports_failure_without_exposing_response_or_token(
    failure: Exception | None, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch("sys.argv", ["smoke_demo.py", "https://api.example.test"]),
        patch.object(smoke, "check_demo", side_effect=failure),
    ):
        assert smoke.main() == (0 if failure is None else 1)
    output = capsys.readouterr()
    assert "guest-test-token" not in output.out + output.err
    assert "private response" not in output.out + output.err
    assert ("passed" in output.out) if failure is None else ("failed" in output.err)


def offline_baseline() -> dict[str, Any]:
    return {
        "scenario": {"p10": -28, "p50": -13, "p90": 2},
        "provenance": {"model_version": "cached_demo-0.1.0"},
    }


def test_demo_smoke_waits_for_a_cold_ml_service_and_then_passes() -> None:
    items = responses()
    items.insert(1, offline_baseline())  # the first request meets a cold ml-service
    sleeps: list[float] = []
    with patch.object(smoke, "post_json", side_effect=items) as post:
        smoke.check_demo(
            "https://api.example.test", attempts=3, wait_seconds=7, sleep=sleeps.append
        )
    assert sleeps == [7]
    assert post.call_count == 5


def test_demo_smoke_still_fails_when_the_ml_service_never_goes_live() -> None:
    items = [responses()[0], *[offline_baseline() for _ in range(3)]]
    sleeps: list[float] = []
    with (
        patch.object(smoke, "post_json", side_effect=items) as post,
        pytest.raises(RuntimeError, match="live ML provenance"),
    ):
        smoke.check_demo(
            "https://api.example.test", attempts=3, wait_seconds=7, sleep=sleeps.append
        )
    assert sleeps == [7, 7]  # no wait after the last attempt
    assert post.call_count == 4


def test_demo_smoke_makes_one_attempt_by_default_so_existing_callers_do_not_wait() -> None:
    items = [responses()[0], offline_baseline()]
    with (
        patch.object(smoke, "post_json", side_effect=items) as post,
        patch.object(smoke.time, "sleep") as sleep,
        pytest.raises(RuntimeError, match="live ML provenance"),
    ):
        smoke.check_demo("https://api.example.test")
    sleep.assert_not_called()
    assert post.call_count == 2


def test_cli_waits_for_a_cold_start_by_default_and_can_be_told_otherwise() -> None:
    with (
        patch("sys.argv", ["smoke_demo.py", "https://api.example.test"]),
        patch.object(smoke, "check_demo") as check,
    ):
        assert smoke.main() == 0
    assert check.call_args.kwargs == {"attempts": 5, "wait_seconds": 15.0}
    with (
        patch(
            "sys.argv",
            ["smoke_demo.py", "https://api.example.test", "--attempts", "1", "--wait-seconds", "0"],
        ),
        patch.object(smoke, "check_demo") as check,
    ):
        assert smoke.main() == 0
    assert check.call_args.kwargs == {"attempts": 1, "wait_seconds": 0.0}
