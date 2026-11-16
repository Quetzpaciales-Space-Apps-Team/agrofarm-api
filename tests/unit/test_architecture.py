"""Layer rules from AGENTS.md section 4, enforced as tests."""

import ast
from pathlib import Path

PACKAGE = "core_api"
SRC = Path(__file__).resolve().parents[2] / "src" / PACKAGE

# layer directory -> import prefixes that layer must never use
FORBIDDEN: dict[str, tuple[str, ...]] = {
    "services": ("fastapi", "starlette", "sqlalchemy", f"{PACKAGE}.api"),
    "repositories": ("fastapi", "starlette", f"{PACKAGE}.services", f"{PACKAGE}.api"),
    "domain": ("fastapi", "starlette", "sqlalchemy", "httpx", f"{PACKAGE}.api"),
    "api": ("sqlalchemy",),
}


def _imports(source: str) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def find_violations(root: Path) -> list[str]:
    found: list[str] = []
    for layer, forbidden in FORBIDDEN.items():
        for path in sorted((root / layer).rglob("*.py")):
            for name in _imports(path.read_text(encoding="utf-8")):
                if any(name == bad or name.startswith(bad + ".") for bad in forbidden):
                    found.append(f"{layer}/{path.name} imports {name}")
    return found


def test_source_tree_respects_the_layer_rules() -> None:
    assert find_violations(SRC) == []


def test_canary_a_service_importing_fastapi_is_caught(tmp_path: Path) -> None:
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "bad.py").write_text("from fastapi import Request\n", encoding="utf-8")

    assert find_violations(tmp_path) == ["services/bad.py imports fastapi"]


def test_canary_a_repository_importing_a_service_is_caught(tmp_path: Path) -> None:
    (tmp_path / "repositories").mkdir()
    (tmp_path / "repositories" / "bad.py").write_text(
        f"import {PACKAGE}.services.readiness\n", encoding="utf-8"
    )

    assert find_violations(tmp_path) == [
        f"repositories/bad.py imports {PACKAGE}.services.readiness"
    ]


def test_canary_a_router_importing_sqlalchemy_is_caught(tmp_path: Path) -> None:
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "bad.py").write_text("import sqlalchemy.orm\n", encoding="utf-8")

    assert find_violations(tmp_path) == ["api/bad.py imports sqlalchemy.orm"]
