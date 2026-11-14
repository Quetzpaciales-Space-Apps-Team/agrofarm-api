from typing import Annotated

from fastapi import APIRouter, Depends

from agrofarm_api.api.dependencies import DatabaseProtocol, get_database
from agrofarm_api.middleware.error_handler import ProblemError

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(database: Annotated[DatabaseProtocol, Depends(get_database)]) -> dict[str, str]:
    if not database.ping():
        raise ProblemError(
            status=503,
            code="dependency_unavailable",
            title="Service Unavailable",
            detail="A required dependency is not reachable.",
        )
    return {"status": "ready"}
