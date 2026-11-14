"""Loads the OpenAPI contract. The canonical file is docs/contract/openapi.yaml; the build
copies it into the package so the installed service can serve it."""

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

_REPO_COPY = Path(__file__).resolve().parents[2] / "docs" / "contract" / "openapi.yaml"


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    packaged = resources.files("core_api") / "openapi.yaml"
    text = packaged.read_text("utf-8") if packaged.is_file() else _REPO_COPY.read_text("utf-8")
    contract: dict[str, Any] = yaml.safe_load(text)
    return contract
