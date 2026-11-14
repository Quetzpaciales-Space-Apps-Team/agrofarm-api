variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

variable "db_tier" {
  type = string
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

resource "google_sql_database_instance" "postgres" {
  project             = var.project_id
  name                = "agrofarm-pg-${var.environment}"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true

  settings {
    tier              = var.db_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = 10
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "prod"
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
}

resource "google_sql_database" "agrofarm" {
  project  = var.project_id
  name     = "agrofarm"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  project  = var.project_id
  name     = "agrofarm_app"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

locals {
  secret_names = {
    database_url            = "database-url-${var.environment}"
    jwt_secret              = "jwt-secret-${var.environment}"
    earthdata_token         = "earthdata-token-${var.environment}"
    meteomatics_credentials = "meteomatics-credentials-${var.environment}"
    cds_api_key             = "cds-api-key-${var.environment}"
  }
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = local.secret_names
  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.secrets["database_url"].id
  secret_data = "postgresql+psycopg://${google_sql_user.app.name}:${random_password.db_password.result}@/${google_sql_database.agrofarm.name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.secrets["jwt_secret"].id
  secret_data = random_password.jwt_secret.result
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "secret_ids" {
  value = { for k, s in google_secret_manager_secret.secrets : k => s.secret_id }
}
