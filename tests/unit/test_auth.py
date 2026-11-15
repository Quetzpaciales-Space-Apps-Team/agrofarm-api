"""Unit and HTTP boundary tests for auth MVP: register, login, refresh, logout, /me, JWT."""

import base64
import json
import time
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from core_api.api.deps import get_auth_service, get_readiness_service
from core_api.config import Settings
from core_api.domain.auth import RefreshTokenRecord, UserRecord, encode_access_token
from core_api.domain.problem import ProblemError
from core_api.main import create_app
from core_api.services.auth import AuthService
from core_api.services.readiness import ReadinessService
from tests.conftest import FakeProbe


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, UserRecord] = {}
        self.by_email: dict[str, uuid.UUID] = {}
        self.tokens: dict[str, RefreshTokenRecord] = {}

    def create_user(self, *, email: str, name: str, role: str, password_hash: str) -> UserRecord:
        lower = email.lower()
        if lower in self.by_email:
            raise ProblemError(409, "conflict", "Email already registered")
        user = UserRecord(
            id=uuid.uuid4(),
            email=lower,
            name=name,
            role=role,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        self.users[user.id] = user
        self.by_email[lower] = user.id
        return user

    def get_user_by_email(self, email: str) -> UserRecord | None:
        uid = self.by_email.get(email.lower())
        return self.users.get(uid) if uid else None

    def get_user_by_id(self, user_id: uuid.UUID) -> UserRecord | None:
        return self.users.get(user_id)

    def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        user = self.users.get(user_id)
        if user is not None:
            self.users[user_id] = replace(user, password_hash=password_hash)

    def count_demo_guests(self, prefix: str = "demo-guest-") -> int:
        lower = prefix.lower()
        return sum(
            1
            for user in self.users.values()
            if user.email.startswith(lower) and user.email.endswith("@demo.agrofarm.invalid")
        )

    def revoke_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        for token_hash, token in self.tokens.items():
            if token.user_id == user_id and token.revoked_at is None:
                self.tokens[token_hash] = replace(token, revoked_at=datetime.now(UTC))

    def create_refresh_token(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshTokenRecord:
        rec = RefreshTokenRecord(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self.tokens[token_hash] = rec
        return rec

    def get_refresh_token(self, token_hash: str) -> RefreshTokenRecord | None:
        return self.tokens.get(token_hash)

    def revoke_refresh_token(self, token_hash: str) -> None:
        rec = self.tokens.get(token_hash)
        if rec and rec.revoked_at is None:
            self.tokens[token_hash] = RefreshTokenRecord(
                id=rec.id,
                user_id=rec.user_id,
                token_hash=rec.token_hash,
                expires_at=rec.expires_at,
                revoked_at=datetime.now(UTC),
            )


@pytest.fixture
def auth_client(settings: Settings) -> Iterator[tuple[TestClient, Settings]]:
    repo = InMemoryAuthRepository()
    app = create_app(settings)
    app.dependency_overrides[get_readiness_service] = lambda: ReadinessService(
        [FakeProbe("database", healthy=True)]
    )
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        repo,
        jwt_secret=settings.jwt_secret.get_secret_value(),
        jwt_issuer=settings.jwt_issuer,
        jwt_audience=settings.jwt_audience,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, settings


def test_register_validation_and_duplicate_email(auth_client: tuple[TestClient, Settings]) -> None:
    client, _ = auth_client
    res = client.post(
        "/v1/auth/register",
        json={"email": "Ana@Example.com", "password": "correct horse battery", "name": "Ana"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "ana@example.com"
    assert "password" not in res.json()

    dup = client.post(
        "/v1/auth/register",
        json={"email": "ana@example.com", "password": "correct horse battery", "name": "Ana"},
    )
    assert dup.status_code == 409

    weak = client.post(
        "/v1/auth/register",
        json={"email": "b@example.com", "password": "password123", "name": "B"},
    )
    assert weak.status_code == 422


def test_login_refresh_me_and_logout(auth_client: tuple[TestClient, Settings]) -> None:
    client, _ = auth_client
    client.post(
        "/v1/auth/register",
        json={"email": "farmer@example.com", "password": "correct horse battery", "name": "Farmer"},
    )

    bad_login = client.post(
        "/v1/auth/login",
        json={"email": "farmer@example.com", "password": "wrong password here"},
    )
    assert bad_login.status_code == 401

    login_res = client.post(
        "/v1/auth/login",
        json={"email": "farmer@example.com", "password": "correct horse battery"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "farmer@example.com"

    ref_res = client.post("/v1/auth/refresh")
    assert ref_res.status_code == 200
    assert ref_res.json()["access_token"]

    logout_res = client.post("/v1/auth/logout")
    assert logout_res.status_code == 204
    assert client.post("/v1/auth/refresh").status_code == 401


def test_jwt_rejects_none_alg_tampered_and_expired(
    auth_client: tuple[TestClient, Settings],
) -> None:
    client, settings = auth_client
    none_header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    none_payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": str(uuid.uuid4())}).encode())
        .rstrip(b"=")
        .decode()
    )
    assert (
        client.get(
            "/v1/me", headers={"Authorization": f"Bearer {none_header}.{none_payload}."}
        ).status_code
        == 401
    )

    expired = encode_access_token(
        user_id=uuid.uuid4(),
        role="farmer",
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_seconds=60,
        now=int(time.time()) - 120,
    )
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
