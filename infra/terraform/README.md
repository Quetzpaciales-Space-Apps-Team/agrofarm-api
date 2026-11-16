# AgroFarm GCP Terraform Foundation (`OPS-001`)

This directory provisions all Google Cloud Platform infrastructure for AgroFarm (`staging` and `prod` environments) in a single GCP project (`us-central1`), as specified in `ADR 0003`.

## Modules

- `modules/apis`: Enables required GCP APIs (`run`, `sqladmin`, `artifactregistry`, `secretmanager`, `iamcredentials`, `sts`, `storage`, `cloudresourcemanager`).
- `modules/artifact_registry`: Creates the shared `agrofarm` Docker repository (`us-central1-docker.pkg.dev/<project>/agrofarm`) when `environment == "staging"` or references it across environments.
- `modules/storage`: Creates private GCS buckets (`raw`, `clean`, `models`, `uploads`) with uniform bucket-level access and versioning.
- `modules/cloud_sql`: Provisions PostgreSQL 16 (`agrofarm-pg-<env>`) with `cloudsql.iam_authentication`, `deletion_protection = true`, generated password stored in Secret Manager, and Secret Manager containers for application and external API secrets.
- `modules/service_accounts`: Creates dedicated least-privilege runtime service accounts (`sa-core-api-<env>`, `sa-ml-service-<env>`, `sa-data-service-<env>`, `sa-frontend-<env>`) and `sa-ci-deployer-<env>`.
- `modules/wif`: Configures Workload Identity Federation pool and OIDC provider restricted to `assertion.repository_owner == var.github_org` with per-repository bindings.
- `modules/cloud_run_service`: Reusable Cloud Run v2 service module (`min_instance_count` variable, default 0; staging keeps one `ml-service` instance warm with `ml_min_instances = 1`; `/healthz` startup and liveness probes, optional Cloud SQL mount, IAM invoker bindings).
- `modules/cloud_run_job`: Reusable Cloud Run v2 job module (`core-api-migrate-<env>` and `data-service-<env>`).

## Usage

```bash
# 1. Bootstrap remote state bucket once
GCP_PROJECT_ID=<project-id> ../bootstrap.sh

# 2. Validate locally without backend
terraform init -backend=false
terraform fmt -check -recursive
terraform validate

# 3. Plan / Apply staging
terraform init -backend-config="bucket=<project-id>-tfstate" -backend-config="prefix=agrofarm/staging"
terraform plan -var-file="envs/staging.tfvars" -var="project_id=<project-id>"
```
