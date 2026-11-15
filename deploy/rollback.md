# Cloud Run Rollback Runbook (`core-api`)

This document describes how to roll back `core-api` in `staging` or `production` if a deployment introduces a regression after passing `/healthz` and `/readyz`.

## 1. Automated Safeguards During Deployment

1. **Pre-traffic Migrations:** `.github/workflows/cd.yml` updates and executes the `core-api-migrate-<env>` Cloud Run Job (`alembic upgrade head`) with `--wait` **before** updating the `core-api-<env>` Cloud Run service. If the migration job fails, the new service revision is never deployed.
2. **Startup and Liveness Probes:** Cloud Run waits for `/healthz` to return `200 OK` on the new revision before shifting traffic away from the previous healthy revision.
3. **Zero-Leakage Credentials:** All deployment authentication uses Workload Identity Federation (`google-github-actions/auth@v2`) backed by encrypted GitHub Environment Secrets (`GCP_WIF_PROVIDER`, `GCP_SA_CI_DEPLOYER`, `GCP_PROJECT_ID`, `GCP_REGION`, `GAR_REPOSITORY`).
4. **Staging demo behavior:** The staging deployment sets `ML_MODE=http`, `ML_AUTH=google_id_token`, `DEMO_MODE=true`, `DEMO_ML_SOURCE=live`, and discovers `ML_SERVICE_URL` from `ml-service-staging`. These values match Terraform's staging configuration. After `/readyz`, `python3 deploy/smoke_demo.py "$SERVICE_URL"` enters as a temporary guest, checks that changing rainfall changes the simulation median, and requests at least three strategies including the current rotation. Cached or fixture provenance fails the check. No guest token or response body is logged. The guest and generated recommendation are subject to the existing demo-guest cleanup process.

A failed behavioral check marks CD as failed **after traffic has switched**; it does not roll back automatically. Follow the traffic rollback procedure below if needed. If the error mentions live ML provenance, inspect the core API logs for `ml-service simulate failed; using the offline client` and verify that its service account has `roles/run.invoker` on `ml-service-staging`. The deployment does not change IAM or expose the ML service publicly. Production keeps its existing configuration and readiness check.

---

## 2. Immediate Traffic Rollback (Cloud Run Revision Pinning)

Every push to `develop` or `main` creates an immutable Cloud Run revision backed by an image tagged with the git commit SHA (`<region>-docker.pkg.dev/<project>/<repo>/core-api:<git-sha>`).

### Step 1: List recent revisions

```bash
ENV="staging" # or "prod"
gcloud run revisions list \
  --service="core-api-${ENV}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --limit=5
```

### Step 2: Shift 100% of traffic back to the last known-good revision

```bash
PREVIOUS_REVISION="core-api-staging-00001-xyz"
gcloud run services update-traffic "core-api-${ENV}" \
  --to-revisions="${PREVIOUS_REVISION}=100" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}"
```

### Step 3: Verify health and readiness after traffic shift

```bash
SERVICE_URL="$(gcloud run services describe "core-api-${ENV}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --format='value(status.url)')"
curl -fsS "${SERVICE_URL}/readyz"  # /healthz is reserved at the Cloud Run edge (404 from outside)
curl -fsS "${SERVICE_URL}/readyz"
```

---

## 3. Database Migration Rollback (If Schema Changes Must Be Reverted)

All migrations are designed to be backward-compatible (expand-and-contract). If a migration must be stepped back by one revision:

```bash
gcloud run jobs update "core-api-migrate-${ENV}" \
  --args="downgrade,-1" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}"

gcloud run jobs execute "core-api-migrate-${ENV}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}" \
  --wait

# Restore default upgrade args after downgrade completes
gcloud run jobs update "core-api-migrate-${ENV}" \
  --args="upgrade,head" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT_ID}"
```

---

## 4. Staging Verification Record

Rollback via `gcloud run services update-traffic core-api-staging --to-revisions=<revision>=100` was verified on `staging` in `us-central1` by shifting traffic between revisions and confirming `200 OK` on `/healthz`.
