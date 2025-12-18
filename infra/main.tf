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
  storage_bucket_name                = "${var.resource_prefix}-bucket"
  scheduler_sa_account_id            = "${var.resource_prefix}-scheduler"
  firestore_database_name            = "${var.resource_prefix}-firestore"
  artifact_repository_id             = "${var.resource_prefix}-repo"
  agentic_dsta_sa_account_id         = "${var.resource_prefix}-sa"
  dsta_automation_scheduler_job_name = "${var.resource_prefix}-daily-automation"
  sa_session_init_scheduler_job_name = "${var.resource_prefix}-sa-session-init-job"
  sa_run_sse_scheduler_job_name      = "${var.resource_prefix}-sa-run-sse-job"
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

  depends_on = [google_project_service.apis]
}

module "apihub" {
  source          = "./modules/apihub"
  project_id      = var.project_id
  location        = var.region # This is the regional location for the instance itself
  specs_dir       = "${path.module}/${var.apihub_specs_dir}"
  vertex_location = var.region
  account_email   = var.account_email
  access_token    = var.access_token

  depends_on = [google_project_service.apis]
}

module "storage" {
  source     = "./modules/storage"
  project_id = var.project_id
  buckets = {
    "${local.storage_bucket_name}-${var.project_id}" = {
      location                    = "US"
      storage_class               = "STANDARD"
      force_destroy               = false
      uniform_bucket_level_access = true
      public_access_prevention    = "enforced"
      retention_duration_seconds  = 604800
      labels                      = {}
    },
    # Using the manually created bucket name without project ID suffix
    "${var.resource_prefix}-tf-state" = {
      location                    = "US"
      storage_class               = "STANDARD"
      force_destroy               = false
      uniform_bucket_level_access = false
      public_access_prevention    = "inherited"
      retention_duration_seconds  = 604800
      labels                      = {}
    }
  }
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
    GOOGLE_CLOUD_PROJECT = var.project_id
    GOOGLE_CLOUD_LOCATION = var.region
  })
  secret_env_vars = { for secret in module.secret_manager.secret_ids : secret => { name = secret, version = "latest" } }
  depends_on = [google_project_service.apis, module.secret_manager]
}

# Service Account for Scheduler
resource "google_service_account" "scheduler_sa" {
  project      = var.project_id
  account_id   = local.scheduler_sa_account_id
  display_name = var.scheduler_sa_display_name
}

# Service Account for agentic-dsta-sa
resource "google_service_account" "agentic_dsta_sa" {
  project      = var.project_id
  account_id   = local.agentic_dsta_sa_account_id
  display_name = "Agentic DSTA Scheduler Invoker SA"
}

# Grant agentic-dsta-sa SA permission to invoke cloud run service
resource "google_cloud_run_v2_service_iam_member" "agentic_dsta_sa_invoker" {
  provider = google-beta
  project  = module.cloud_run_service.project_id
  location = module.cloud_run_service.location
  name     = module.cloud_run_service.name
  role     = var.run_invoker_role
  member   = "serviceAccount:${google_service_account.agentic_dsta_sa.email}"
}

locals {
  session_id = "session-${timestamp()}"
}

# Scheduler job for sa-session-init-job
resource "google_cloud_scheduler_job" "sa_session_init_job" {
  project          = var.project_id
  region           = var.region
  name             = local.sa_session_init_scheduler_job_name
  description      = var.sa_session_init_scheduler_job_description
  schedule         = var.sa_session_init_scheduler_job_schedule
  time_zone        = var.sa_session_init_scheduler_job_timezone
  attempt_deadline = var.sa_session_init_scheduler_job_attempt_deadline

  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }

  http_target {
    http_method = "POST"
    uri         = "${module.cloud_run_service.service_url}/run_sse"
    body = base64encode(jsonencode({
      app_name = "decision_agent"
      user_id  = google_service_account.agentic_dsta_sa.email
      session_id = local.session_id
      new_message = {
        role  = "user"
        parts = [{ text = var.scheduler_new_message_text }]
      }
      streaming = false
    }))
    headers = {
      "Content-Type" = "application/json"
      "User-Agent"   = "Google-Cloud-Scheduler"
    }

    oidc_token {
      service_account_email = google_service_account.agentic_dsta_sa.email
      audience              = "${module.cloud_run_service.service_url}/run_sse"
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.agentic_dsta_sa_invoker]
}

# Scheduler job for sa-run-sse-job
resource "google_cloud_scheduler_job" "sa_run_sse_job" {
  project          = var.project_id
  region           = var.region
  name             = local.sa_run_sse_scheduler_job_name
  description      = var.sa_run_sse_scheduler_job_description
  schedule         = var.sa_run_sse_scheduler_job_schedule
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
    uri         = "${module.cloud_run_service.service_url}/run_sse"
    body = base64encode(jsonencode({
      app_name = "decision_agent"
      user_id  = google_service_account.agentic_dsta_sa.email
      session_id = local.session_id
      new_message = {
        role  = "user"
        parts = [{ text = var.scheduler_new_message_text }]
      }
      streaming = false
    }))
    headers = {
      "Content-Type" = "application/json"
      "User-Agent"   = "Google-Cloud-Scheduler"
    }

    oidc_token {
      service_account_email = google_service_account.agentic_dsta_sa.email
      audience              = "${module.cloud_run_service.service_url}/run_sse"
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.agentic_dsta_sa_invoker]
}



# --- Scheduler Verification Outputs ---
output "scheduler_target_uri" {
  description = "The target URI being used for scheduler jobs"
  value       = "${module.cloud_run_service.service_url}/run_sse"
}

output "scheduler_oidc_service_account" {
  description = "The service account email being used for scheduler OIDC tokens"
  value       = google_service_account.agentic_dsta_sa.email
}

output "scheduler_session_id" {
  description = "The dynamic session ID being used for scheduler jobs"
  value       = local.session_id
}
