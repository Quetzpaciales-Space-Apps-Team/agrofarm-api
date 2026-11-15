"""Real NDVI inference without the fixed-rule or cached simulation fallback."""

import math
from typing import Any

from core_api.clients.ml import HttpMLClient
from core_api.domain.problem import ProblemError


def validate_outlook(result: Any) -> dict[str, Any]:
    try:
        valid = (
            result["target"] == "seasonal_peak_ndvi_anomaly_pct"
            and result["unit"] == "%"
            and result["needs_local_review"] is True
            and result["validation"]["acceptance_rule_met"] is False
            and result["provenance"]["evaluation_verdict"] == "no_skill_over_climatology"
            and result["provenance"]["model_version"] == "ndvi-vegetation-outlook-0.1.0"
            and bool(result["limitations"])
            and bool(result["reference_cell"]["cell_id"])
        )
        for key in ["baseline", "scenario"]:
            q = [result[key][name] for name in ["p10", "p50", "p90"]]
            valid = (
                valid
                and all(isinstance(v, int | float) and math.isfinite(v) for v in q)
                and q == sorted(q)
            )
        valid = valid and all(
            isinstance(item["feature"], str) and math.isfinite(item["contribution"])
            for item in result["attributions"]
        )
    except (KeyError, TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        raise ProblemError(502, "invalid_ml_response", "Invalid vegetation outlook response")
    parsed: dict[str, Any] = result
    return parsed


class HttpVegetationClient(HttpMLClient):
    def simulate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return validate_outlook(self._post_json("/v1/vegetation/simulate", payload))
