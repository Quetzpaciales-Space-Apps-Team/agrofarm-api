import pytest
from pydantic import ValidationError

from core_api import main as main_module
from core_api.config import DEFAULT_DEV_JWT_SECRET, Settings


def test_settings_refuse_to_load_without_a_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_read_the_database_url_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")

    settings = Settings(_env_file=None)

    assert settings.database_url.get_secret_value().endswith("/app")


def test_database_url_is_never_shown_in_the_settings_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:hunter2@localhost:5432/app")

    assert "hunter2" not in repr(Settings(_env_file=None))


def test_wildcard_cors_origin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["*"]')

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_accepts_both_cors_allowed_origins_and_cors_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "https://agrofarming.site,http://localhost:5173")

    settings = Settings(_env_file=None)
    assert settings.cors_allowed_origins == ["https://agrofarming.site", "http://localhost:5173"]

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["https://agrofarming.site"]')
    settings_override = Settings(_env_file=None)
    assert settings_override.cors_allowed_origins == ["https://agrofarming.site"]


def test_non_local_environment_rejects_default_or_empty_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)

    monkeypatch.setenv("JWT_SECRET", DEFAULT_DEV_JWT_SECRET)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)

    monkeypatch.setenv("JWT_SECRET", "   ")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)

    monkeypatch.setenv("JWT_SECRET", "strong-prod-secret-value")
    settings = Settings(_env_file=None)
    assert settings.jwt_secret.get_secret_value() == "strong-prod-secret-value"


def test_demo_mode_defaults_to_false_and_seed_demo_does_not_run_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/app")
    monkeypatch.delenv("DEMO_MODE", raising=False)

    settings = Settings(_env_file=None)
    assert settings.demo_mode is False

    called = False

    def _fail_if_called(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("core_api.seed_demo.seed_demo", _fail_if_called)
    main_module.create_app(settings)
    assert called is False
