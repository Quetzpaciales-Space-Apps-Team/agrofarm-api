"""Domain models and validation for farms, polygons (EPSG:4326), and farmer priorities."""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core_api.domain.problem import ProblemError

WaterAvailability = Literal["low", "medium", "high"]
EquipmentType = Literal["hand_tools", "animal_traction", "tractor", "irrigation"]


class PolygonModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["Polygon"]
    coordinates: list[list[list[float]]] = Field(min_length=1)


class FarmCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    boundary: PolygonModel
    current_rotation: list[str] = Field(default_factory=list, max_length=12)


class FarmUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    boundary: PolygonModel | None = None
    current_rotation: list[str] | None = Field(default=None, max_length=12)


class PriorityWeightsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    water_use: float = Field(ge=0.0, le=1.0)
    income: float = Field(ge=0.0, le=1.0)
    soil_structure: float = Field(ge=0.0, le=1.0)
    forage_value: float = Field(ge=0.0, le=1.0)
    nitrogen_fixing: float = Field(ge=0.0, le=1.0)
    erosion_reduction: float = Field(ge=0.0, le=1.0)
    market_suitability: float = Field(ge=0.0, le=1.0)


class PriorityConstraintsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    water_availability: WaterAvailability
    equipment: list[EquipmentType] = Field(max_length=10)


class PrioritiesModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weights: PriorityWeightsModel
    constraints: PriorityConstraintsModel


@dataclass(frozen=True, slots=True)
class FarmRecord:
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    boundary: dict[str, Any]
    area_ha: float
    centroid_lat: float
    centroid_lon: float
    current_rotation: list[str]
    created_at: datetime


def default_priorities() -> dict[str, Any]:
    return {
        "weights": {
            "water_use": 0.5,
            "income": 0.5,
            "soil_structure": 0.5,
            "forage_value": 0.5,
            "nitrogen_fixing": 0.5,
            "erosion_reduction": 0.5,
            "market_suitability": 0.5,
        },
        "constraints": {
            "water_availability": "medium",
            "equipment": [],
        },
    }


def _ring_area_ha(ring: list[list[float]]) -> tuple[float, float, float]:
    """Compute approximate geodesic area in hectares and centroid (lat, lon) via shoelace."""
    lons = [pt[0] for pt in ring[:-1]]
    lats = [pt[1] for pt in ring[:-1]]
    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)

    meters_per_deg_lat = 111_320.0
    meters_per_deg_lon = 111_320.0 * math.cos(math.radians(centroid_lat))

    area_m2 = 0.0
    for i in range(len(ring) - 1):
        x1 = ring[i][0] * meters_per_deg_lon
        y1 = ring[i][1] * meters_per_deg_lat
        x2 = ring[i + 1][0] * meters_per_deg_lon
        y2 = ring[i + 1][1] * meters_per_deg_lat
        area_m2 += (x1 * y2) - (x2 * y1)
    area_ha = abs(area_m2) / 2.0 / 10_000.0
    return round(area_ha, 2), round(centroid_lat, 6), round(centroid_lon, 6)


def validate_polygon(boundary: PolygonModel) -> tuple[float, float, float]:
    """Validate EPSG:4326 GeoJSON Polygon and return (area_ha, centroid_lat, centroid_lon)."""
    errors: list[dict[str, str]] = []
    for ring_idx, ring in enumerate(boundary.coordinates):
        if len(ring) < 4:
            errors.append(
                {
                    "field": f"boundary.coordinates.{ring_idx}",
                    "message": "Polygon ring must have at least 4 positions.",
                }
            )
            continue
        for pos_idx, pos in enumerate(ring):
            if len(pos) != 2:
                errors.append(
                    {
                        "field": f"boundary.coordinates.{ring_idx}.{pos_idx}",
                        "message": "Position must have exactly [longitude, latitude].",
                    }
                )
                continue
            lon, lat = pos
            if not math.isfinite(lon) or lon < -180.0 or lon > 180.0:
                errors.append(
                    {
                        "field": f"boundary.coordinates.{ring_idx}.{pos_idx}",
                        "message": "Longitude must be between -180 and 180.",
                    }
                )
            if not math.isfinite(lat) or lat < -90.0 or lat > 90.0:
                errors.append(
                    {
                        "field": f"boundary.coordinates.{ring_idx}.{pos_idx}",
                        "message": "Latitude must be between -90 and 90.",
                    }
                )
        if ring[0] != ring[-1]:
            errors.append(
                {
                    "field": f"boundary.coordinates.{ring_idx}",
                    "message": "Polygon ring must be closed (first and last position must match).",
                }
            )

    if errors:
        raise ProblemError(
            422,
            "validation_error",
            "Invalid polygon geometry",
            extra={"errors": errors},
        )

    area_ha, centroid_lat, centroid_lon = _ring_area_ha(boundary.coordinates[0])
    if area_ha <= 0.0:
        raise ProblemError(
            422,
            "validation_error",
            "Invalid polygon geometry",
            extra={
                "errors": [
                    {"field": "boundary.coordinates.0", "message": "Polygon area must be > 0."}
                ]
            },
        )
    return area_ha, centroid_lat, centroid_lon
