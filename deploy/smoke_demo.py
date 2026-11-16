"""Verify staging's live ML path using only a temporary demo guest.

Run with Python's standard library: python3 deploy/smoke_demo.py SERVICE_URL.
Never print response bodies, credentials, or guest identifiers.
"""

import argparse
import json
import sys
import time
import urllib.request
from collections.abc import Callable
from typing import Any


def post_json(url: str, payload: dict[str, Any], token: str = "") -> dict[str, Any]:
    if not url.startswith("https://"):
        raise RuntimeError("The staging smoke check requires HTTPS")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(  # noqa: S310 -- HTTPS checked above
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        parsed: dict[str, Any] = json.load(response)
        return parsed


def require_live(response: dict[str, Any]) -> None:
    provenance = response.get("provenance", {})
    version = provenance.get("model_version", "")
    if (
        not version
        or version.startswith(("cached_demo", "fixture"))
        or provenance.get("data_versions", {}).get("snapshot_mode") == "cached_demo"
    ):
        raise RuntimeError("Expected live ML provenance; check ML settings, URL, and invoker IAM")


def first_live_simulation(
    url: str,
    payload: dict[str, Any],
    token: str,
    attempts: int,
    wait_seconds: float,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    """Ask for a simulation until it is live. A cold ml-service answers the first call late, so
    core-api gives up on it and returns the cached answer; the next calls reach a warm service.
    A service that never goes live still fails after the last attempt."""
    for attempt in range(1, attempts + 1):
        response = post_json(url, payload, token)
        try:
            require_live(response)
        except RuntimeError:
            if attempt == attempts:
                raise
            sleep(wait_seconds)
        else:
            return response
    raise RuntimeError("The smoke check needs at least one attempt")


def check_demo(
    base_url: str,
    attempts: int = 1,
    wait_seconds: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    base_url = base_url.rstrip("/")
    guest = post_json(f"{base_url}/v1/auth/demo", {})
    token = guest["access_token"]
    payload = {"farm_id": guest["farm_id"], "crop": "beans", "scenario": {}}
    baseline = first_live_simulation(
        f"{base_url}/v1/scenarios/simulate", payload, token, attempts, wait_seconds, sleep
    )
    changed_payload = {**payload, "scenario": {"rainfall_change_pct": 40}}
    changed = post_json(f"{base_url}/v1/scenarios/simulate", changed_payload, token)
    require_live(changed)
    if baseline["scenario"]["p50"] == changed["scenario"]["p50"]:
        raise RuntimeError("Simulation did not change when rainfall changed")
    recommendations = post_json(
        f"{base_url}/v1/farms/{guest['farm_id']}/recommendations", {"scenario": {}}, token
    )
    require_live(recommendations)
    strategies = recommendations.get("strategies", [])
    if len(strategies) < 3 or not any(
        isinstance(strategy, dict) and strategy.get("is_current") is True for strategy in strategies
    ):
        raise RuntimeError("Expected at least three strategies including the current rotation")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service_url")
    parser.add_argument(
        "--attempts",
        type=int,
        default=5,
        help="Tries of the first simulation before failing; a cold ml-service needs more than one.",
    )
    parser.add_argument("--wait-seconds", type=float, default=15.0)
    args = parser.parse_args()
    try:
        check_demo(args.service_url, attempts=args.attempts, wait_seconds=args.wait_seconds)
    except RuntimeError as exc:
        print(f"Demo smoke check failed: {exc}", file=sys.stderr)  # noqa: T201
        return 1
    except Exception as exc:
        # HTTP errors and malformed responses may contain private data. Log only the type.
        print(f"Demo smoke check failed ({type(exc).__name__})", file=sys.stderr)  # noqa: T201
        return 1
    print("Demo smoke check passed: live scenario response and rotation comparison")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
