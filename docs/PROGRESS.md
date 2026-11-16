# Progress and Status (`agrofarm-api`, service `core-api`)

## Status on 2026-11-15

The submission closes on 2026-11-15 at 23:59 Guatemala time.

- All pull requests listed below are merged into `develop`. There are no open pull requests in this repository.
- Only the branches `main` and `develop` exist.
- Staging runs on Cloud Run: core-api at https://core-api-staging-7l2bzjrqpq-uc.a.run.app and frontend at https://frontend-staging-7l2bzjrqpq-uc.a.run.app. The staging deploy (`.github/workflows/cd.yml`) sets `ML_MODE=http`, `ML_AUTH=google_id_token`, `DEMO_MODE=true` and `DEMO_ML_SOURCE=live`, so demo guests get live ml-service answers with cached snapshots as fallback.
- Production has never been deployed. The production job exists in `cd.yml` and runs on pushes to `main`; no CD run on `main` exists before 2026-11-16.
- The `ml_min_instances=1` change (PR #54) is in the Terraform code; whether it was applied to staging is not confirmed. See [`ops-env.md`](ops-env.md).

## Merged pull requests

Source: `gh pr list --state merged` on this repository. Dates are `mergedAt` dates (UTC).

| PR | Merged | Author | Title |
|---|---|---|---|
| [#18](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/18) | 2026-11-14 | `eldmark` | feat: scaffold core-api with layers, health endpoints, migrations, Docker and CI |
| [#19](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/19) | 2026-11-14 | `eldmark` | feat: publish the v1 contract and serve contract-driven stub endpoints |
| [#22](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/22) | 2026-11-14 | `angcoder-c` | chore(infra): modulos de Terraform para GCP, WIF y script de proteccion de ramas |
| [#23](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/23) | 2026-11-14 | `MarceloDetlefsen` | docs: ADR 0001 farm polygons storage (GeoJSON jsonb for MVP) |
| [#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/24) | 2026-11-14 | `MarceloDetlefsen` | feat: farms CRUD with ownership checks and priorities (BE-020, BE-025) |
| [#25](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/25) | 2026-11-14 | `MarceloDetlefsen` | feat: auth MVP register, login, refresh, logout, /me (BE-010) |
| [#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/26) | 2026-11-14 | `MarceloDetlefsen` | feat: farm data upload CSV and GeoJSON with DEC-005 validation (BE-030) |
| [#27](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/27) | 2026-11-14 | `MarceloDetlefsen` | feat: ENSO series, scenario simulation, and rotation recommendations (BE-045, BE-050) |
| [#29](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/29) | 2026-11-14 | `MarceloDetlefsen` | feat(demo): DEMO_MODE offline snapshots and idempotent seed-demo (BE-085) |
| [#30](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/30) | 2026-11-14 | `MarceloDetlefsen` | fix(config): CORS_ORIGINS alias, non-local JWT_SECRET guard, and ops-env docs |
| [#31](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/31) | 2026-11-14 | `MarceloDetlefsen` | feat(contract): canonical OpenAPI source of truth, disclaimer/provenance, and frontend migration guide |
| [#33](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/33) | 2026-11-14 | `MarceloDetlefsen` | feat(ml): expected ml-service contract, HTTP contract tests, and fixture fallback (BE-048) |
| [#34](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/34) | 2026-11-14 | `MarceloDetlefsen` | chore(deploy): deployment readiness checklist and verified container startup |
| [#35](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/35) | 2026-11-14 | `angcoder-c` | feat(cd): despliegue continuo de core-api a Cloud Run con WIF |
| [#36](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/36) | 2026-11-14 | `eldmark` | docs: add AI use traceability and public access rules (G11, G12) |
| [#38](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/38) | 2026-11-15 | `eldmark` | fix: remove fixed demo password and rotate seeded credential |
| [#39](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/39) | 2026-11-15 | `MarceloDetlefsen` | feat(auth): passwordless demo guest access (BE-090) |
| [#40](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/40) | 2026-11-15 | `MarceloDetlefsen` | test(ml): real local HTTP integration with agrofarm-analytic ml-service |
| [#41](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/41) | 2026-11-15 | `MarceloDetlefsen` | docs(deploy): use /readyz for Cloud Run smoke tests and update progress |
| [#42](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/42) | 2026-11-15 | `eldmark` | feat: add read-only NASA POWER climate endpoint |
| [#43](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/43) | 2026-11-15 | `eldmark` | fix(cd): stop calling /healthz from outside Cloud Run in the post-deploy smoke test |
| [#44](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/44) | 2026-11-15 | `eldmark` | feat: authenticate core-api to the private ml-service with a Google identity token |
| [#45](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/45) | 2026-11-15 | `MarceloDetlefsen` | docs(ai): add MarceloDetlefsen to AI_USAGE.md (G11) |
| [#46](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/46) | 2026-11-15 | `MarceloDetlefsen` | docs(contract): frontend passwordless demo flow guide and snapshot examples |
| [#47](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/47) | 2026-11-15 | `MarceloDetlefsen` | docs(progress): update PROGRESS.md with PRs #45 and #46 |
| [#48](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/48) | 2026-11-15 | `MarceloDetlefsen` | docs(ai): record Gemini 4 Hydrogen in AI_USAGE.md |
| [#49](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/49) | 2026-11-15 | `eldmark` | feat: let demo mode call ml-service, with cached answers as fallback (BE-091) |
| [#50](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/50) | 2026-11-15 | `eldmark` | fix: configure live staging ML and check demo behavior in CD |
| [#51](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/51) | 2026-11-15 | `eldmark` | feat: add authenticated farm photo screening through private ML |
| [#52](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/52) | 2026-11-15 | `eldmark` | feat: connect farm scenarios to trained regional NDVI outlook |
| [#53](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/53) | 2026-11-15 | `eldmark` | fix: serve the real NOAA CPC ENSO series instead of a few invented months |
| [#54](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/54) | 2026-11-15 | `eldmark` | fix: keep one ml-service instance warm in staging |
| [#55](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/55) | 2026-11-15 | `eldmark` | fix: let the post-deploy smoke check wait for a cold ml-service |
| [#56](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/56) | 2026-11-15 | `eldmark` | fix: demo guest cap counts the last 24 hours only, default 1000 |
| [#57](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/57) | 2026-11-15 | `eldmark` | chore: set the six team members as code owners (DEC-007) |

## Remaining open items and known risks

- The release pull request `develop` -> `main` is a human decision; production has not been deployed from it.
- Operations notes in [`ops-env.md`](ops-env.md): the pending `terraform apply` for staging and the CI/CD billing failure seen on 2026-11-16.
- Operations in the OpenAPI contract still marked `x-stub: true` (served from example data): `GET /v1/farms/{farm_id}/insights`, `GET /v1/layers`, `GET /v1/search`.
- Refresh token reuse detection (family revocation) was deferred in the auth MVP (PR #25); not confirmed as implemented since.
- Responses are decision support, never certain predictions; every recommendation keeps its disclaimer and provenance (rule G10).
- Port `5432` busy locally: use `DB_PORT=5433` with the make targets below.

## Run commands

```bash
cp .env.example .env
make dev                # API on http://localhost:8080 and PostgreSQL
make check              # lint, typecheck, tests with the coverage gate
make seed-demo          # idempotent demo data (needs DEMO_MODE=true to use the guest flow)
make export-openapi     # regenerate docs/contract/openapi.yaml from the app
DB_PORT=5433 make check # when host port 5432 is taken
```

Environment variables are documented in [`ops-env.md`](ops-env.md); deployment steps in [`deploy-checklist.md`](deploy-checklist.md).
