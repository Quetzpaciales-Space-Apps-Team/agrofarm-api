"""The demo guest cap counts guests of the last 24 hours, so old guests never lock the demo."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from core_api.config import Settings
from core_api.domain.problem import ProblemError
from core_api.services.auth import AuthService
from tests.conftest import TEST_DATABASE_URL
from tests.unit.test_auth import InMemoryAuthRepository


def _service(repo: InMemoryAuthRepository) -> AuthService:
    return AuthService(repo, jwt_secret="x" * 40, jwt_issuer="issuer", jwt_audience="audience")


def _age_every_guest(repo: InMemoryAuthRepository, hours: int) -> None:
    for user_id, user in list(repo.users.items()):
        repo.users[user_id] = replace(user, created_at=datetime.now(UTC) - timedelta(hours=hours))


def test_guests_older_than_a_day_do_not_count_toward_the_cap() -> None:
    repo = InMemoryAuthRepository()
    service = _service(repo)
    for _ in range(3):
        service.create_demo_guest(max_guests=3)
    with pytest.raises(ProblemError) as full:
        service.create_demo_guest(max_guests=3)
    assert full.value.status == 503

    _age_every_guest(repo, hours=25)

    user, *_ = service.create_demo_guest(max_guests=3)
    assert user.email.startswith("demo-guest-")


def test_recent_guests_still_hit_the_cap() -> None:
    repo = InMemoryAuthRepository()
    service = _service(repo)
    service.create_demo_guest(max_guests=2)
    service.create_demo_guest(max_guests=2)
    with pytest.raises(ProblemError, match="capacity"):
        service.create_demo_guest(max_guests=2)


def test_a_guest_just_inside_the_window_still_counts() -> None:
    repo = InMemoryAuthRepository()
    service = _service(repo)
    service.create_demo_guest(max_guests=1)
    _age_every_guest(repo, hours=23)
    with pytest.raises(ProblemError, match="capacity"):
        service.create_demo_guest(max_guests=1)


def test_registered_users_are_never_counted_as_guests() -> None:
    repo = InMemoryAuthRepository()
    repo.create_user(email="farmer@example.test", name="Farmer", role="farmer", password_hash="h")
    service = _service(repo)
    service.create_demo_guest(max_guests=1)


def test_the_default_cap_leaves_room_for_a_whole_day_of_judges() -> None:
    assert Settings(database_url=TEST_DATABASE_URL).demo_max_guests == 1000
