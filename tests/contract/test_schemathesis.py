"""Property-based conformance: generated requests must never crash the service and every
response must match the contract. Runs in process, no network."""

import tempfile
from pathlib import Path
from typing import Any

import schemathesis
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_schema_conformance,
    status_code_conformance,
)

from core_api.api.deps import get_auth_service, get_farm_service, get_upload_service
from core_api.config import Settings
from core_api.main import create_app
from core_api.services.auth import AuthService
from core_api.services.farms import FarmService
from core_api.services.uploads import UploadService
from tests.conftest import TEST_DATABASE_URL, FakeProbe
from tests.unit.test_auth import InMemoryAuthRepository
from tests.unit.test_farms import InMemoryFarmRepository
from tests.unit.test_uploads import InMemoryUploadRepository

_settings = Settings(database_url=TEST_DATABASE_URL)
app = create_app(_settings)
app.state.probes = [FakeProbe("database", healthy=True)]
_fake_auth_repo = InMemoryAuthRepository()
_fake_farm_repo = InMemoryFarmRepository()
_fake_upload_repo = InMemoryUploadRepository()
app.dependency_overrides[get_auth_service] = lambda: AuthService(
    _fake_auth_repo,
    jwt_secret=_settings.jwt_secret.get_secret_value(),
    jwt_issuer=_settings.jwt_issuer,
    jwt_audience=_settings.jwt_audience,
)
app.dependency_overrides[get_farm_service] = lambda: FarmService(_fake_farm_repo)
app.dependency_overrides[get_upload_service] = lambda: UploadService(
    _fake_farm_repo, _fake_upload_repo, raw_dir=Path(tempfile.mkdtemp())
)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
def test_service_conforms_to_the_contract(case: "schemathesis.Case[Any]") -> None:
    case.call_and_validate(
        checks=[
            not_a_server_error,
            status_code_conformance,
            content_type_conformance,
            response_schema_conformance,
        ]
    )
