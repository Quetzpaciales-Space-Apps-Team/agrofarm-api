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
export API_URL="https://api.agrofarming.site"

# 1. Health & readiness
curl -sf "$API_URL/healthz"
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
