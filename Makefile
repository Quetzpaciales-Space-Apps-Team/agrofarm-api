.PHONY: dev test test-unit test-integration lint format typecheck build check migrate seed-demo purge-demo-guests export-openapi audit db-up db-down
DB_PORT ?= 5432
TEST_DATABASE_URL ?= postgresql+psycopg://agrofarm:local-dev-only@localhost:$(DB_PORT)/agrofarm

dev: ## full local environment (API + PostgreSQL)
	docker compose up --build

db-up: ## start only PostgreSQL and wait until it is healthy
	DB_PORT=$(DB_PORT) docker compose up -d --wait db

db-down:
	docker compose down

migrate: ## apply migrations to the local database
	DATABASE_URL=$(TEST_DATABASE_URL) uv run alembic upgrade head

test-unit: ## no network, no database
	uv run pytest -m "not integration"

test-integration: db-up migrate ## real PostgreSQL, never SQLite
	DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest -m integration

test: db-up migrate ## everything, with the coverage gate
	DATABASE_URL=$(TEST_DATABASE_URL) uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

audit: ## known vulnerabilities in the locked dependencies
	uv export --frozen --no-dev --no-emit-project -o /tmp/core-api-requirements.txt -q
	uv run pip-audit -r /tmp/core-api-requirements.txt --require-hashes --disable-pip

build:
	docker build -t core-api:local .

check: lint typecheck test ## what CI runs

seed-demo: db-up migrate ## idempotently seed demo user, farm, priorities, and recommendation
	DATABASE_URL=$(TEST_DATABASE_URL) uv run python -m core_api.seed_demo

purge-demo-guests: db-up migrate ## remove demo-guest accounts older than 24 hours
	DATABASE_URL=$(TEST_DATABASE_URL) uv run python -m core_api.purge_demo_guests

export-openapi: ## export app.openapi() to docs/contract/openapi.yaml
	DATABASE_URL=$(TEST_DATABASE_URL) uv run python -c "from pathlib import Path; import yaml; from core_api.config import Settings; from core_api.main import create_app; app = create_app(Settings(database_url='postgresql+psycopg://u:p@localhost:5432/db')); Path('docs/contract/openapi.yaml').write_text(yaml.safe_dump(app.openapi(), sort_keys=False), encoding='utf-8')"
