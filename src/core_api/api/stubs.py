"""Stub endpoints generated from the contract.

Every operation marked `x-stub: true` answers with the example of its success response, so
the frontend and the other services can build against the contract before the real
implementation exists. Stubs do not validate input and do not check authentication.
When a real router lands, remove `x-stub` from the operation in the contract.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

METHODS = ("get", "post", "put", "patch", "delete")
STUB_HEADERS = {"X-Stub": "true"}


def _resolve(contract: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        target: Any = contract
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def _handler(status: int, example: Any) -> Callable[[Request], Awaitable[Response]]:
    async def stub(_: Request) -> Response:
        if status == 204:
            return Response(status_code=204, headers=STUB_HEADERS)
        return JSONResponse(example, status_code=status, headers=STUB_HEADERS)

    return stub


def build_stub_router(contract: dict[str, Any]) -> APIRouter:
    router = APIRouter()
    for path, item in contract["paths"].items():
        for method in METHODS:
            operation = item.get(method)
            if not operation or not operation.get("x-stub"):
                continue
            status = min(int(code) for code in operation["responses"] if code.startswith("2"))
            response = _resolve(contract, operation["responses"][str(status)])
            example = response.get("content", {}).get("application/json", {}).get("example")
            router.add_api_route(
                path,
                _handler(status, example),
                methods=[method.upper()],
                name=f"stub_{operation['operationId']}",
                include_in_schema=False,
            )
    return router
