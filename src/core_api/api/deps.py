"""Dependency injection wiring. Tests replace these providers."""

from fastapi import Request

from core_api.services.readiness import ReadinessService


def get_readiness_service(request: Request) -> ReadinessService:
    return ReadinessService(request.app.state.probes)
