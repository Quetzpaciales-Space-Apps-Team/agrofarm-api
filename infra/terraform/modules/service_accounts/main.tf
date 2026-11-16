variable "project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "bucket_names" {
  type = map(string)
}

variable "secret_ids" {
  type = map(string)
}

locals {
  accounts = {
    core_api     = "sa-core-api-${var.environment}"
    ml_service   = "sa-ml-service-${var.environment}"
    data_service = "sa-data-service-${var.environment}"
    frontend     = "sa-frontend-${var.environment}"
    ci_deployer  = "sa-ci-deployer-${var.environment}"
  }
}

resource "google_service_account" "sa" {
  for_each     = local.accounts
  project      = var.project_id
  account_id   = each.value
  display_name = "AgroFarm ${each.key} (${var.environment})"
}

# core-api: Cloud SQL client
resource "google_project_iam_member" "core_api_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.sa["core_api"].email}"
}

# core-api: read clean bucket, read/write uploads bucket
resource "google_storage_bucket_iam_member" "core_api_clean_reader" {
  bucket = var.bucket_names["clean"]
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.sa["core_api"].email}"
}

resource "google_storage_bucket_iam_member" "core_api_uploads_rw" {
  bucket = var.bucket_names["uploads"]
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.sa["core_api"].email}"
}

# ml-service: read-only access to clean and models buckets
resource "google_storage_bucket_iam_member" "ml_service_clean_reader" {
  bucket = var.bucket_names["clean"]
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.sa["ml_service"].email}"
}

resource "google_storage_bucket_iam_member" "ml_service_models_reader" {
  bucket = var.bucket_names["models"]
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.sa["ml_service"].email}"
}

# data-service: read/write access to raw and clean buckets
resource "google_storage_bucket_iam_member" "data_service_raw_rw" {
  bucket = var.bucket_names["raw"]
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.sa["data_service"].email}"
}

resource "google_storage_bucket_iam_member" "data_service_clean_rw" {
  bucket = var.bucket_names["clean"]
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.sa["data_service"].email}"
}

# Secret Manager accessors: core-api reads db_url and jwt_secret
resource "google_secret_manager_secret_iam_member" "core_api_db_secret" {
  project   = var.project_id
  secret_id = var.secret_ids["database_url"]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa["core_api"].email}"
}

resource "google_secret_manager_secret_iam_member" "core_api_jwt_secret" {
  project   = var.project_id
  secret_id = var.secret_ids["jwt_secret"]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa["core_api"].email}"
}

# Secret Manager accessors: data-service reads external provider credentials
resource "google_secret_manager_secret_iam_member" "data_service_earthdata" {
  project   = var.project_id
  secret_id = var.secret_ids["earthdata_token"]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa["data_service"].email}"
}

resource "google_secret_manager_secret_iam_member" "data_service_meteomatics" {
  project   = var.project_id
  secret_id = var.secret_ids["meteomatics_credentials"]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa["data_service"].email}"
}

resource "google_secret_manager_secret_iam_member" "data_service_cds" {
  project   = var.project_id
  secret_id = var.secret_ids["cds_api_key"]
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.sa["data_service"].email}"
}

# ci-deployer: Artifact Registry writer, Cloud Run admin, and ServiceAccountUser on runtime SAs only
resource "google_project_iam_member" "ci_deployer_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.sa["ci_deployer"].email}"
}

resource "google_project_iam_member" "ci_deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.sa["ci_deployer"].email}"
}

resource "google_service_account_iam_member" "ci_deployer_act_as_runtime" {
  for_each           = toset(["core_api", "ml_service", "data_service", "frontend"])
  service_account_id = google_service_account.sa[each.key].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.sa["ci_deployer"].email}"
}

output "emails" {
  value = { for k, v in google_service_account.sa : k => v.email }
}

output "names" {
  value = { for k, v in google_service_account.sa : k => v.name }
}
