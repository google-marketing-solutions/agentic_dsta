provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs for the project
resource "google_project_service" "apis" {
  for_each           = toset(var.gcp_apis)
  service            = each.key
  disable_on_destroy = false
}


locals {
  service_name                       = "${var.resource_prefix}-app"
  run_sa_account_id                  = "${var.resource_prefix}-runner"
  firestore_database_name            = "${var.resource_prefix}-firestore"
  artifact_repository_id             = "${var.resource_prefix}-repo"

  sa_combined_scheduler_job_name     = "${var.resource_prefix}-sa-combined-job"
  google_ads_combined_scheduler_job_name = "${var.resource_prefix}-ga-combined-job"
}

# Service Account for Cloud Run
resource "google_service_account" "run_sa" {
  project      = var.project_id
  account_id   = local.run_sa_account_id
  display_name = var.run_sa_display_name
}

# IAM roles for Service Account
resource "google_project_iam_member" "run_sa_roles" {
  for_each = toset(var.run_sa_roles)
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

#--- Modules ---

module "firestore" {
  source        = "./modules/firestore"
  project_id    = var.project_id
  location_id   = var.region
  database_name = local.firestore_database_name
  database_type = var.firestore_database_type

  depends_on = [google_project_service.apis]
}

module "secret_manager" {
  source                = "./modules/secret_manager"
  project_id            = var.project_id
  service_account_email = google_service_account.run_sa.email
  additional_secrets    = var.additional_secrets
  secret_values         = var.secret_values

  depends_on = [google_project_service.apis]
}

module "apihub" {
  source          = "./modules/apihub"
  project_id      = var.project_id
  location        = var.region
  specs_dir       = "${path.module}/${var.apihub_specs_dir}"
  vertex_location = var.apihub_vertex_location
  account_email   = google_service_account.run_sa.email
  access_token    = var.access_token

  depends_on = [google_project_service.apis]
}



module "artifact_registry" {
  source        = "./modules/artifact_registry"
  project_id    = var.project_id
  location      = var.region
  repository_id = local.artifact_repository_id
  description   = var.artifact_repository_description
  format        = var.artifact_repository_format

  depends_on = [google_project_service.apis]
}

module "cloud_run_service" {
  source                = "./modules/cloud_run_service"
  service_name          = local.service_name
  project_id            = var.project_id
  location              = var.location != "" ? var.location : var.region
  image_url             = var.image_url != "" ? var.image_url : var.run_service_default_image_url
  container_port        = var.container_port
  allow_unauthenticated = var.allow_unauthenticated
  service_account_email = google_service_account.run_sa.email

  env_vars = merge(var.run_service_env_vars, {
    GOOGLE_CLOUD_PROJECT              = var.project_id
    GOOGLE_CLOUD_LOCATION             = var.region
    FIRESTORE_DB                      = local.firestore_database_name
    GOOGLE_ADS_FORCE_USER_CREDS     = var.google_ads_force_user_creds
    SA360_FORCE_USER_CREDS          = var.sa360_force_user_creds
  })
  secret_env_vars = { for secret in module.secret_manager.secret_ids : secret => { name = secret, version = "latest" } }
  depends_on = [google_project_service.apis, module.secret_manager]
}


# Combined Scheduler Job for Decision Agent
resource "google_cloud_scheduler_job" "sa_combined_job" {
  project          = var.project_id
  region           = var.region
  name             = local.sa_combined_scheduler_job_name
  description      = "Combined job to init session and run agent for SA360"
  schedule         = var.sa360_scheduler_schedule
  time_zone        = var.sa_run_sse_scheduler_job_timezone
  attempt_deadline = var.sa_run_sse_scheduler_job_attempt_deadline

  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    http_method = "POST"
    uri         = "${module.cloud_run_service.service_url}/scheduler/init_and_run"
    body = base64encode(jsonencode({
      app_name = "decision_agent"
      user_id  = google_service_account.run_sa.email
      customer_id = var.sa360_customer_id
      usecase = "SA360"
    }))
    headers = {
      "Content-Type" = "application/json"
      "User-Agent"   = "Google-Cloud-Scheduler"
    }

    oidc_token {
      service_account_email = google_service_account.run_sa.email
      audience              = "${module.cloud_run_service.service_url}/scheduler/init_and_run"
    }
  }
}


# Combined Scheduler Job for Decision Agent
resource "google_cloud_scheduler_job" "google_ads_combined_job" {
  project          = var.project_id
  region           = var.region
  name             = local.google_ads_combined_scheduler_job_name
  description      = "Combined job to init session and run agent for Google Ads"
  schedule         = var.googleads_scheduler_schedule
  time_zone        = var.sa_run_sse_scheduler_job_timezone
  attempt_deadline = var.sa_run_sse_scheduler_job_attempt_deadline

  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    http_method = "POST"
    uri         = "${module.cloud_run_service.service_url}/scheduler/init_and_run"
    body = base64encode(jsonencode({
      app_name = "decision_agent"
      user_id  = google_service_account.run_sa.email
      customer_id = var.googleads_customer_id
      usecase = "GoogleAds"
    }))
    headers = {
      "Content-Type" = "application/json"
      "User-Agent"   = "Google-Cloud-Scheduler"
    }

    oidc_token {
      service_account_email = google_service_account.run_sa.email
      audience              = "${module.cloud_run_service.service_url}/scheduler/init_and_run"
    }
  }
}

# --- Scheduler Verification Outputs ---
output "scheduler_target_uri" {
  description = "The target URI being used for scheduler jobs"
  value       = "${module.cloud_run_service.service_url}/scheduler/init_and_run"
}

output "scheduler_oidc_service_account" {
  description = "The service account email being used for scheduler OIDC tokens"
  value       = google_service_account.run_sa.email
}
