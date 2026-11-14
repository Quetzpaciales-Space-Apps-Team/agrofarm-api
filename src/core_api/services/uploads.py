"""Service for farm data uploads (CSV and GeoJSON) with ownership and DEC-005 validation."""

import re
import uuid
from pathlib import Path

from core_api.domain.auth import CurrentUser
from core_api.domain.problem import ProblemError
from core_api.domain.uploads import (
    UploadFormat,
    UploadRecord,
    validate_csv_upload,
    validate_geojson_upload,
)
from core_api.repositories.farms import FarmRepository
from core_api.repositories.uploads import UploadRepository

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


class UploadService:
    def __init__(
        self,
        farm_repo: FarmRepository,
        upload_repo: UploadRepository,
        *,
        raw_dir: Path,
    ) -> None:
        self._farm_repo = farm_repo
        self._upload_repo = upload_repo
        self._raw_dir = raw_dir

    def _require_farm(self, user: CurrentUser, farm_id: uuid.UUID) -> None:
        farm = self._farm_repo.get(farm_id)
        if not farm or (farm.owner_id != user.id and user.role != "admin"):
            raise ProblemError(404, "not_found", "Farm not found")

    def list_uploads(
        self, user: CurrentUser, farm_id: uuid.UUID, limit: int = 20, cursor: str | None = None
    ) -> tuple[list[UploadRecord], str | None]:
        self._require_farm(user, farm_id)
        return self._upload_repo.list_by_farm(farm_id, limit, cursor)

    def process_upload(
        self,
        user: CurrentUser,
        farm_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
    ) -> UploadRecord:
        self._require_farm(user, farm_id)
        clean_name = _SAFE_NAME_RE.sub("_", Path(filename).name or "upload.csv")[:120]
        lower = clean_name.lower()
        fmt: UploadFormat
        if lower.endswith(".geojson") or lower.endswith(".json"):
            fmt = "geojson"
            parsed = validate_geojson_upload(content)
        elif lower.endswith(".csv"):
            fmt = "csv"
            parsed = validate_csv_upload(content)
        else:
            raise ProblemError(
                422,
                "validation_error",
                "Unsupported file format. Only .csv and .geojson are accepted.",
            )

        upload_id = uuid.uuid4()
        target_dir = self._raw_dir / str(farm_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        raw_path = target_dir / f"{upload_id}_{clean_name}"
        raw_path.write_bytes(content)

        return self._upload_repo.create(
            upload_id=upload_id,
            farm_id=farm_id,
            filename=clean_name,
            fmt=fmt,
            status=parsed.status,
            rows_total=parsed.rows_total,
            rows_accepted=parsed.rows_accepted,
            errors=parsed.errors,
            raw_path=str(raw_path),
            accepted_rows=parsed.accepted_rows,
        )
