"""Authentication HTTP endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response

from core_api.api.deps import get_auth_service, get_current_user
from core_api.config import Settings
from core_api.domain.auth import CurrentUser, LoginInput, RegisterInput, UserRecord
from core_api.services.auth import AuthService

router = APIRouter(prefix="/v1", tags=["auth"])


def _serialize_user(user: UserRecord) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "created_at": user.created_at.isoformat().replace("+00:00", "Z"),
    }


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.environment != "local",
        samesite="lax",
        max_age=settings.refresh_token_ttl_seconds,
        path="/v1/auth",
    )


@router.post("/auth/register", status_code=201)
def register(
    payload: RegisterInput,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    return _serialize_user(service.register(payload))


@router.post("/auth/login")
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    access_token, expires_in, raw_refresh = service.login(payload)
    _set_refresh_cookie(response, raw_refresh, request.app.state.settings)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_in}


@router.post("/auth/refresh")
def refresh(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> dict[str, Any]:
    access_token, expires_in, new_refresh = service.refresh(refresh_token)
    _set_refresh_cookie(response, new_refresh, request.app.state.settings)
    return {"access_token": access_token, "token_type": "bearer", "expires_in": expires_in}


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    service.logout(refresh_token)
    response.delete_cookie(key="refresh_token", path="/v1/auth")
    response.status_code = 204
    return response


@router.get("/me")
def me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    return _serialize_user(service.get_me(user))
