"""RFC 7807 problem+json error handling with stable codes."""

import logging
import re
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

PROBLEM_JSON = "application/problem+json"
logger = logging.getLogger("agrofarm_api.errors")

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "rate_limited",
}


class ProblemError(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str | None = None) -> None:
        super().__init__(detail or title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def problem_response(
    request: Request,
    status: int,
    code: str,
    title: str,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "code": code,
        "request_id": request_id,
    }
    if detail:
        body["detail"] = detail
    if extra:
        body.update(extra)
    response = JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)
    response.headers["X-Request-Id"] = request_id
    return response


class UnhandledErrorMiddleware(BaseHTTPMiddleware):
    """Last line of defence: unexpected exceptions become a generic 500 problem."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "unhandled error", extra={"request_id": getattr(request.state, "request_id", "-")}
            )
            return problem_response(
                request,
                500,
                "internal_error",
                "Internal Server Error",
                "An unexpected error occurred.",
            )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError) -> JSONResponse:
        return problem_response(request, exc.status, exc.code, exc.title, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        title = re.sub(r"\s+", " ", str(exc.detail)) if exc.detail else "Error"
        return problem_response(request, exc.status_code, code, title)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": [str(p) for p in e["loc"]], "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        return problem_response(
            request,
            422,
            "validation_error",
            "Validation Error",
            "The request is not valid.",
            {"errors": errors},
        )
