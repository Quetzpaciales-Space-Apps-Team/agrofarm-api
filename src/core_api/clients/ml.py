"""ML service client behind an interface with ML_MODE=http|fixture."""

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any, Protocol

from core_api.domain.problem import ProblemError
from core_api.domain.recommendations import DISCLAIMER_TEXT


class MLClient(Protocol):
    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def score_rotations(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class FixtureMLClient:
    """Deterministic fixture client for offline/local/CI runs."""

    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        scenario = payload.get("scenario", {})
        rain = float(scenario.get("rainfall_change_pct", 0.0))
        temp = float(scenario.get("temperature_change_c", 0.0))
        phase = str(scenario.get("enso_phase", "neutral"))
        crop = str(payload.get("crop", "maize"))

        phase_shift = -4.0 if phase == "el_nino" else (3.0 if phase == "la_nina" else 0.0)
        p50 = round((rain * 0.45) - (temp * 2.5) + phase_shift, 2)
        return {
            "crop": crop,
            "target": "yield_anomaly_pct",
            "unit": "%",
            "baseline": {"p10": -12.0, "p50": 0.0, "p90": 11.0},
            "scenario": {
                "p10": round(p50 - 16.0, 2),
                "p50": p50,
                "p90": round(p50 + 15.0, 2),
            },
            "attributions": [
                {"feature": "rainfall_anomaly_jja", "contribution": round(rain * 0.42, 2)},
                {"feature": "enso_roni_lag3", "contribution": round(phase_shift, 2)},
                {"feature": "temperature_anomaly_jja", "contribution": round(-temp * 2.2, 2)},
            ],
            "out_of_range_inputs": ["rainfall_change_pct"] if abs(rain) > 60 else [],
            "provenance": {
                "model_version": "fixture-0.1.0",
                "data_versions": {"nasa_power": "2026-11-14", "enso_monthly": "2026-11"},
                "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
        }

    def score_rotations(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = payload.get("current_rotation") or ["maize", "fallow"]
        weights = payload.get("priorities", {}).get("weights", {})
        water_w = float(weights.get("water_use", 0.5))
        erosion_w = float(weights.get("erosion_reduction", 0.5))

        return {
            "disclaimer": DISCLAIMER_TEXT,
            "strategies": [
                {
                    "id": "current",
                    "name": "Current rotation (" + " -> ".join(current) + ")",
                    "is_current": True,
                    "sequence": current,
                    "overall_score": 0.48,
                    "scores": {
                        "water_use": 0.5,
                        "income": 0.6,
                        "soil_structure": 0.3,
                        "forage_value": 0.1,
                        "nitrogen_fixing": 0.1,
                        "erosion_reduction": 0.3,
                        "market_suitability": 0.7,
                    },
                    "uncertainty": {"low": 0.38, "high": 0.57},
                    "why": ["This is what the farm does today. It is the baseline for comparison."],
                    "evidence": [
                        {
                            "statement": (
                                "93% of yearly rain falls May-October at INSIVUMEH station."
                            ),
                            "source": "insivumeh_daily",
                        }
                    ],
                    "benefits": ["Known practice, no new equipment required."],
                    "gaps": ["Limited parcel-level historical yield records."],
                    "risks": [
                        {
                            "description": "Bare soil from December to April raises erosion risk.",
                            "needs_local_review": True,
                        }
                    ],
                    "needs_local_review": True,
                },
                {
                    "id": "maize_beans",
                    "name": "Maize, then black beans",
                    "is_current": False,
                    "sequence": ["maize", "black_beans"],
                    "overall_score": round(min(0.95, 0.62 + 0.08 * water_w), 2),
                    "scores": {
                        "water_use": 0.6,
                        "income": 0.7,
                        "soil_structure": 0.6,
                        "forage_value": 0.2,
                        "nitrogen_fixing": 0.9,
                        "erosion_reduction": 0.6,
                        "market_suitability": 0.7,
                    },
                    "uncertainty": {"low": 0.52, "high": 0.76},
                    "why": [
                        "Beans fix atmospheric nitrogen for the next maize season.",
                        "Shortens the bare-field period.",
                    ],
                    "evidence": [
                        {
                            "statement": "Legumes fix atmospheric nitrogen (crop traits table v1).",
                            "source": "crop_traits",
                        }
                    ],
                    "benefits": ["Lower synthetic nitrogen need.", "Longer soil cover."],
                    "gaps": ["Late-season rainfall is uncertain under El Nino."],
                    "risks": [
                        {
                            "description": "Late-sown beans may face dry spells before pod fill.",
                            "needs_local_review": True,
                        }
                    ],
                    "needs_local_review": True,
                },
                {
                    "id": "maize_cover_crop",
                    "name": "Maize, then a cover crop",
                    "is_current": False,
                    "sequence": ["maize", "cover_crop"],
                    "overall_score": round(min(0.95, 0.56 + 0.1 * erosion_w), 2),
                    "scores": {
                        "water_use": 0.7,
                        "income": 0.4,
                        "soil_structure": 0.8,
                        "forage_value": 0.6,
                        "nitrogen_fixing": 0.6,
                        "erosion_reduction": 0.9,
                        "market_suitability": 0.3,
                    },
                    "uncertainty": {"low": 0.47, "high": 0.72},
                    "why": [
                        "Keeps soil covered through the dry season.",
                        "Matches priority weight on erosion reduction.",
                    ],
                    "evidence": [
                        {
                            "statement": (
                                "Heavy rain events (>50 mm/day) drive topsoil loss on bare slopes."
                            ),
                            "source": "nasa_power_chirps",
                        }
                    ],
                    "benefits": ["Reduced erosion risk.", "Improved soil organic matter."],
                    "gaps": ["Local cover-crop seed cost and availability not verified."],
                    "risks": [
                        {
                            "description": "Cover crop generates no direct cash income.",
                            "needs_local_review": True,
                        }
                    ],
                    "needs_local_review": True,
                },
            ],
            "provenance": {
                "model_version": "fixture-0.1.0",
                "data_versions": {
                    "insivumeh_daily": "2026-11-14",
                    "enso_monthly": "2026-11",
                    "crop_traits": "v1",
                },
                "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            },
        }


class HttpMLClient:
    """HTTP client for ml-service with timeout and single bounded retry."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post_json("/v1/simulate", payload)

    def score_rotations(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post_json("/v1/rotations/score", payload)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for _attempt in range(2):
            req = urllib.request.Request(  # noqa: S310
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
                    parsed: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
                    return parsed
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
        raise ProblemError(
            503,
            "service_unavailable",
            "ML service is currently unavailable",
            detail=type(last_error).__name__ if last_error else None,
        )
