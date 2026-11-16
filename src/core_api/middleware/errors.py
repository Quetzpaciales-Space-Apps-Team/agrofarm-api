"""Every error leaves the API as application/problem+json (RFC 7807) with a stable code."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from core_api.domain.problem import ProblemError
from core_api.middleware.request_id import current_request_id

logger = logging.getLogger(__name__)
_CODES = {401: "unauthenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}


def problem(
    status: int, code: str, title: str, detail: str | None = None, **extra: Any
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "code": code,
        "request_id": current_request_id(),
        **extra,
    }
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(_: Request, error: ProblemError) -> JSONResponse:
        return problem(error.status, error.code, error.title, error.detail, **error.extra)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, error: HTTPException) -> JSONResponse:
        code = _CODES.get(error.status_code, "http_error")
        return problem(error.status_code, code, HTTPStatus(error.status_code).phrase)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, error: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
            for item in error.errors()
        ]
        return problem(422, "validation_error", "Request validation failed", errors=fields)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, error: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", type(error).__name__)
        return problem(500, "internal_error", "Internal server error")
