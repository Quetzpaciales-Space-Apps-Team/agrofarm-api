# Backend & Demo Progress (`agrofarm-api` & `agrofarm-docs`)

| Block | Issue | PR | Status | Notes |
|---|---|---|---|---|
| Block 1 | `agrofarm-docs#13` (DEC-005) | [agrofarm-docs#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/24) | PR open | Farm upload schema (CSV + GeoJSON) + valid/invalid examples with provisional Guatemala City polygon. |
| Block 1 | `agrofarm-api#4` (BE-015) | [agrofarm-api#23](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/23) | PR open | ADR `0001-farm-polygons-storage.md` choosing `jsonb` GeoJSON for MVP. |
| Block 2 | `agrofarm-api#9` (BE-020), `#10` (BE-025) | [agrofarm-api#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/24) | PR open | Farms CRUD + pagination + EPSG:4326 polygon validation + IDOR checks + priorities/constraints + migration 0002. |
| Block 3 | `agrofarm-api#6` (BE-010) | [agrofarm-api#25](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/25) | PR open | Auth MVP (`/register`, `/login`, `/refresh`, `/logout`, `/me`) + migration 0003; reuse-detection family revocation & rate-limit deferred post-MVP. |
| Block 4 | `agrofarm-api#11` (BE-030) | [agrofarm-api#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/26) | PR open | Farm CSV/GeoJSON uploads following DEC-005, streaming 413 check, row-level errors, CSV escape helper, migration 0004. |
| Block 5 | `agrofarm-api#7` (BE-045), `#14` (BE-050) | [agrofarm-api#27](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/27) | PR open | `MLClient` (`ML_MODE=fixture|http`), `/v1/climate/enso`, `/v1/scenarios/simulate`, `/v1/farms/{id}/recommendations` with provenance & migration 0005. |
| Block 6 | `agrofarm-api#28` (BE-085) | [agrofarm-api#29](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/29) | PR open | `DemoMLClient`, `DEMO_MODE=true` offline snapshots (`cached_demo`), idempotent `make seed-demo`, 123 tests passing (88.78% coverage). |
| Block 7 | `agrofarm-docs#17` (DEMO-001), `#25` (DEMO-003) | [agrofarm-docs#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/26) | PR open | 7-slide English presentation + 30s script (`docs/demo/presentation.md`), challenge checklist (`docs/demo/challenge-checklist.md`), submission form copy & incognito links checklist (`docs/demo/submission-form.md`). |

## Remaining Optional Items (If Time Before Freeze)
- `BE-048` (contract tests against `agrofarm-analytic` once ML service PRs merge)
- `BE-040`, `BE-055`, `BE-080`
- Deferred post-MVP: refresh token reuse-detection family revocation (`BE-010`), frontend screen capture (`FE-505` -> `agrofarm-frontend#36`), `.pptx`/PDF export if needed.

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
