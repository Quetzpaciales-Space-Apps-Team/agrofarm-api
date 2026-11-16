"""Domain models for ENSO series, scenario simulation, and rotation recommendations."""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core_api.domain.problem import ProblemError

EnsoPhase = Literal["el_nino", "la_nina", "neutral"]

DISCLAIMER_TEXT = "This tool supports decisions. It does not replace farmers or local agronomists."


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rainfall_change_pct: float = Field(default=0.0, ge=-80.0, le=100.0)
    temperature_change_c: float = Field(default=0.0, ge=-5.0, le=8.0)
    enso_phase: EnsoPhase = "neutral"


class SimulationRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farm_id: uuid.UUID
    crop: str = Field(min_length=1, max_length=60)
    scenario: ScenarioInput


class RecommendationRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: ScenarioInput = Field(default_factory=ScenarioInput)


@dataclass(frozen=True, slots=True)
class RecommendationRecord:
    id: uuid.UUID
    farm_id: uuid.UUID
    model_version: str
    data_versions: dict[str, str]
    input_hash: str
    payload: dict[str, Any]
    created_at: datetime


def compute_input_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_simulation_response(
    data: dict[str, Any], *, input_hash: str | None = None
) -> dict[str, Any]:
    """Ensure simulation response has ordered quantiles (p10 <= p50 <= p90) and provenance."""
    for key in ("baseline", "scenario"):
        q = data.get(key)
        if not isinstance(q, dict) or not all(k in q for k in ("p10", "p50", "p90")):
            raise ProblemError(503, "invalid_ml_response", f"Missing quantiles in {key}")
        if not (q["p10"] <= q["p50"] <= q["p90"]):
            raise ProblemError(503, "invalid_ml_response", f"Unordered quantiles in {key}")
    prov = data.get("provenance")
    if not isinstance(prov, dict) or not prov.get("model_version") or "data_versions" not in prov:
        raise ProblemError(503, "invalid_ml_response", "Missing provenance in simulation response")
    prov.setdefault("model_name", "agrofarm-yield-anomaly")
    prov.setdefault("input_hash", input_hash or compute_input_hash(data))
    data.setdefault("disclaimer", DISCLAIMER_TEXT)
    return data


def map_and_validate_recommendations(
    *,
    rec_id: uuid.UUID,
    farm_id: uuid.UUID,
    raw: dict[str, Any],
    input_hash: str | None = None,
) -> dict[str, Any]:
    """Map ml-service rotation scoring output and enforce all required blocks."""
    strategies = raw.get("strategies")
    if not isinstance(strategies, list) or len(strategies) < 3:
        raise ProblemError(
            503, "invalid_ml_response", "ML service must return at least 3 rotation strategies."
        )

    has_current = False
    required_blocks = (
        "why",
        "evidence",
        "benefits",
        "gaps",
        "risks",
        "needs_local_review",
        "uncertainty",
        "scores",
    )
    for strat in strategies:
        if not isinstance(strat, dict):
            raise ProblemError(503, "invalid_ml_response", "Invalid strategy item.")
        for field in required_blocks:
            val = strat.get(field)
            if val is None or (isinstance(val, list | dict) and len(val) == 0):
                raise ProblemError(
                    503,
                    "invalid_ml_response",
                    f"Strategy '{strat.get('id', 'unknown')}' missing required field '{field}'.",
                )
        if strat.get("is_current") is True:
            has_current = True

    if not has_current:
        raise ProblemError(
            503, "invalid_ml_response", "Strategies must include the current farm rotation."
        )

    prov = raw.get("provenance")
    if not isinstance(prov, dict) or not prov.get("model_version") or "data_versions" not in prov:
        raise ProblemError(503, "invalid_ml_response", "Missing provenance in recommendations.")
    prov.setdefault("model_name", "agrofarm-rotation-ranker")
    prov.setdefault("input_hash", input_hash or compute_input_hash(raw))

    return {
        "id": str(rec_id),
        "farm_id": str(farm_id),
        "disclaimer": raw.get("disclaimer") or DISCLAIMER_TEXT,
        "strategies": strategies,
        "provenance": prov,
    }
