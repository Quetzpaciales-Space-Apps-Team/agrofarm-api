import pytest
from pydantic import ValidationError

from agrofarm_api.config import Settings


def test_settings_refuse_to_start_without_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://u:p@h:5432/d')
    monkeypatch.setenv('CORS_ORIGINS', '["https://app.example.org"]')
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.database_url.endswith('/d')
    assert settings.cors_origins == ['https://app.example.org']


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url='postgresql+psycopg://u:p@h/d', cors_origins=['*'])


def test_cors_defaults_to_empty_allowlist() -> None:
    assert Settings(database_url='postgresql+psycopg://u:p@h/d').cors_origins == []
