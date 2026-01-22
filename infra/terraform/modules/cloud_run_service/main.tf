# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

resource "google_cloud_run_v2_service" "default" {
  provider = google-beta # v2 service often requires beta provider

  name     = var.service_name
  location = var.location
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL" # Adjust as needed (e.g., INGRESS_TRAFFIC_INTERNAL_ONLY)
  deletion_protection = false
  template {
    containers {
      image = var.image_url
      ports { container_port = var.container_port }

      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 10
        period_seconds        = 10
        failure_threshold     = 60 # 60 * 10s = 600s = 10 minutes timeout
        tcp_socket {
          port = var.container_port
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
              secret  = env.value.name
              version = env.value.version
            }
          }
        }
      }
    }
    service_account = var.service_account_email
  }


}

# IAM policy for invoker role
resource "google_cloud_run_v2_service_iam_member" "invoker_all" {
  provider = google-beta
  count    = var.allow_unauthenticated ? 1 : 0
  project  = google_cloud_run_v2_service.default.project
  location = google_cloud_run_v2_service.default.location
  name     = google_cloud_run_v2_service.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}


