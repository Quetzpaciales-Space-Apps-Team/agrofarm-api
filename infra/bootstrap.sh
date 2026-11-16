#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GCP_PROJECT_ID:-}" ]]; then
  echo "Error: GCP_PROJECT_ID environment variable is required." >&2
  exit 1
fi

REGION="${GCP_REGION:-us-central1}"
STATE_BUCKET="${GCP_PROJECT_ID}-tfstate"

echo "Setting active GCP project to ${GCP_PROJECT_ID}..."
gcloud config set project "${GCP_PROJECT_ID}"

echo "Enabling base bootstrap APIs..."
gcloud services enable \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  serviceusage.googleapis.com \
  sts.googleapis.com \
  --project="${GCP_PROJECT_ID}"

if gcloud storage buckets describe "gs://${STATE_BUCKET}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
  echo "State bucket gs://${STATE_BUCKET} already exists."
else
  echo "Creating Terraform state bucket gs://${STATE_BUCKET} in ${REGION}..."
  gcloud storage buckets create "gs://${STATE_BUCKET}" \
    --project="${GCP_PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --public-access-prevention
fi

echo "Enabling object versioning on gs://${STATE_BUCKET}..."
gcloud storage buckets update "gs://${STATE_BUCKET}" \
  --project="${GCP_PROJECT_ID}" \
  --versioning

echo "Bootstrap complete. Initialize Terraform with:"
echo "  terraform -chdir=infra/terraform init -backend-config=\"bucket=${STATE_BUCKET}\" -backend-config=\"prefix=agrofarm/staging\""
