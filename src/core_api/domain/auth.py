"""Domain auth primitives: password hashing, JWT HS256 encode/decode, and user models."""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core_api.domain.problem import ProblemError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COMMON_PASSWORDS = frozenset(
    {
        "1234567890",
        "password123",
        "qwerty12345",
        "letmein1234",
        "admin123456",
        "welcome1234",
    }
)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    role: str


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: uuid.UUID
    email: str
    name: str
    role: str
    password_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshTokenRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=72)
    name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address.")
        return value

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password exceeds 72-byte limit.")
        if value.lower() in COMMON_PASSWORDS:
            raise ValueError("Password is too common.")
        return value


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("Invalid email address.")
        return value


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    dk_b64 = base64.b64encode(derived).decode("ascii")
    return f"scrypt${salt_b64}${dk_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored_hash.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
    except Exception:
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(actual, expected)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode_access_token(
    *,
    user_id: uuid.UUID,
    role: str,
    secret: str,
    issuer: str,
    audience: str,
    ttl_seconds: int = 900,
    now: int | None = None,
) -> str:
    issued_at = now if now is not None else int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": issuer,
        "aud": audience,
        "iat": issued_at,
        "exp": issued_at + ttl_seconds,
        "jti": str(uuid.uuid4()),
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
    now: int | None = None,
) -> CurrentUser:
    parts = token.split(".")
    if len(parts) != 3:
        raise ProblemError(401, "unauthenticated", "Invalid authentication token")

    header_b64, payload_b64, sig_b64 = parts
    try:
        header: dict[str, Any] = json.loads(_b64url_decode(header_b64))
        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
        provided_sig = _b64url_decode(sig_b64)
    except Exception as exc:
        raise ProblemError(401, "unauthenticated", "Invalid authentication token") from exc

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise ProblemError(401, "unauthenticated", "Invalid token algorithm")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ProblemError(401, "unauthenticated", "Invalid token signature")

    current_time = now if now is not None else int(time.time())
    exp = payload.get("exp")
    if not isinstance(exp, int | float) or exp <= current_time:
        raise ProblemError(401, "unauthenticated", "Token has expired")

    if payload.get("iss") != issuer or payload.get("aud") != audience:
        raise ProblemError(401, "unauthenticated", "Invalid token claims")

    sub = payload.get("sub")
    role = payload.get("role")
    if not isinstance(sub, str) or not isinstance(role, str) or not payload.get("jti"):
        raise ProblemError(401, "unauthenticated", "Invalid token claims")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise ProblemError(401, "unauthenticated", "Invalid token subject") from exc

    return CurrentUser(id=user_id, role=role)
