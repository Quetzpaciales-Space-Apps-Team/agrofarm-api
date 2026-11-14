import pytest
from pydantic import ValidationError

from core_api.config import Settings


def test_settings_refuse_to_load_without_a_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_read_the_database_url_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.database_url.get_secret_value().endswith("/app")


def test_database_url_is_never_shown_in_the_settings_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:hunter2@localhost:5432/app")

    assert "hunter2" not in repr(Settings(_env_file=None))  # type: ignore[call-arg]


def test_wildcard_cors_origin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["*"]')

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
