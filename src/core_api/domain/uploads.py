"""Domain models and DEC-005 validation for farm CSV and GeoJSON uploads."""

import csv
import io
import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

UploadFormat = Literal["csv", "geojson"]
UploadStatus = Literal["accepted", "accepted_with_errors", "rejected"]

REQUIRED_CSV_COLUMNS = (
    "parcel_id",
    "season_year",
    "crop",
    "sowing_date",
    "area_ha",
    "latitude",
    "longitude",
)
REQUIRED_GEOJSON_PROPS = ("parcel_id", "season_year", "crop", "sowing_date", "area_ha")
ALLOWED_IRRIGATION = frozenset({"rainfed", "drip", "sprinkler", "furrow"})
PARCEL_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class RowErrorItem:
    row: int
    column: str | None
    message: str


@dataclass(frozen=True, slots=True)
class UploadRecord:
    id: uuid.UUID
    farm_id: uuid.UUID
    filename: str
    format: UploadFormat
    status: UploadStatus
    rows_total: int
    rows_accepted: int
    errors: list[RowErrorItem]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ParsedUpload:
    format: UploadFormat
    status: UploadStatus
    rows_total: int
    rows_accepted: int
    errors: list[RowErrorItem]
    accepted_rows: list[dict[str, Any]]


def escape_csv_cell(value: str) -> str:
    """Escape formula-injection prefixes (=, +, -, @) for any CSV produced by the API."""
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def _parse_iso_date(raw: Any, column: str, row_num: int, errors: list[RowErrorItem]) -> date | None:
    if raw is None or str(raw).strip() == "":
        return None
    text = str(raw).strip()
    if not ISO_DATE_RE.match(text):
        errors.append(RowErrorItem(row=row_num, column=column, message="Date must be YYYY-MM-DD."))
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        errors.append(RowErrorItem(row=row_num, column=column, message="Invalid calendar date."))
        return None


def _parse_float(
    raw: Any,
    column: str,
    row_num: int,
    errors: list[RowErrorItem],
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    strict_gt: float | None = None,
) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        errors.append(RowErrorItem(row=row_num, column=column, message="Must be a valid number."))
        return None
    if not math.isfinite(val):
        errors.append(RowErrorItem(row=row_num, column=column, message="Must be a finite number."))
        return None
    if strict_gt is not None and val <= strict_gt:
        errors.append(
            RowErrorItem(row=row_num, column=column, message=f"Must be greater than {strict_gt}.")
        )
        return None
    if min_val is not None and val < min_val:
        errors.append(RowErrorItem(row=row_num, column=column, message=f"Must be >= {min_val}."))
        return None
    if max_val is not None and val > max_val:
        errors.append(RowErrorItem(row=row_num, column=column, message=f"Must be <= {max_val}."))
        return None
    return val


