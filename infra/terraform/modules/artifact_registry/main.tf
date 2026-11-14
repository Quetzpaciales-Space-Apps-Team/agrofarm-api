variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "repository_id" {
  type    = string
  default = "agrofarm"
}

resource "google_artifact_registry_repository" "docker" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  description   = "Docker images for AgroFarm microservices (core-api, ml-service, data-service, frontend)"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-recent-revisions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }
}

output "repository_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "repository_name" {
  value = google_artifact_registry_repository.docker.name
}
