# Implementation Assumptions (Hackathon MVP)

This file records pragmatic decisions made during the NASA Space Apps Challenge 2026 sprint to keep `core-api` unblocked and shippable before code freeze (Sunday 2026-11-15 16:00 local time).

## 1. Farm Polygon Storage (`BE-015` / `BE-020`)
- **Decision:** Store farm polygons as RFC 7946 GeoJSON (`EPSG:4326`) in a PostgreSQL `jsonb` column alongside precomputed `area_ha`, `centroid_lat`, and `centroid_lon`.
- **Why:** Keeps `pgvector/pgvector:pg17` and Cloud SQL free of extra PostGIS/GEOS build complexity while satisfying all MVP CRUD and upload requirements.

## 2. Provisional Pilot Polygon (`DEC-005` / `BE-085`)
- **Decision:** Since `DEC-003` is not yet finalized, examples and demo seeds use a provisional polygon near the INSIVUMEH reference station in Guatemala City (`14.5892, -90.5315`), explicitly marked `provisional: true`.

## 3. Auth MVP Scope (`BE-010`)
- **Decision:** Implement `/v1/auth/register`, `/v1/auth/login`, `/v1/auth/refresh`, `/v1/auth/logout`, and `/v1/me` with Argon2/PBKDF2 password hashing and signed JWTs + DB-backed refresh tokens.
- **Deferred:** Refresh token reuse-detection family revocation (second iteration only if all MVP blocks finish before freeze).

## 4. `ml-service` Contract & `ML_MODE=http|fixture` (`BE-045` / `BE-050`)
- **Decision:** `agrofarm-analytic/services/ml/docs/contract/openapi.yaml` does not exist yet (`ML-001` is open). `core-api` defines an explicit `MLClient` interface with `ML_MODE=fixture|http` (default `fixture` for offline/local safety) and an explicit mapper that guarantees all required fields (`why`, `evidence`, `benefits`, `gaps`, `risks`, `needs_local_review`, `uncertainty`, priority scores, and provenance).

## 5. CORS & JWT Configuration (`fix/config-cors-jwt`)
- **Decision:** `Settings` accepts both `CORS_ALLOWED_ORIGINS` (JSON list or comma-separated) and `CORS_ORIGINS` (used by `infra/terraform/main.tf`) without modifying Terraform; when `ENVIRONMENT != "local"`, empty or default `JWT_SECRET` fails startup validation.

## 6. Canonical OpenAPI & Provenance (`feat/contract-source-of-truth`)
- **Decision:** `agrofarm-api/docs/contract/openapi.yaml` is the single source of truth for frontend and backend. `Provenance.data_versions` uses a flat `dict[str, str]` (simpler than nested dataset arrays) and `Provenance` always includes `model_name`, `model_version`, `data_versions`, `input_hash`, and `generated_at`. `disclaimer` is included on `/v1/climate/enso`, `/v1/scenarios/simulate`, and `/v1/farms/{farm_id}/recommendations`.

## 7. Passwordless Demo Guest Access (`BE-090`)
- **Decision:** `POST /v1/auth/demo` provisions an isolated ephemeral guest user (`demo-guest-<uuid>@demo.agrofarm.invalid`) with a random discarded password, clones the provisional Guatemala City pilot farm and default priorities, and returns an access token + `farm_id` + `is_demo_guest: true`. Protected by an in-memory per-IP rate limiter (`DEMO_RATE_LIMIT_PER_MINUTE=20`), a max-guest cap (`DEMO_MAX_GUESTS=200`), and `make purge-demo-guests` (`>24h`).
- **Why:** Allows judges to test the full flow in a private browser window without publishing any credentials while keeping real user data strictly isolated.

## 8. NASA POWER Climate Series (`GET /v1/climate/nasa-power`)
- **Decision:** The endpoint serves the static snapshot `src/core_api/demo_snapshots/nasa_power.json` (372 monthly rows, 1995-01 to 2025-12, built from NASA POWER daily data at 14.59, -90.53) in every mode, with the same auth as `/v1/climate/enso`. Values are served unchanged; a missing value is `null`, never 0 or -999. The response carries `resolution_note` (a reanalysis grid cell of about 50 km, not a station) and the `disclaimer`.
- **Why:** The frontend can show real NASA data now. Reading it from the `data-service` `clean/` datasets by manifest version is the later step; the snapshot is not refreshed automatically.
