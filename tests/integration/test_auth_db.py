"""PostgreSQL integration tests for SqlAlchemyAuthRepository."""

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from core_api.domain.auth import hash_password, hash_refresh_token
from core_api.domain.problem import ProblemError
from core_api.repositories.auth import SqlAlchemyAuthRepository
from core_api.repositories.database import create_db_engine

pytestmark = pytest.mark.integration


def test_auth_repository_roundtrip() -> None:
    url = os.environ.get("DATABASE_URL")
    assert url
    repo = SqlAlchemyAuthRepository(create_db_engine(url))
    email = f"user-{uuid.uuid4()}@example.com"

    created = repo.create_user(
        email=email,
        name="Test User",
        role="farmer",
        password_hash=hash_password("correct horse battery"),
    )
    assert repo.get_user_by_email(email.upper()) is not None
    assert repo.get_user_by_id(created.id) is not None

    with pytest.raises(ProblemError):
        repo.create_user(
            email=email,
            name="Dup User",
            role="farmer",
            password_hash=hash_password("correct horse battery"),
        )

    thash = hash_refresh_token("raw-token-" + str(uuid.uuid4()))
    repo.create_refresh_token(
        user_id=created.id,
        token_hash=thash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    found = repo.get_refresh_token(thash)
    assert found is not None and found.revoked_at is None

    repo.revoke_refresh_token(thash)
    revoked = repo.get_refresh_token(thash)
    assert revoked is not None and revoked.revoked_at is not None
