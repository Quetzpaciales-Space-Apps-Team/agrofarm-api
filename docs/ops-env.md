# Runtime Environment Variables (`core-api`)

All configuration is read from environment variables (or a local `.env` file, never committed).

| Variable | Required | Default | Example | Notes |
|---|---|---|---|---|
| `DATABASE_URL` | Yes | — | `postgresql+psycopg://agrofarm:pass@localhost:5432/agrofarm` | App refuses to start if missing. |
| `ENVIRONMENT` | No | `local` | `staging` / `prod` | Non-`local` enforces explicit non-default `JWT_SECRET`. |
| `JWT_SECRET` | Yes when `ENVIRONMENT != local` | `local-dev-jwt-secret-change-in-production` | `$(openssl rand -hex 32)` | App refuses to start if empty or default in `staging`/`prod`. |
| `JWT_ISSUER` | No | `agrofarm-core-api` | `agrofarm-core-api` | JWT `iss` claim. |
| `JWT_AUDIENCE` | No | `agrofarm-clients` | `agrofarm-clients` | JWT `aud` claim. |
| `ACCESS_TOKEN_TTL_SECONDS` | No | `900` | `900` | Access token lifetime (15 min). |
| `REFRESH_TOKEN_TTL_SECONDS` | No | `604800` | `604800` | Refresh token lifetime (7 days). |
| `CORS_ALLOWED_ORIGINS` (or `CORS_ORIGINS`) | No (recommended in prod) | `[]` | `["http://localhost:5173","https://agrofarming.site"]` or `https://agrofarming.site` | Wildcard `*` is rejected. Accepts JSON list or comma-separated string. |
| `LOG_LEVEL` | No | `INFO` | `INFO` | Standard Python logging level. |
| `ML_MODE` | No | `fixture` | `fixture` / `http` | `http` calls `ML_SERVICE_URL`; `fixture` uses deterministic local outputs. |
| `ML_SERVICE_URL` | No | `http://localhost:8081` | `https://ml-service-....run.app` | Base URL for `ml-service` when `ML_MODE=http`. |
| `ML_TIMEOUT_SECONDS` | No | `5.0` | `5.0` | HTTP client timeout when calling `ml-service`. |
| `DEMO_MODE` | No | `false` | `false` / `true` | Enables `POST /v1/auth/demo` guest sessions and, unless `DEMO_ML_SOURCE=live`, serves `cached_demo` snapshots instead of calling `ml-service`. Never auto-seeds DB. |
| `DEMO_ML_SOURCE` | No | `snapshot` | `snapshot` / `live` | Only read when `DEMO_MODE=true`. `snapshot`: every simulation and rotation answer is the same cached file, whatever the scenario. `live`: with `ML_MODE=http`, calls `ml-service` and uses the cached file only when that call fails; the provenance then says `cached_demo`. |
| `DEMO_RATE_LIMIT_PER_MINUTE` | No | `20` | `20` | Per-IP sliding-window limit for `POST /v1/auth/demo`. |
| `DEMO_MAX_GUESTS` | No | `1000` | `1000` | Maximum `demo-guest-*` accounts created in the last 24 hours before `503`. Older guests do not count; `make purge-demo-guests` removes them. |
| `MAX_UPLOAD_BYTES` | No | `2097152` | `2097152` | 2 MiB streaming cap for farm CSV/GeoJSON uploads. |
| `RAW_UPLOADS_DIR` | No | `data/raw/uploads` | `data/raw/uploads` | Local raw upload storage path. |
