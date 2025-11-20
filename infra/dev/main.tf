provider "google" {
  project = var.project_id<REDACTED_PII>= var.project_id
  region  = var.region
}

# Enable required APIs for the project
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",             # Cloud Run
    "artifactregistry.googleapis.com",  # Artifact Registry
    "cloudbuild.googleapis.com",        # Cloud Build
    "iamcredentials.googleapis.com",    # IAM Credentials
    "compute.googleapis.com",           # Compute Engine (often a dependency)
  ])
  service            = each.key
  disable_on_destroy = false
}

# Example: Create a dedicated service account for the Cloud Run instance
# resource "google_service_account" "run_sa" {
#   account_id   = "agentic-dsta-dev-run"
#   display_name = "Agentic DSTA DEV Cloud Run SA"
#   project      = var.project_id
# }

module "cloud_run_service" {
  source       = "../../modules/cloud_run_service"
  service_name = var.service_name
  project_id   = var.project_id
  location     = var.region
  image_url    = var.image_url != "" ? var.image_url : "gcr.io/cloudrun/hello" # Placeholder image
  # service_account_email = google_service_account.run_sa.email
  service_account_email = var.service_account_email # Or use a manually created one

  env_vars = {
    FLASK_ENV = "production"
    PORT      = "8080"
    # Add other environment variables needed by the app
  }
  # depends_on = [google_project_service.apis]
}
