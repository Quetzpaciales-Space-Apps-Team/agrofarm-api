# Backend & Demo Progress (`agrofarm-api` & `agrofarm-docs`)

| Block | Issue | PR | Status | Notes |
|---|---|---|---|---|
| Block 1 | `agrofarm-docs#13` (DEC-005) | [agrofarm-docs#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/24) | PR open | Farm upload schema (CSV + GeoJSON) + valid/invalid examples with provisional Guatemala City polygon. |
| Block 1 | `agrofarm-api#4` (BE-015) | [agrofarm-api#23](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/23) | PR open | ADR `0001-farm-polygons-storage.md` choosing `jsonb` GeoJSON for MVP. |
| Block 2 | `agrofarm-api#9` (BE-020), `#10` (BE-025) | [agrofarm-api#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/24) | PR open | Farms CRUD + pagination + EPSG:4326 polygon validation + IDOR checks + priorities/constraints + migration 0002. |
| Block 3 | `agrofarm-api#6` (BE-010) | [agrofarm-api#25](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/25) | PR open | Auth MVP (`/register`, `/login`, `/refresh`, `/logout`, `/me`) + migration 0003; reuse-detection family revocation & rate-limit deferred post-MVP. |
| Block 4 | `agrofarm-api#11` (BE-030) | [agrofarm-api#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/26) | PR open | Farm CSV/GeoJSON uploads following DEC-005, streaming 413 check, row-level errors, CSV escape helper, migration 0004. |
| Block 5 | `agrofarm-api#7` (BE-045), `#14` (BE-050) | [agrofarm-api#27](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/27) | PR open | `MLClient` (`ML_MODE=fixture|http`), `/v1/climate/enso`, `/v1/scenarios/simulate`, `/v1/farms/{id}/recommendations` with provenance & migration 0005. |
| Block 6 | `agrofarm-api#28` (BE-085) | [agrofarm-api#29](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/29) | Merged | `DemoMLClient`, `DEMO_MODE=true` offline snapshots (`cached_demo`), idempotent `make seed-demo`. |
| Block 7 | `agrofarm-docs#17` (DEMO-001), `#25` (DEMO-003) | [agrofarm-docs#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/26) | Merged | 7-slide English presentation + 30s script (`docs/demo/presentation.md`), challenge checklist, submission form copy. |
| T1 | — (`fix/config-cors-jwt`) | [agrofarm-api#30](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/30) | PR open | `CORS_ORIGINS` alias, non-local `JWT_SECRET` guard, `DEMO_MODE=false` default test, `.env.example` (`https://agrofarming.site`), `docs/ops-env.md`. |
| T2 | `agrofarm-frontend#46` | [agrofarm-api#31](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/31) | PR open | `disclaimer` on ENSO/simulate/recommendations, full `Provenance`, `make export-openapi` + drift tests, `docs/contract/frontend-migration.md`. |
| T3 | `agrofarm-api#32` (BE-048) | [agrofarm-api#33](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/33) | PR open | `docs/contract/ml-service-expected.yaml`, `HttpMLClient` fixture fallback + `httpx.MockTransport` contract tests, posted on `agrofarm-analytic#3` & `#27`. |
| T4 | — (`chore/deploy-readiness`) | PR opening | PR opening | Local `docker build` + container `/healthz`/`/readyz`/`seed-demo` verified (`DEMO_MODE=true`), `docs/deploy-checklist.md`. |
| T5 | — (`docs/submission-honesty`) | [agrofarm-docs#27](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/27) | PR open | Clarified `cached_demo` / `ML_MODE=fixture` in `presentation.md` & `submission-form.md`, SI units, `https://agrofarming.site` + `TODO_PUBLIC_URL` placeholders. |

## Remaining Optional Items (If Time Before Freeze)
- `BE-040` (out of MVP cut), stretch items (`BE-055`, `BE-058`, `BE-060`, `BE-070`, `BE-080` — untouched).
- Deferred post-MVP: refresh token reuse-detection family revocation (`BE-010`), frontend alignment (`agrofarm-frontend#46`) & `FE-505` (`agrofarm-frontend#36`), GCP/CD deployment (`OPS-001..004` by `angcoder-c`), final `develop` -> `main` release PR (human).

## Known Risks
- **Port 5432 in use locally:** Run `DB_PORT=5433 make check` / `DB_PORT=5433 make seed-demo` when host port `5432` is occupied.
- **Chained PRs in `agrofarm-api`:** PRs #23 -> #24 -> #25 -> #26 -> #27 -> #29 were branched sequentially; merge in order into `develop` (or squash/rebase as needed).
- **Live ML & Frontend integration:** `core-api` currently validates against deterministic `FixtureMLClient` and `DemoMLClient` until `agrofarm-analytic` ML service PRs (#36, #37) and `agrofarm-frontend` (`FE-505`) merge.

## Exact Run & Offline Demo Commands
```bash
cd agrofarm-api
DB_PORT=5433 make check
DB_PORT=5433 make seed-demo
DATABASE_URL=postgresql+psycopg://agrofarm:local-dev-only@localhost:5433/agrofarm \
  DEMO_MODE=true uv run uvicorn core_api.main:create_app --factory --port 8080
```
