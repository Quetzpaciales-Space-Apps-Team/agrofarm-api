from typing import Annotated

from fastapi import APIRouter, Depends

from core_api.api.deps import get_readiness_service
from core_api.domain.problem import ProblemError
from core_api.services.readiness import ReadinessService

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="The process is alive")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="The dependencies are reachable")
def readyz(
    service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> dict[str, object]:
    report = service.check()
    if not report.ready:
        raise ProblemError(
            status=503,
            code="not_ready",
            title="Service is not ready",
            detail="At least one dependency is unreachable.",
            extra={"checks": report.checks},
        )
    return {"status": "ready", "checks": report.checks}
