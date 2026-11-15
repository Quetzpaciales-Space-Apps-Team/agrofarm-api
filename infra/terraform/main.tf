module "apis" {
  source     = "./modules/apis"
  project_id = var.project_id
}

module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
  depends_on = [module.apis]
}

module "storage" {
  source      = "./modules/storage"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  depends_on  = [module.apis]
}

module "cloud_sql" {
  source      = "./modules/cloud_sql"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  db_tier     = var.db_tier
  depends_on  = [module.apis]
}

module "service_accounts" {
  source       = "./modules/service_accounts"
  project_id   = var.project_id
  environment  = var.environment
  bucket_names = module.storage.bucket_names
  secret_ids   = module.cloud_sql.secret_ids
  depends_on   = [module.apis]
}

module "wif" {
  source              = "./modules/wif"
  project_id          = var.project_id
  environment         = var.environment
  github_org          = var.github_org
  ci_deployer_sa_name = module.service_accounts.names["ci_deployer"]
  depends_on          = [module.apis]
}

module "ml_service" {
  source                = "./modules/cloud_run_service"
  project_id            = var.project_id
  region                = var.region
  service_name          = "ml-service-${var.environment}"
  image                 = var.ml_service_image
  service_account_email = module.service_accounts.emails["ml_service"]
  allow_unauthenticated = false
  invoker_service_account_emails = toset([
    module.service_accounts.emails["core_api"],
  ])
  cpu    = "1"
  memory = "1Gi"
  env_vars = {
    LOG_LEVEL         = "INFO"
    GCS_BUCKET_CLEAN  = module.storage.bucket_names["clean"]
    GCS_BUCKET_MODELS = module.storage.bucket_names["models"]
  }
}

module "core_api_service" {
  source                    = "./modules/cloud_run_service"
  project_id                = var.project_id
  region                    = var.region
  service_name              = "core-api-${var.environment}"
  image                     = var.core_api_image
  service_account_email     = module.service_accounts.emails["core_api"]
  cloud_sql_connection_name = module.cloud_sql.connection_name
  allow_unauthenticated     = true
  cpu                       = "1"
  memory                    = "512Mi"
  env_vars = {
    LOG_LEVEL          = "INFO"
    CLOUD_SQL_INSTANCE = module.cloud_sql.connection_name
    ML_SERVICE_URL     = module.ml_service.service_url
    ML_MODE            = "http"
    ML_AUTH            = "google_id_token"
    CORS_ORIGINS       = var.cors_origins
    GCS_BUCKET_CLEAN   = module.storage.bucket_names["clean"]
    GCS_BUCKET_UPLOADS = module.storage.bucket_names["uploads"]
  }
  secret_env_vars = {
    DATABASE_URL = module.cloud_sql.secret_ids["database_url"]
    JWT_SECRET   = module.cloud_sql.secret_ids["jwt_secret"]
  }
}

module "frontend_service" {
  source                = "./modules/cloud_run_service"
  project_id            = var.project_id
  region                = var.region
  service_name          = "frontend-${var.environment}"
  image                 = var.frontend_image
  service_account_email = module.service_accounts.emails["frontend"]
  allow_unauthenticated = true
  cpu                   = "1"
  memory                = "256Mi"
  env_vars = {
    API_BASE_URL = module.core_api_service.service_url
    USE_MOCKS    = "false"
  }
}

module "core_api_migrate_job" {
  source                    = "./modules/cloud_run_job"
  project_id                = var.project_id
  region                    = var.region
  job_name                  = "core-api-migrate-${var.environment}"
  image                     = var.core_api_image
  service_account_email     = module.service_accounts.emails["core_api"]
  cloud_sql_connection_name = module.cloud_sql.connection_name
  command                   = ["alembic"]
  args                      = ["upgrade", "head"]
  env_vars = {
    LOG_LEVEL          = "INFO"
    CLOUD_SQL_INSTANCE = module.cloud_sql.connection_name
  }
  secret_env_vars = {
    DATABASE_URL = module.cloud_sql.secret_ids["database_url"]
  }
}

module "data_service_job" {
  source                = "./modules/cloud_run_job"
  project_id            = var.project_id
  region                = var.region
  job_name              = "data-service-${var.environment}"
  image                 = var.data_service_image
  service_account_email = module.service_accounts.emails["data_service"]
  env_vars = {
    LOG_LEVEL        = "INFO"
    GCS_BUCKET_RAW   = module.storage.bucket_names["raw"]
    GCS_BUCKET_CLEAN = module.storage.bucket_names["clean"]
  }
  secret_env_vars = {
    EARTHDATA_TOKEN         = module.cloud_sql.secret_ids["earthdata_token"]
    METEOMATICS_CREDENTIALS = module.cloud_sql.secret_ids["meteomatics_credentials"]
    CDS_API_KEY             = module.cloud_sql.secret_ids["cds_api_key"]
  }
}
