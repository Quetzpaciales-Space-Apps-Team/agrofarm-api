from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI

from agrofarm_api.api import health, v1
from agrofarm_api.config import Settings
from agrofarm_api.middleware.cors import add_cors
from agrofarm_api.middleware.error_handler import UnhandledErrorMiddleware, register_error_handlers
from agrofarm_api.middleware.logging import configure_logging
from agrofarm_api.middleware.request_id import RequestIdMiddleware
from agrofarm_api.repositories.database import Database

_CONTRACT_Candidates = (
    Path(__file__).resolve().parents[2] / "docs" / "contract" / "openapi.yaml",
    Path("/app/docs/contract/openapi.yaml"),
)


@lru_cache(maxsize=1)
def load_openapi_contract() -> dict[str, Any]:
    for candidate in _CONTRACT_Candidates:
        if candidate.is_file():
            loaded: dict[str, Any] = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            return loaded
    raise RuntimeError("OpenAPI contract file docs/contract/openapi.yaml was not found")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.database.dispose()

    app = FastAPI(title="AgroFarm core-api", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = Database(settings.database_url)
    app.openapi = load_openapi_contract  # type: ignore[method-assign]
    register_error_handlers(app)
    # Starlette runs the last added middleware first: request id outermost,
    # then error handling, then CORS closest to the routes.
    add_cors(app, settings)
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(v1.router)
    return app


def app_factory() -> FastAPI:
    return create_app()
