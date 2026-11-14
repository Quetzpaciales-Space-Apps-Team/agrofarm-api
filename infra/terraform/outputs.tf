output "artifact_registry_url" {
  description = "Artifact Registry Docker repository URL"
  value       = module.artifact_registry.repository_url
}

output "storage_buckets" {
  description = "Provisioned GCS bucket names by purpose"
  value       = module.storage.bucket_names
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name for the Cloud SQL Auth Proxy / Connector"
  value       = module.cloud_sql.connection_name
}

output "service_account_emails" {
  description = "Emails of runtime and CI deployer service accounts"
  value       = module.service_accounts.emails
}

output "wif_provider_name" {
  description = "Full Workload Identity Provider resource name for google-github-actions/auth"
  value       = module.wif.provider_name
}

output "core_api_url" {
  description = "Public URL of the core-api Cloud Run service"
  value       = module.core_api_service.service_url
}

output "ml_service_url" {
  description = "Internal URL of the ml-service Cloud Run service"
  value       = module.ml_service.service_url
}

output "frontend_url" {
  description = "Public URL of the frontend Cloud Run service"
  value       = module.frontend_service.service_url
}
