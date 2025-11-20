resource "google_cloud_run_v2_service" "default" {
  provider = google-beta # v2 service often requires beta provider

  name     = var.service_name
  location = var.location
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL" # Adjust as needed (e.g., INGRESS_TRAFFIC_INTERNAL_ONLY)

  template {
    containers {
      image = var.image_url
      ports { container_port = var.container_port }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
      # Add resource limits if necessary
      # resources {
      #   limits = {
      #     cpu    = "1000m"
      #     memory = "512Mi"
      #   }
      # }
    }
    service_account = var.service_account_email
    # max_instance_request_concurrency = 80
    # timeout = "300s"
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image, # Allow image to be updated by CI/CD
    ]
  }
}

# IAM policy for invoker role
data "google_iam_policy" "invoker" {
  binding {
    role = "roles/run.invoker"
    members = var.allow_unauthenticated ? ["allUsers"] : [
      # Add specific service accounts or groups allowed to invoke
      # Example: "serviceAccount:your-caller-sa@your-project.iam.gserviceaccount.com"
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "invoker" {
  location    = google_cloud_run_v2_service.default.location
  project     = google_cloud_run_v2_service.default.project
  <REDACTED_PII>ame
  policy_data = data.google_iam_policy.invoker.policy_data
}

# Output the URL of the service
output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.uri
}
