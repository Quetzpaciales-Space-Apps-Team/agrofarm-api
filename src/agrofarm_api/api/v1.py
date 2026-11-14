"""Contract stub routers for /v1/* endpoints (BE-002)."""

import copy
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from agrofarm_api.api.schemas import (
    AuthTokenResponse,
    CreateFarmRequest,
    CreateFarmUploadRequest,
    EnsoSeriesResponse,
    Farm,
    FarmInsights,
    FarmListResponse,
    FarmPriorities,
    FarmPrioritiesUpdate,
    FarmUpload,
    FarmUploadListResponse,
    LayerListResponse,
    LoginRequest,
    PaginationMeta,
    Recommendation,
    RecommendationRequest,
    RegisterRequest,
    ScenarioSimulationRequest,
    ScenarioSimulationResponse,
    SearchEntityType,
    SearchResponse,
    UpdateFarmRequest,
    UserProfile,
)
from agrofarm_api.middleware.error_handler import ProblemError
from agrofarm_api.stubs import (
    DISCLAIMER_TEXT,
    STUB_ENSO_SERIES,
    STUB_FARMS,
    STUB_INSIGHTS,
    STUB_LAYERS,
    STUB_PRIORITIES,
    STUB_PROVENANCE,
    STUB_RECOMMENDATION,
    STUB_SEARCH_CATALOG,
    STUB_SIMULATION,
    STUB_UPLOADS,
    STUB_USER,
)


def _mark_stub(response: Response) -> None:
    response.headers["X-Stub"] = "true"


router = APIRouter(prefix="/v1", dependencies=[Depends(_mark_stub)])

FarmIdParam = Annotated[str, Path(min_length=1, max_length=64)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
CursorQuery = Annotated[str | None, Query(max_length=128)]
IdempotencyHeader = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=1, max_length=128)
]


