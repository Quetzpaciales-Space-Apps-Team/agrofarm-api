"""Bounded binary photo intake; ownership and inference live in the service layer."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool

from core_api.api.deps import get_current_user, get_leaf_service
from core_api.domain.auth import CurrentUser
from core_api.domain.problem import ProblemError
from core_api.services.leaves import LeafAssessmentService

router = APIRouter(prefix="/v1/farms", tags=["farms"])


@router.post("/{farm_id}/leaves/assess")
async def assess_leaf(
    farm_id: uuid.UUID,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[LeafAssessmentService, Depends(get_leaf_service)],
) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in {"image/jpeg", "image/png"}:
        raise ProblemError(415, "unsupported_media_type", "Upload JPEG or PNG image bytes")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 5 * 1024 * 1024:
            raise ProblemError(413, "image_too_large", "Image exceeds the 5 MiB limit")
    return await run_in_threadpool(service.assess, user, farm_id, bytes(data), content_type)
