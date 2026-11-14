"""Pydantic v2 request and response schemas matching docs/contract/openapi.yaml."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

UserRole = Literal["farmer", "agronomist", "admin"]
EnsoPhase = Literal["el_nino", "la_nina", "neutral"]
SearchEntityType = Literal["crop", "place", "farm"]
StrictNumber = StrictFloat | StrictInt


def _validate_json_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not a valid integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError("Input should be a valid integer")


JsonSchemaInt = Annotated[int, BeforeValidator(_validate_json_int)]


class PaginationMeta(BaseModel):
    limit: int = Field(ge=1, le=100)
    next_cursor: str | None = None


class DatasetVersionRef(BaseModel):
    dataset_id: str
    version: str
    source: str
    date_range: str
    spatial_resolution: str
    is_preliminary: bool = False


class Provenance(BaseModel):
    model_name: str
    model_version: str
    data_versions: list[DatasetVersionRef] = Field(min_length=1)
    input_hash: str
    generated_at: datetime


class QuantileUncertainty(BaseModel):
    p10: float
    p50: float
    p90: float
    unit: str
    confidence_note: str


class RegisterRequest(BaseModel):
    email: StrictStr = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: StrictStr = Field(min_length=10, max_length=72)
    full_name: StrictStr = Field(min_length=1, max_length=120)
    role: UserRole = "farmer"


class LoginRequest(BaseModel):
    email: StrictStr = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: StrictStr = Field(min_length=1, max_length=72)


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105
    expires_in: int = 900
    user: UserProfile


class GeoPoint(BaseModel):
    latitude: StrictNumber = Field(ge=-90, le=90)
    longitude: StrictNumber = Field(ge=-180, le=180)


class GeoPolygon(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[
        Annotated[
            list[Annotated[list[StrictNumber], Field(min_length=2, max_length=2)]],
            Field(min_length=4),
        ]
    ] = Field(min_length=1)


class Farm(BaseModel):
    id: str
    name: str
    department: str
    municipality: str
    reference_point: GeoPoint
    polygon: GeoPolygon | None = None
    area_ha: float = Field(ge=0.01)
    elevation_m: float
    current_rotation: list[str] = Field(min_length=1)
    station_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateFarmRequest(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=120)
    department: StrictStr = Field(min_length=1, max_length=80)
    municipality: StrictStr = Field(min_length=1, max_length=80)
    reference_point: GeoPoint
    polygon: GeoPolygon | None = None
    area_ha: StrictNumber = Field(ge=0.01, le=100000)
    elevation_m: StrictNumber = 1502.0
    current_rotation: list[Annotated[StrictStr, Field(min_length=1)]] = Field(
        min_length=1, max_length=10
    )


class UpdateFarmRequest(BaseModel):
    name: StrictStr | None = Field(default=None, min_length=1, max_length=120)
    area_ha: StrictNumber | None = Field(default=None, ge=0.01, le=100000)
    current_rotation: list[Annotated[StrictStr, Field(min_length=1)]] | None = Field(
        default=None, min_length=1, max_length=10
    )
    polygon: GeoPolygon | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in ("name", "area_ha", "current_rotation"):
                if key in data and data[key] is None:
                    raise ValueError(f"{key} cannot be null")
        return data


class FarmListResponse(BaseModel):
    items: list[Farm]
    pagination: PaginationMeta


class UploadRowError(BaseModel):
    row: int = Field(ge=1)
    column: str
    code: str
    message: str


class FarmUpload(BaseModel):
    id: str
    farm_id: str
    filename: str
    format: Literal["csv", "geojson"]
    status: Literal["validated", "validated_with_errors", "rejected"]
    total_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    row_errors: list[UploadRowError]
    created_at: datetime


class CreateFarmUploadRequest(BaseModel):
    filename: StrictStr = Field(min_length=1, max_length=255)
    format: Literal["csv", "geojson"]
    content: StrictStr = Field(min_length=1, max_length=100000)


class FarmUploadListResponse(BaseModel):
    items: list[FarmUpload]
    pagination: PaginationMeta


class PriorityWeights(BaseModel):
    yield_stability: StrictNumber = Field(ge=0, le=1)
    soil_health: StrictNumber = Field(ge=0, le=1)
    water_efficiency: StrictNumber = Field(ge=0, le=1)
    income_diversification: StrictNumber = Field(ge=0, le=1)
    low_input_cost: StrictNumber = Field(ge=0, le=1)


class FarmPriorities(BaseModel):
    farm_id: str
    weights: PriorityWeights
    irrigation_available: bool
    max_fallow_days: int = Field(ge=0, le=365)
    excluded_crops: list[str]
    notes: str = ""
    updated_at: datetime


class FarmPrioritiesUpdate(BaseModel):
    weights: PriorityWeights
    irrigation_available: StrictBool
    max_fallow_days: JsonSchemaInt = Field(ge=0, le=365)
    excluded_crops: list[StrictStr] = Field(default_factory=list)
    notes: StrictStr = Field(default="", max_length=500)


class BareFieldPeriod(BaseModel):
    start_date: date
    end_date: date
    duration_days: int = Field(ge=1)
    mean_ndvi: float = Field(ge=-1, le=1)
    erosion_exposure: Literal["low", "moderate", "high"]
    explanation: str


class VulnerableSeason(BaseModel):
    season_name: str
    months: str
    primary_hazard: Literal[
        "dry_spell_canicula", "extreme_rainfall", "cold_night_frost", "heat_stress"
    ]
    enso_sensitivity: str
    recommended_watch: str


class FarmInsights(BaseModel):
    farm_id: str
    bare_field_periods: list[BareFieldPeriod]
    vulnerable_seasons: list[VulnerableSeason]
    provenance: Provenance
    disclaimer: str


class LayerLegendStop(BaseModel):
    value: float
    color: str
    label: str


class LayerLegend(BaseModel):
    unit: str
    palette_name: str
    color_blind_safe: bool
    stops: list[LayerLegendStop] = Field(min_length=2)


class LayerSourceBlock(BaseModel):
    provider: str
    dataset_id: str
    version: str
    spatial_resolution: str
    date_range: str
    measurement_type: Literal[
        "satellite_derived", "ground_station", "reanalysis_model", "soil_prediction"
    ]
    limitation_note: str


class MapLayer(BaseModel):
    id: str
    name: str
    category: Literal["climate", "soil", "vegetation", "terrain", "water_stress"]
    description: str
    tile_url_template: str
    legend: LayerLegend
    source: LayerSourceBlock


class LayerListResponse(BaseModel):
    items: list[MapLayer]
    pagination: PaginationMeta


class EnsoMonthPoint(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    oni_c: float
    roni_c: float
    phase: EnsoPhase
    rainfall_anomaly_note: str


class EnsoSeriesResponse(BaseModel):
    threshold_c: float
    items: list[EnsoMonthPoint]
    provenance: Provenance
    disclaimer: str


class ScenarioSimulationRequest(BaseModel):
    farm_id: StrictStr = Field(min_length=1)
    crop_id: StrictStr = Field(min_length=1)
    season_start: date = date(2025, 5, 1)
    season_end: date = date(2025, 10, 31)
    rainfall_change_pct: StrictNumber = Field(ge=-60, le=60)
    temperature_change_c: StrictNumber = Field(ge=-4, le=6)
    enso_phase: EnsoPhase

    @field_validator("season_start", "season_end", mode="before")
    @classmethod
    def _require_iso_date_str(cls, value: Any) -> Any:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError("date must be an ISO 8601 string (YYYY-MM-DD)")
        return value


class FeatureAttribution(BaseModel):
    feature: str
    shap_value: float
    direction: Literal["positive", "negative", "neutral"]
    explanation: str


class ScenarioTimelineStep(BaseModel):
    period: str
    baseline_p50: float
    scenario_p10: float
    scenario_p50: float
    scenario_p90: float
    water_balance_mm: float


class ScenarioSimulationResponse(BaseModel):
    farm_id: str
    crop_id: str
    metric_name: str
    baseline: QuantileUncertainty
    scenario: QuantileUncertainty
    out_of_training_range: bool
    range_warning: str | None = None
    top_attributions: list[FeatureAttribution]
    timeline: list[ScenarioTimelineStep]
    provenance: Provenance
    disclaimer: str


class RecommendationRequest(BaseModel):
    enso_phase: EnsoPhase = "la_nina"
    rainfall_change_pct: StrictNumber = Field(default=0.0, ge=-60, le=60)
    temperature_change_c: StrictNumber = Field(default=0.0, ge=-4, le=6)


class StrategyScores(BaseModel):
    overall: float = Field(ge=0, le=100)
    yield_stability: float = Field(ge=0, le=100)
    soil_health: float = Field(ge=0, le=100)
    water_efficiency: float = Field(ge=0, le=100)
    income_diversification: float = Field(ge=0, le=100)
    low_input_cost: float = Field(ge=0, le=100)


class RotationStrategy(BaseModel):
    id: str
    name: str
    is_current_rotation: bool
    sequence: list[str] = Field(min_length=1)
    why: list[str] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    benefits: list[str] = Field(min_length=1)
    gaps: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    needs_local_review: bool
    uncertainty: QuantileUncertainty
    scores: StrategyScores


class Recommendation(BaseModel):
    id: str
    farm_id: str
    scenario_summary: str
    strategies: list[RotationStrategy] = Field(min_length=3)
    provenance: Provenance
    disclaimer: str


class SearchResultItem(BaseModel):
    id: str
    type: SearchEntityType
    name: str
    aliases: list[str]
    similarity: float = Field(ge=0, le=1)
    summary: str


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem] = Field(max_length=20)
    pagination: PaginationMeta