@router.post("/auth/register", status_code=201, response_model=AuthTokenResponse, tags=["auth"])
def register_user(
    payload: RegisterRequest,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = idempotency_key
    user = {
        **STUB_USER,
        "email": payload.email.lower(),
        "full_name": payload.full_name,
        "role": payload.role,
    }
    return {
        "access_token": "stub-jwt-access-token-guatemala",
        "token_type": "Bearer",
        "expires_in": 900,
        "user": user,
    }


@router.post("/auth/login", response_model=AuthTokenResponse, tags=["auth"])
def login_user(payload: LoginRequest) -> dict[str, Any]:
    user = {**STUB_USER, "email": payload.email.lower()}
    return {
        "access_token": "stub-jwt-access-token-guatemala",
        "token_type": "Bearer",
        "expires_in": 900,
        "user": user,
    }


@router.post("/auth/refresh", response_model=AuthTokenResponse, tags=["auth"])
def refresh_access_token() -> dict[str, Any]:
    return {
        "access_token": "stub-jwt-access-token-rotated",
        "token_type": "Bearer",
        "expires_in": 900,
        "user": STUB_USER,
    }


@router.post("/auth/logout", status_code=204, tags=["auth"])
def logout_user() -> Response:
    return Response(status_code=204, headers={"X-Stub": "true"})


@router.get("/me", response_model=UserProfile, tags=["auth"])
def get_current_user() -> dict[str, Any]:
    return STUB_USER


@router.get("/farms", response_model=FarmListResponse, tags=["farms"])
def list_farms(
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> dict[str, Any]:
    _ = cursor
    items = STUB_FARMS[:limit]
    return {
        "items": items,
        "pagination": PaginationMeta(limit=limit, next_cursor=None).model_dump(),
    }


@router.post("/farms", status_code=201, response_model=Farm, tags=["farms"])
def create_farm(
    payload: CreateFarmRequest,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = idempotency_key
    base = copy.deepcopy(STUB_FARMS[0])
    base.update(
        {
            "id": "farm_gt_created_001",
            "name": payload.name,
            "department": payload.department,
            "municipality": payload.municipality,
            "reference_point": payload.reference_point.model_dump(),
            "polygon": payload.polygon.model_dump() if payload.polygon else None,
            "area_ha": payload.area_ha,
            "elevation_m": payload.elevation_m,
            "current_rotation": payload.current_rotation,
        }
    )
    return base


@router.get("/farms/{id}", response_model=Farm, tags=["farms"])
def get_farm(id: FarmIdParam) -> dict[str, Any]:
    for farm in STUB_FARMS:
        if farm["id"] == id:
            return farm
    return {**STUB_FARMS[0], "id": id}


@router.patch("/farms/{id}", response_model=Farm, tags=["farms"])
def update_farm(id: FarmIdParam, payload: UpdateFarmRequest) -> dict[str, Any]:
    updated = copy.deepcopy(STUB_FARMS[0])
    updated["id"] = id
    if payload.name is not None:
        updated["name"] = payload.name
    if payload.area_ha is not None:
        updated["area_ha"] = payload.area_ha
    if payload.current_rotation is not None:
        updated["current_rotation"] = payload.current_rotation
    if payload.polygon is not None:
        updated["polygon"] = payload.polygon.model_dump()
    return updated


@router.delete("/farms/{id}", status_code=204, tags=["farms"])
def delete_farm(id: FarmIdParam) -> Response:
    _ = id
    return Response(status_code=204, headers={"X-Stub": "true"})


@router.get("/farms/{id}/uploads", response_model=FarmUploadListResponse, tags=["farms"])
def list_farm_uploads(
    id: FarmIdParam,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> dict[str, Any]:
    _ = cursor
    items = [{**u, "farm_id": id} for u in STUB_UPLOADS[:limit]]
    return {
        "items": items,
        "pagination": PaginationMeta(limit=limit, next_cursor=None).model_dump(),
    }


@router.post("/farms/{id}/uploads", status_code=201, response_model=FarmUpload, tags=["farms"])
def create_farm_upload(
    id: FarmIdParam,
    payload: CreateFarmUploadRequest,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = idempotency_key
    base = copy.deepcopy(STUB_UPLOADS[0])
    base["id"] = "upl_gt_created_001"
    base["farm_id"] = id
    base["filename"] = payload.filename
    base["format"] = payload.format
    return base


@router.get("/farms/{id}/priorities", response_model=FarmPriorities, tags=["farms"])
def get_farm_priorities(id: FarmIdParam) -> dict[str, Any]:
    return {**STUB_PRIORITIES, "farm_id": id}


@router.put("/farms/{id}/priorities", response_model=FarmPriorities, tags=["farms"])
def update_farm_priorities(
    id: FarmIdParam,
    payload: FarmPrioritiesUpdate,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = idempotency_key
    return {
        "farm_id": id,
        "weights": payload.weights.model_dump(),
        "irrigation_available": payload.irrigation_available,
        "max_fallow_days": payload.max_fallow_days,
        "excluded_crops": payload.excluded_crops,
        "notes": payload.notes,
        "updated_at": STUB_PRIORITIES["updated_at"],
    }


@router.get("/farms/{id}/insights", response_model=FarmInsights, tags=["farms"])
def get_farm_insights(id: FarmIdParam) -> dict[str, Any]:
    return {**STUB_INSIGHTS, "farm_id": id}


@router.get("/layers", response_model=LayerListResponse, tags=["layers"])
def list_layers(
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> dict[str, Any]:
    _ = cursor
    items = STUB_LAYERS[:limit]
    return {
        "items": items,
        "pagination": PaginationMeta(limit=limit, next_cursor=None).model_dump(),
    }


@router.get("/climate/enso", response_model=EnsoSeriesResponse, tags=["climate"])
def get_enso_series(
    start_month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
    end_month: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")] = None,
) -> dict[str, Any]:
    items = STUB_ENSO_SERIES
    if start_month:
        items = [p for p in items if p["month"] >= start_month]
    if end_month:
        items = [p for p in items if p["month"] <= end_month]
    if not items:
        items = STUB_ENSO_SERIES
    return {
        "threshold_c": 0.5,
        "items": items,
        "provenance": STUB_PROVENANCE,
        "disclaimer": DISCLAIMER_TEXT,
    }


@router.post("/scenarios/simulate", response_model=ScenarioSimulationResponse, tags=["scenarios"])
def simulate_scenario(
    payload: ScenarioSimulationRequest,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = idempotency_key
    out_of_range = abs(payload.rainfall_change_pct) > 45 or abs(payload.temperature_change_c) > 3.5
    warning = (
        "Scenario inputs exceed historical 1995-2025 INSIVUMEH observation bounds; "
        "treat extrapolation with caution."
        if out_of_range
        else None
    )
    return {
        **STUB_SIMULATION,
        "farm_id": payload.farm_id,
        "crop_id": payload.crop_id,
        "out_of_training_range": out_of_range,
        "range_warning": warning,
    }


@router.post("/farms/{id}/recommendations", response_model=Recommendation, tags=["farms"])
async def create_farm_recommendations(
    request: Request,
    id: FarmIdParam,
    payload: RecommendationRequest | None = None,
    idempotency_key: IdempotencyHeader = None,
) -> dict[str, Any]:
    _ = payload, idempotency_key
    if (await request.body()).strip() == b"null":
        raise ProblemError(422, "validation_error", "Validation Error", "Body cannot be null.")
    return {
        **STUB_RECOMMENDATION,
        "farm_id": id,
    }


@router.get("/search", response_model=SearchResponse, tags=["search"])
def search_catalog(
    q: Annotated[str, Query(min_length=2, max_length=100)],
    type: Annotated[SearchEntityType | None, Query()] = None,
    limit: LimitQuery = 20,
    cursor: CursorQuery = None,
) -> dict[str, Any]:
    _ = cursor
    needle = q.strip().lower()
    filtered = [item for item in STUB_SEARCH_CATALOG if type is None or item["type"] == type]
    matched = [
        item
        for item in filtered
        if needle in str(item["name"]).lower()
        or any(needle in alias.lower() for alias in item["aliases"])
    ]
    results = (matched or filtered)[: min(limit, 20)]
    return {
        "query": q,
        "items": results,
        "pagination": PaginationMeta(limit=min(limit, 20), next_cursor=None).model_dump(),
    }
