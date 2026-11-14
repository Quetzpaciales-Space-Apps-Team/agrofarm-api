"""Property-based conformance: generated requests must never crash the service and every
response must match the contract. Runs in process, no network."""

from typing import Any

import schemathesis
from schemathesis.checks import not_a_server_error
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_schema_conformance,
    status_code_conformance,
)

from core_api.config import Settings
from core_api.main import create_app
from tests.conftest import TEST_DATABASE_URL, FakeProbe

app = create_app(Settings(database_url=TEST_DATABASE_URL))
app.state.probes = [FakeProbe("database", healthy=True)]
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
