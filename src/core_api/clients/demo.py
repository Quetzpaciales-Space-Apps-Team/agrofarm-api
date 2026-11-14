"""Offline demo snapshot client used when DEMO_MODE=true."""

import copy
import json
from pathlib import Path
from typing import Any

_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "demo_snapshots"


def _load_snapshot(filename: str) -> dict[str, Any]:
    path = _SNAPSHOT_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def load_demo_enso_snapshot() -> dict[str, Any]:
    """Return the cached ENSO time series snapshot for offline demo mode."""
    return copy.deepcopy(_load_snapshot("enso.json"))


class DemoMLClient:
    """Offline ML client serving deterministic cached_demo JSON snapshots."""

    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        snapshot = copy.deepcopy(_load_snapshot("simulate.json"))
        crop = payload.get("crop")
        if isinstance(crop, str) and crop:
            snapshot["crop"] = crop
        return snapshot

    def score_rotations(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = payload
        return copy.deepcopy(_load_snapshot("recommendations.json"))
