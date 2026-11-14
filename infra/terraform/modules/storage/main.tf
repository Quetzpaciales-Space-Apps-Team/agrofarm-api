variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment" {
  type = string
}

locals {
  buckets = {
    raw     = "${var.project_id}-raw-${var.environment}"
    clean   = "${var.project_id}-clean-${var.environment}"
    models  = "${var.project_id}-models-${var.environment}"
    uploads = "${var.project_id}-uploads-${var.environment}"
  }
}

resource "google_storage_bucket" "buckets" {
  for_each                    = local.buckets
  project                     = var.project_id
  name                        = each.value
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = var.environment == "staging"

  versioning {
    enabled = true
  }
}

output "bucket_names" {
  value = { for k, b in google_storage_bucket.buckets : k => b.name }
}
