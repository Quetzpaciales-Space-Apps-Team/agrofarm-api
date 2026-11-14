"""Domain auth primitives: JWT HS256 encode/decode and authenticated user context."""

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from core_api.domain.problem import ProblemError


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    role: str


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
