variable "project_id" {
  description = "Google Cloud project ID hosting AgroFarm resources"
  type        = string
}

variable "region" {
  description = "Primary GCP region for Cloud Run, Cloud SQL, Artifact Registry and buckets"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment suffix (staging or prod)"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either 'staging' or 'prod'."
  }
}

variable "github_org" {
  description = "GitHub organization allowed to authenticate via Workload Identity Federation"
  type        = string
  default     = "Quetzpaciales-Space-Apps-Team"
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins for core-api"
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "core_api_image" {
  description = "Container image URI for core-api Cloud Run service and migration job"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "ml_service_image" {
  description = "Container image URI for ml-service Cloud Run service"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "data_service_image" {
  description = "Container image URI for data-service Cloud Run job"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "frontend_image" {
  description = "Container image URI for frontend Cloud Run service"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
