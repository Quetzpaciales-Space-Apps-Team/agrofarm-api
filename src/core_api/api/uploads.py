"""Farm data upload HTTP endpoints with streaming size limit."""

import uuid
from email.parser import BytesParser
from email.policy import default
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from core_api.api.deps import get_current_user, get_upload_service
from core_api.config import Settings
from core_api.domain.auth import CurrentUser
from core_api.domain.problem import ProblemError
from core_api.domain.uploads import UploadRecord
from core_api.services.uploads import UploadService

router = APIRouter(prefix="/v1/farms/{farm_id}/uploads", tags=["farms"])


def _serialize_upload(upload: UploadRecord) -> dict[str, Any]:
    return {
        "id": str(upload.id),
        "farm_id": str(upload.farm_id),
        "filename": upload.filename,
        "format": upload.format,
        "status": upload.status,
        "rows_total": upload.rows_total,
        "rows_accepted": upload.rows_accepted,
        "errors": [{"row": e.row, "column": e.column, "message": e.message} for e in upload.errors],
        "created_at": upload.created_at.isoformat().replace("+00:00", "Z"),
    }


def _extract_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    if "multipart/form-data" not in content_type.lower():
        raise ProblemError(422, "validation_error", "Expected multipart/form-data request.")
    raw_msg = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("latin-1") + body
    msg = BytesParser(policy=default).parsebytes(raw_msg)
    if not msg.is_multipart():
        raise ProblemError(422, "validation_error", "Invalid multipart payload.")
    for part in msg.iter_parts():
        if part.get_param("name", header="Content-Disposition") == "file":
            filename = part.get_filename() or "upload.csv"
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                return filename, payload
    raise ProblemError(422, "validation_error", "Missing 'file' field in multipart payload.")


@router.get("")
def list_uploads(
    farm_id: uuid.UUID,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> dict[str, Any]:
    items, next_cursor = service.list_uploads(user, farm_id, limit=limit, cursor=cursor)
    return {"items": [_serialize_upload(u) for u in items], "next_cursor": next_cursor}


@router.post("", status_code=201)
async def create_upload(
    farm_id: uuid.UUID,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[UploadService, Depends(get_upload_service)],
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    max_bytes = settings.max_upload_bytes
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        raise ProblemError(413, "payload_too_large", "Uploaded file exceeds size limit.")

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            raise ProblemError(413, "payload_too_large", "Uploaded file exceeds size limit.")
        chunks.append(chunk)

    content_type = request.headers.get("content-type", "")
    filename, file_bytes = _extract_multipart_file(content_type, b"".join(chunks))
    upload = service.process_upload(user, farm_id, filename=filename, content=file_bytes)
    return _serialize_upload(upload)
