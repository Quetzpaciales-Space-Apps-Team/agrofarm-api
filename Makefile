PYTHON_BIN := $(shell if [ -d .venv/bin ]; then echo ".venv/bin"; else echo "uv run"; fi)
RUFF := $(if $(wildcard .venv/bin/ruff),.venv/bin/ruff,uv run ruff)
MYPY := $(if $(wildcard .venv/bin/mypy),.venv/bin/mypy,uv run mypy)
PYTEST := $(if $(wildcard .venv/bin/pytest),.venv/bin/pytest,uv run pytest)
UVICORN := $(if $(wildcard .venv/bin/uvicorn),.venv/bin/uvicorn,uv run uvicorn)

.PHONY: dev test lint typecheck build check

dev:
	$(UVICORN) agrofarm_api.main:app_factory --factory --reload --host 0.0.0.0 --port $${PORT:-8080}

lint:
	$(RUFF) check .
	$(RUFF) format --check .

typecheck:
	$(MYPY) src tests

test:
	$(PYTEST) --cov

build:
	docker build -t agrofarm-api:local .

check: lint typecheck test