def _validate_row_fields(
    raw: dict[str, Any], row_num: int, *, require_coords: bool
) -> tuple[dict[str, Any] | None, list[RowErrorItem]]:
    errors: list[RowErrorItem] = []

    parcel_id = str(raw.get("parcel_id") or "").strip()
    if not PARCEL_ID_RE.match(parcel_id):
        errors.append(
            RowErrorItem(
                row=row_num,
                column="parcel_id",
                message="Required; 1-64 chars matching [a-zA-Z0-9_-].",
            )
        )

    year_raw = raw.get("season_year")
    season_year: int | None = None
    try:
        season_year = int(str(year_raw).strip())
        if season_year < 1980 or season_year > 2030:
            errors.append(
                RowErrorItem(
                    row=row_num,
                    column="season_year",
                    message="Must be between 1980 and 2030.",
                )
            )
    except (TypeError, ValueError):
        errors.append(
            RowErrorItem(row=row_num, column="season_year", message="Must be an integer year.")
        )

    crop = str(raw.get("crop") or "").strip().lower()
    if not crop:
        errors.append(RowErrorItem(row=row_num, column="crop", message="Crop is required."))

    sowing_raw = raw.get("sowing_date")
    if sowing_raw is None or str(sowing_raw).strip() == "":
        errors.append(
            RowErrorItem(row=row_num, column="sowing_date", message="sowing_date is required.")
        )
        sowing_date = None
    else:
        sowing_date = _parse_iso_date(sowing_raw, "sowing_date", row_num, errors)

    harvest_date = _parse_iso_date(raw.get("harvest_date"), "harvest_date", row_num, errors)
    if sowing_date and harvest_date and harvest_date < sowing_date:
        errors.append(
            RowErrorItem(
                row=row_num,
                column="harvest_date",
                message="harvest_date must be >= sowing_date.",
            )
        )

    area_ha = _parse_float(
        raw.get("area_ha"), "area_ha", row_num, errors, strict_gt=0.0, max_val=100000.0
    )
    if area_ha is None and (raw.get("area_ha") is None or str(raw.get("area_ha")).strip() == ""):
        errors.append(RowErrorItem(row=row_num, column="area_ha", message="area_ha is required."))

    lat = _parse_float(
        raw.get("latitude"), "latitude", row_num, errors, min_val=-90.0, max_val=90.0
    )
    lon = _parse_float(
        raw.get("longitude"), "longitude", row_num, errors, min_val=-180.0, max_val=180.0
    )
    if require_coords:
        if lat is None and (raw.get("latitude") is None or str(raw.get("latitude")).strip() == ""):
            errors.append(
                RowErrorItem(row=row_num, column="latitude", message="latitude is required.")
            )
        if lon is None and (
            raw.get("longitude") is None or str(raw.get("longitude")).strip() == ""
        ):
            errors.append(
                RowErrorItem(row=row_num, column="longitude", message="longitude is required.")
            )

    yield_kg_ha = _parse_float(raw.get("yield_kg_ha"), "yield_kg_ha", row_num, errors, min_val=0.0)
    soil_ph = _parse_float(
        raw.get("soil_ph"), "soil_ph", row_num, errors, min_val=3.0, max_val=10.0
    )
    soil_om_pct = _parse_float(
        raw.get("soil_om_pct"), "soil_om_pct", row_num, errors, min_val=0.0, max_val=100.0
    )
    soil_n = _parse_float(raw.get("soil_n_mg_kg"), "soil_n_mg_kg", row_num, errors, min_val=0.0)
    soil_p = _parse_float(raw.get("soil_p_mg_kg"), "soil_p_mg_kg", row_num, errors, min_val=0.0)
    soil_k = _parse_float(raw.get("soil_k_mg_kg"), "soil_k_mg_kg", row_num, errors, min_val=0.0)
    rainfall_mm = _parse_float(
        raw.get("rainfall_season_mm"), "rainfall_season_mm", row_num, errors, min_val=0.0
    )

    irrigation_raw = str(raw.get("irrigation") or "").strip().lower()
    if irrigation_raw and irrigation_raw not in ALLOWED_IRRIGATION:
        errors.append(
            RowErrorItem(
                row=row_num,
                column="irrigation",
                message=f"Must be one of {sorted(ALLOWED_IRRIGATION)}.",
            )
        )

    if errors:
        return None, errors

    return {
        "parcel_id": parcel_id,
        "season_year": season_year,
        "crop": crop,
        "sowing_date": sowing_date.isoformat() if sowing_date else None,
        "harvest_date": harvest_date.isoformat() if harvest_date else None,
        "area_ha": area_ha,
        "latitude": lat,
        "longitude": lon,
        "yield_kg_ha": yield_kg_ha,
        "irrigation": irrigation_raw or None,
        "soil_ph": soil_ph,
        "soil_om_pct": soil_om_pct,
        "soil_n_mg_kg": soil_n,
        "soil_p_mg_kg": soil_p,
        "soil_k_mg_kg": soil_k,
        "rainfall_season_mm": rainfall_mm,
        "notes": str(raw.get("notes") or "")[:500] or None,
    }, []


def _status_for(rows_total: int, rows_accepted: int, errors: list[RowErrorItem]) -> UploadStatus:
    if rows_total == 0 or rows_accepted == 0:
        return "rejected"
    if errors:
        return "accepted_with_errors"
    return "accepted"


