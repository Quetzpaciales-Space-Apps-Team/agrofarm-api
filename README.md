# agrofarm-api

Public REST API: auth, farms, uploads, search and orchestration. Owns PostgreSQL (service `core-api`).

Part of AgroFarm, a crop growth and rotation simulator for farmers. The tool supports decisions. It never replaces farmers or local agronomists.

## Run it

Needs Docker and [uv](https://docs.astral.sh/uv/) (dependency manager for this repo, lockfile `uv.lock`).

```
cp .env.example .env
make dev      # API on http://localhost:8080 and PostgreSQL, migrations applied
make check    # lint, typecheck and all tests against a real PostgreSQL (what CI runs)
```

Other targets: `make test-unit`, `make test-integration`, `make migrate`, `make format`, `make audit`, `make build`. If port 5432 or 8080 is taken, set `DB_PORT` or `API_PORT`.

Layout (`src/core_api/`): `api/` routers, `middleware/`, `services/` use cases, `repositories/` data access, `domain/` pure code, `clients/` other services, `config.py` settings. The layer rules are enforced by `tests/unit/test_architecture.py`.

## Start here

- **Rules for people and agents:** [`AGENTS.md`](AGENTS.md). Read it before changing anything.
- **Tasks:** the GitHub issues of this repository. Issues labeled `agent-ready` can be given to an agent. Issues labeled `needs-human` need a person.
- **Shared plan and dataset catalog:** the `agrofarm-docs` repository.

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
