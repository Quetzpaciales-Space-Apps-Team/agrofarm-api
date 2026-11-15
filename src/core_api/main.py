"""Application factory. Run with: uvicorn core_api.main:create_app --factory"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core_api.api import auth, farms, health, simulation, uploads
from core_api.api.stubs import build_stub_router
from core_api.config import Settings
from core_api.contract import load_contract
from core_api.middleware.errors import register_error_handlers
from core_api.middleware.request_id import RequestContextMiddleware
from core_api.repositories.database import DatabaseProbe, create_db_engine
from core_api.services.auth import DemoRateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    # Settings() raises when a required secret is missing, so the app refuses to start.
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")

    app = FastAPI(title="AgroFarm core-api", version="0.1.0")
    engine = create_db_engine(settings.database_url.get_secret_value())
    app.state.settings = settings
    app.state.engine = engine
    app.state.probes = [DatabaseProbe(engine)]
    app.state.demo_rate_limiter = DemoRateLimiter(max_requests=settings.demo_rate_limit_per_minute)

    # Order (outermost first): request id and logging, CORS, [rate limit, auth: later tasks],
    # error handlers. Starlette runs the middleware added last first.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"],
        expose_headers=["X-Request-Id"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    # Contract first: serve the hand-written contract, not a generated schema.
    contract = load_contract()
    app.openapi = lambda: contract  # type: ignore[method-assign]

    # Real routers first. Stubs only cover operations still marked `x-stub` in the contract.
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(farms.router)
    app.include_router(uploads.router)
    app.include_router(simulation.router)
    app.include_router(build_stub_router(contract))
    return app
