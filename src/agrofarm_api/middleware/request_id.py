import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HEADER = "X-Request-Id"
_SAFE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
access_logger = logging.getLogger("agrofarm_api.access")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Echo a safe incoming X-Request-Id or generate one, and log each request with it."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if _SAFE.match(incoming) else str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        response.headers[HEADER] = request_id
        access_logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        return response
