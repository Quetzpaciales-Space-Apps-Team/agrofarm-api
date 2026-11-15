# Deployment Readiness Checklist (`core-api`)

This checklist covers container verification, environment variables, database migrations, demo seeding, and public smoke tests for `https://agrofarming.site` (without modifying Terraform or GCP resources directly).

---

## 1. Required Environment Variables by Environment

| Variable | `local` | `staging` | `prod` |
|---|---|---|---|
| `DATABASE_URL` | Local Postgres DSN (`5432` or `5433`) | Cloud SQL Secret Manager | Cloud SQL Secret Manager |
| `ENVIRONMENT` | `local` | `staging` | `prod` |
| `JWT_SECRET` | Optional (dev default allowed) | **Required** (Secret Manager, non-default) | **Required** (Secret Manager, non-default) |
| `CORS_ALLOWED_ORIGINS` (or `CORS_ORIGINS`) | `["http://localhost:5173","https://agrofarming.site"]` | `https://agrofarming.site` | `https://agrofarming.site` |
| `ML_MODE` | `fixture` | `fixture` (until `ml-service` HTTP endpoints land) | `fixture` or `http` |
| `ML_SERVICE_URL` | `http://localhost:8081` | Cloud Run `ml-service` URL | Cloud Run `ml-service` URL |
| `DEMO_MODE` | `false` (or `true` for offline demo) | `true` for hackathon fallback, else `false` | `false` (or `true` only for demo fallback) |

---

## 2. Container Build, Migration, and Demo Seed Commands

```bash
# Build image locally
docker build -t core-api:local .

# Run migrations inside the container
docker run --rm \
  -e DATABASE_URL="$DATABASE_URL" \
  core-api:local \
  alembic upgrade head

# Seed demo data; the account receives a random, discarded password hash
docker run --rm \
  -e DATABASE_URL="$DATABASE_URL" \
  core-api:local \
  python -m core_api.seed_demo
```

Before making the service public, run the seeder against the target database once. It replaces any earlier seeded password hash and revokes refresh tokens. Existing access tokens expire within their configured lifetime. The no-login public demo entry is a separate pending feature; seeding alone does not provide it.

---

## 3. Public URL Smoke Tests (`curl` + CORS `https://agrofarming.site`)

Replace `API_URL` with the deployed `core-api` URL:

```bash
export API_URL="https://core-api-staging-7l2bzjrqpq-uc.a.run.app"

# 1. Readiness (Cloud Run reserves /healthz at its edge, so external smoke tests use /readyz)
curl -sf "$API_URL/readyz"

# 2. CORS preflight from https://agrofarming.site
curl -si -X OPTIONS "$API_URL/v1/auth/login" \
  -H "Origin: https://agrofarming.site" \
  -H "Access-Control-Request-Method: POST" | grep -i "access-control-allow-origin"

# 3. Verify the public no-login demo in a private browser window before submission.
# Do not put user passwords or demo credentials in commands, docs, or submission materials.
```

---

## 4. Remaining Infrastructure Tasks (`angcoder-c` / `OPS-001..004`)

- **GCP Foundation (`OPS-001`):** Provision staging/prod Cloud SQL, Secret Manager values (`database_url`, `jwt_secret`), and Cloud Run services via `infra/terraform`.
- **Custom Domain & CORS (`OPS-002`):** Map `https://agrofarming.site` (frontend) and API subdomain on the same registrable domain so `httpOnly; Secure; SameSite=Lax` refresh cookies work, and set `CORS_ORIGINS=https://agrofarming.site` in `envs/*.tfvars`.
- **CD Workflows:** Add GitHub Actions deploy workflows (`develop` -> staging, `main` -> prod) using WIF (`sa-ci-deployer`).
- **Branch Protection (`OPS-004`):** Enforce `ci-gate` and PR review rules on `develop` and `main`, and open the final `develop` -> `main` release PR before freeze.

---

## 5. Enabling `ML_MODE=http` (`ml-service` Integration)

`core-api` is verified end-to-end against `agrofarm-analytic/services/ml` (`agrofarm_ml`) over HTTP (`tests/integration/test_ml_service_real_http.py`). Staging and production remain on `DEMO_MODE=true` (`ML_MODE=fixture`) until `ml-service` is deployed to Cloud Run (`OPS-001` / `ML-001`).

To run with the real `ml-service` locally:
```bash
# Terminal 1 (agrofarm-analytic/services/ml)
uv run uvicorn agrofarm_ml.main:create_app --factory --host 127.0.0.1 --port 8081

# Terminal 2 (agrofarm-api)
ML_MODE=http ML_SERVICE_URL=http://127.0.0.1:8081 DATABASE_URL="$DATABASE_URL" \
  uv run uvicorn core_api.main:create_app --factory --port 8080
```

To enable `ML_MODE=http` in staging/prod once `ml-service` is deployed:
1. Set `ML_SERVICE_URL` to the deployed Cloud Run `ml-service` URL.
2. Set `ML_MODE=http`. To keep the guest demo entry (`DEMO_MODE=true`) and still get live answers, also set `DEMO_ML_SOURCE=live`; with the default `snapshot`, demo mode keeps serving the cached file and the scenario sliders change nothing.
3. Verify `POST /v1/scenarios/simulate` and `POST /v1/farms/{farm_id}/recommendations` return `200`/`201` with `>=3` strategies.
