"""Authentication service (MVP): register, login, refresh, logout, and /me."""

import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from core_api.domain.auth import (
    CurrentUser,
    LoginInput,
    RegisterInput,
    UserRecord,
    encode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from core_api.domain.problem import ProblemError
from core_api.repositories.auth import AuthRepository

ACTIVE_GUEST_WINDOW = timedelta(hours=24)  # a demo guest counts toward the cap for one day

_DUMMY_PASSWORD_HASH = hash_password("dummy-timing-equalizer-password")


class DemoRateLimiter:
    """In-memory per-IP sliding-window limiter for anonymous demo session creation."""

    def __init__(self, *, max_requests: int = 20, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        if self._max_requests <= 0:
            raise ProblemError(429, "rate_limited", "Demo rate limit exceeded.")
        now = time.monotonic()
        cutoff = now - self._window_seconds
        bucket = self._hits[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self._max_requests:
            raise ProblemError(
                429,
                "rate_limited",
                "Too many demo sessions requested. Please try again shortly.",
            )
        bucket.append(now)


class AuthService:
    def __init__(
        self,
        repo: AuthRepository,
        *,
        jwt_secret: str,
        jwt_issuer: str,
        jwt_audience: str,
        access_ttl_seconds: int = 900,
        refresh_ttl_seconds: int = 604800,
    ) -> None:
        self._repo = repo
        self._jwt_secret = jwt_secret
        self._jwt_issuer = jwt_issuer
        self._jwt_audience = jwt_audience
        self._access_ttl = access_ttl_seconds
        self._refresh_ttl = refresh_ttl_seconds

    def register(self, payload: RegisterInput) -> UserRecord:
        pw_hash = hash_password(payload.password)
        return self._repo.create_user(
            email=str(payload.email).lower(),
            name=payload.name,
            role="farmer",
            password_hash=pw_hash,
        )

    def login(self, payload: LoginInput) -> tuple[str, int, str]:
        user = self._repo.get_user_by_email(str(payload.email).lower())
        stored_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
        valid = verify_password(payload.password, stored_hash)
        if not user or not valid:
            raise ProblemError(401, "unauthenticated", "Invalid email or password")

        return self._issue_tokens(user)

    def refresh(self, raw_refresh_token: str | None) -> tuple[str, int, str]:
        if not raw_refresh_token:
            raise ProblemError(401, "unauthenticated", "Missing refresh token")

        token_hash = hash_refresh_token(raw_refresh_token)
        record = self._repo.get_refresh_token(token_hash)
        if not record or record.revoked_at is not None or record.expires_at <= datetime.now(UTC):
            raise ProblemError(401, "unauthenticated", "Invalid or expired refresh token")

        user = self._repo.get_user_by_id(record.user_id)
        if not user:
            raise ProblemError(401, "unauthenticated", "Invalid refresh token")

        self._repo.revoke_refresh_token(token_hash)
        return self._issue_tokens(user)

    def logout(self, raw_refresh_token: str | None) -> None:
        if raw_refresh_token:
            self._repo.revoke_refresh_token(hash_refresh_token(raw_refresh_token))

    def get_me(self, current_user: CurrentUser) -> UserRecord:
        user = self._repo.get_user_by_id(current_user.id)
        if not user:
            raise ProblemError(401, "unauthenticated", "User not found")
        return user

    def _issue_tokens(self, user: UserRecord) -> tuple[str, int, str]:
        access_token = encode_access_token(
            user_id=user.id,
            role=user.role,
            secret=self._jwt_secret,
            issuer=self._jwt_issuer,
            audience=self._jwt_audience,
            ttl_seconds=self._access_ttl,
        )
        raw_refresh = generate_refresh_token()
        self._repo.create_refresh_token(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(seconds=self._refresh_ttl),
        )
        return access_token, self._access_ttl, raw_refresh

    def create_demo_guest(self, *, max_guests: int = 200) -> tuple[UserRecord, str, int, str]:
        """Provision an isolated ephemeral guest user for DEMO_MODE without credentials."""
        # Only guests of the last day count. Older ones are expired (the purge command removes
        # them) and must never lock the demo for the visitors who come after.
        recent = datetime.now(UTC) - ACTIVE_GUEST_WINDOW
        if self._repo.count_demo_guests(created_after=recent) >= max_guests:
            raise ProblemError(
                503,
                "demo_capacity_reached",
                "Demo guest capacity reached. Please try again later.",
            )
        email = f"demo-guest-{uuid.uuid4()}@demo.agrofarm.invalid"
        password_hash = hash_password(secrets.token_urlsafe(32))
        user = self._repo.create_user(
            email=email,
            name="Demo Guest",
            role="farmer",
            password_hash=password_hash,
        )
        access_token, expires_in, raw_refresh = self._issue_tokens(user)
        return user, access_token, expires_in, raw_refresh

    def ensure_user_exists(self, user_id: uuid.UUID) -> bool:
        return self._repo.get_user_by_id(user_id) is not None
