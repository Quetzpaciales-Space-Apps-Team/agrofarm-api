"""Drift and completeness checks between docs/contract/openapi.yaml and app.openapi()."""

from pathlib import Path

import yaml

from core_api.config import Settings
from core_api.main import create_app
from tests.conftest import TEST_DATABASE_URL


def test_openapi_yaml_matches_app_openapi() -> None:
    app = create_app(Settings(database_url=TEST_DATABASE_URL))
    contract_path = Path(__file__).resolve().parents[2] / "docs" / "contract" / "openapi.yaml"
    on_disk = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    assert on_disk == app.openapi()


def test_openapi_enforces_disclaimer_and_full_provenance() -> None:
    app = create_app(Settings(database_url=TEST_DATABASE_URL))
    schemas = app.openapi()["components"]["schemas"]

    for schema_name in ("EnsoSeries", "SimulationResult", "RecommendationSet"):
        schema = schemas[schema_name]
        assert "disclaimer" in schema["required"]
        assert "disclaimer" in schema["properties"]

    prov = schemas["Provenance"]
    for field in ("model_name", "model_version", "data_versions", "input_hash", "generated_at"):
        assert field in prov["required"]
        assert field in prov["properties"]
