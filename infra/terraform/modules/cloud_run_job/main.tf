variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "job_name" {
  type = string
}

variable "image" {
  type = string
}

variable "service_account_email" {
  type = string
}

variable "command" {
  type    = list(string)
  default = []
}

variable "args" {
  type    = list(string)
  default = []
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "secret_env_vars" {
  type    = map(string)
  default = {}
}

variable "cloud_sql_connection_name" {
  type    = string
  default = ""
}

resource "google_cloud_run_v2_job" "job" {
  project  = var.project_id
  name     = var.job_name
  location = var.region

  template {
    template {
      service_account = var.service_account_email
      max_retries     = 1
      timeout         = "1800s"

      dynamic "volumes" {
        for_each = var.cloud_sql_connection_name != "" ? [var.cloud_sql_connection_name] : []
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = [volumes.value]
          }
        }
      }

      containers {
        image   = var.image
        command = var.command
        args    = var.args

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        dynamic "volume_mounts" {
          for_each = var.cloud_sql_connection_name != "" ? [1] : []
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secret_env_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }
}

output "job_name" {
  value = google_cloud_run_v2_job.job.name
}