def validate_csv_upload(content: bytes) -> ParsedUpload:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ParsedUpload(
            format="csv",
            status="rejected",
            rows_total=0,
            rows_accepted=0,
            errors=[RowErrorItem(row=1, column=None, message="File must be UTF-8 encoded.")],
            accepted_rows=[],
        )

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in headers]
    if missing:
        return ParsedUpload(
            format="csv",
            status="rejected",
            rows_total=0,
            rows_accepted=0,
            errors=[
                RowErrorItem(row=1, column=col, message="Missing required column.")
                for col in missing
            ],
            accepted_rows=[],
        )

    all_errors: list[RowErrorItem] = []
    accepted: list[dict[str, Any]] = []
    rows_total = 0
    for idx, row in enumerate(reader, start=1):
        rows_total += 1
        cleaned, row_errors = _validate_row_fields(row, idx, require_coords=True)
        all_errors.extend(row_errors)
        if cleaned is not None:
            accepted.append(cleaned)

    return ParsedUpload(
        format="csv",
        status=_status_for(rows_total, len(accepted), all_errors),
        rows_total=rows_total,
        rows_accepted=len(accepted),
        errors=all_errors,
        accepted_rows=accepted,
    )


def _geometry_centroid(geometry: Any) -> tuple[float, float] | None:
    if not isinstance(geometry, dict):
        return None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon" and isinstance(coords, list) and coords and isinstance(coords[0], list):
        ring = coords[0]
    elif (
        gtype == "MultiPolygon"
        and isinstance(coords, list)
        and coords
        and isinstance(coords[0], list)
        and coords[0]
        and isinstance(coords[0][0], list)
    ):
        ring = coords[0][0]
    else:
        return None

    if len(ring) < 4 or ring[0] != ring[-1]:
        return None
    lons: list[float] = []
    lats: list[float] = []
    for pt in ring[:-1]:
        if not isinstance(pt, list) or len(pt) != 2:
            return None
        lon, lat = pt
        if not isinstance(lon, int | float) or not isinstance(lat, int | float):
            return None
        if lon < -180 or lon > 180 or lat < -90 or lat > 90:
            return None
        lons.append(float(lon))
        lats.append(float(lat))
    return round(sum(lats) / len(lats), 6), round(sum(lons) / len(lons), 6)


def validate_geojson_upload(content: bytes) -> ParsedUpload:
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return ParsedUpload(
            format="geojson",
            status="rejected",
            rows_total=0,
            rows_accepted=0,
            errors=[RowErrorItem(row=1, column=None, message="Invalid UTF-8 JSON.")],
            accepted_rows=[],
        )

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        return ParsedUpload(
            format="geojson",
            status="rejected",
            rows_total=0,
            rows_accepted=0,
            errors=[
                RowErrorItem(
                    row=1, column="type", message="GeoJSON must be a FeatureCollection (EPSG:4326)."
                )
            ],
            accepted_rows=[],
        )

    features = data.get("features")
    if not isinstance(features, list):
        return ParsedUpload(
            format="geojson",
            status="rejected",
            rows_total=0,
            rows_accepted=0,
            errors=[RowErrorItem(row=1, column="features", message="features must be a list.")],
            accepted_rows=[],
        )

    all_errors: list[RowErrorItem] = []
    accepted: list[dict[str, Any]] = []
    for idx, feat in enumerate(features, start=1):
        if not isinstance(feat, dict) or feat.get("type") != "Feature":
            all_errors.append(
                RowErrorItem(row=idx, column=None, message="Item must be a GeoJSON Feature.")
            )
            continue
        centroid = _geometry_centroid(feat.get("geometry"))
        if centroid is None:
            all_errors.append(
                RowErrorItem(
                    row=idx,
                    column="geometry",
                    message="Geometry must be a valid closed Polygon/MultiPolygon in EPSG:4326.",
                )
            )
            continue
        props = dict(feat.get("properties") or {})
        props.setdefault("latitude", centroid[0])
        props.setdefault("longitude", centroid[1])
        cleaned, row_errors = _validate_row_fields(props, idx, require_coords=True)
        all_errors.extend(row_errors)
        if cleaned is not None:
            accepted.append(cleaned)

    return ParsedUpload(
        format="geojson",
        status=_status_for(len(features), len(accepted), all_errors),
        rows_total=len(features),
        rows_accepted=len(accepted),
        errors=all_errors,
        accepted_rows=accepted,
    )
