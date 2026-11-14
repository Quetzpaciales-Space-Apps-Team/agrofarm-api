# agrofarm-api

Public REST API: auth, farms, uploads, search and orchestration. Owns PostgreSQL (service `core-api`).

Part of AgroFarm, a crop growth and rotation simulator for farmers. The tool supports decisions. It never replaces farmers or local agronomists.

## Start here

- **Rules for people and agents:** [`AGENTS.md`](AGENTS.md). Read it before changing anything.
- **Tasks:** the GitHub issues of this repository. Issues labeled `agent-ready` can be given to an agent. Issues labeled `needs-human` need a person.
- **Shared plan and dataset catalog:** the `agrofarm-docs` repository.

## Stack and Dependency Manager

- **Language & Runtime:** Python 3.12 (`FastAPI`, `Pydantic v2`, `SQLAlchemy 2.0`, `Alembic`).
- **Dependency manager:** [`uv`](https://docs.astral.sh/uv/) with a locked `uv.lock` file.
- **Database:** PostgreSQL 16 (`postgis/postgis:16-3.4` in local compose with `pg_trgm` and `unaccent` enabled; PostGIS stays disabled until ADR BE-015).

## Local Development

Copy `.env.example` to `.env` or pass environment variables directly:

```bash
cp .env.example .env
uv sync --frozen
```

### Standard Makefile Targets

```bash
make dev        # Run uvicorn with hot reload on PORT (default 8080)
make lint       # Run ruff check and ruff format --check
make typecheck  # Run mypy in strict mode
make test       # Run pytest with coverage gate (80%)
make build      # Build the multi-stage Docker image
make check      # Run lint + typecheck + test
```

### Running with Docker Compose

```bash
docker compose up --build
```

- Liveness check: `GET http://localhost:8080/healthz`
- Readiness check: `GET http://localhost:8080/readyz`
- OpenAPI docs: `http://localhost:8080/docs`

## The short version of the rules

1. Everything is written in English.
2. Tests first (TDD). CI must be green.
3. Branch from `develop`, open a pull request into `develop`. Nobody pushes to `develop` or `main` directly.
4. `develop` deploys to staging. `main` deploys to production after manual approval.
5. One task, one branch, one pull request.

## Repositories

| Repo | Service(s) |
|---|---|
| `agrofarm-frontend` | `frontend` |
| `agrofarm-api` | `core-api` |
| `agrofarm-analytic` | `ml-service`, `data-service` |
| `agrofarm-docs` | documentation only |
