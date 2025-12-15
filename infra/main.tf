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
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iamcredentials.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
    "firestore.googleapis.com",
    "apihub.googleapis.com",
    "aiplatform.googleapis.com",
    "iap.googleapis.com",
    "googleads.googleapis.com",
    "pollen.googleapis.com",
    "weather.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Service Account for Cloud Run
resource "google_service_account" "run_sa" {
  account_id   = "agentic-dsta-runner"
  display_name = "Agentic DSTA Cloud Run Runner"
  project      = var.project_id
}

# IAM roles for Service Account
resource "google_project_iam_member" "run_sa_roles" {
  for_each = toset([
    "roles/datastore.user",
    "roles/apihub.editor",
    "roles/aiplatform.user",
    "roles/secretmanager.secretAccessor",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

#--- Modules ---

module "firestore" {
  source        = "./modules/firestore"
  project_id    = var.project_id
  location_id   = var.firestore_location_id
  database_name = var.firestore_database_name
  database_type = var.firestore_database_type

  depends_on = [google_project_service.apis]
}

module "secret_manager" {
  source     = "./modules/secret_manager"
  project_id = var.project_id
  secrets = {
    GOOGLE_API_KEY             = var.google_api_key
    GOOGLE_ADS_DEVELOPER_TOKEN = var.google_ads_developer_token
    GOOGLE_ADS_CLIENT_ID       = var.google_ads_client_id
    GOOGLE_ADS_CLIENT_SECRET   = var.google_ads_client_secret
    GOOGLE_ADS_REFRESH_TOKEN   = var.google_ads_refresh_token
    GOOGLE_POLLEN_API_KEY      = var.google_pollen_api_key
    GOOGLE_WEATHER_API_KEY     = var.google_weather_api_key
  }
  service_account_email = google_service_account.run_sa.email

  depends_on = [google_project_service.apis]
}

module "apihub" {
  source          = "./modules/apihub"
  project_id      = var.project_id
  location        = var.region # This is the regional location for the instance itself
  specs_dir       = "${path.module}/specs"
  vertex_location = var.apihub_vertex_location

  depends_on = [google_project_service.apis]
}

module "storage" {
  source     = "./modules/storage"
  project_id = var.project_id
  buckets = {
    "dsta-bucket-${var.project_id}" = {
      location                    = "US"
      storage_class               = "STANDARD"
      force_destroy               = false
      uniform_bucket_level_access = true
      public_access_prevention    = "enforced"
      retention_duration_seconds  = 604800
      labels                      = {}
    },
    # Using the manually created bucket name without project ID suffix
    "agentic-dsta-tf-state" = {
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
  repository_id = var.artifact_repository_id
  description   = "Docker repository for Agentic DSTA"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

module "cloud_run_service" {
  source                = "./modules/cloud_run_service"
  service_name          = var.service_name
  project_id            = var.project_id
  location              = var.location != "" ? var.location : var.region
  image_url             = var.image_url != "" ? var.image_url : "gcr.io/cloudrun/hello"
  container_port        = var.container_port
  allow_unauthenticated = var.allow_unauthenticated
  service_account_email = google_service_account.run_sa.email

  env_vars = {
    GOOGLE_CLOUD_PROJECT       = var.project_id
    GOOGLE_CLOUD_LOCATION      = var.region
    GOOGLE_GENAI_USE_VERTEXAI  = "True"
  }
  secret_env_vars = {
    GOOGLE_API_KEY = {
      name    = module.secret_manager.secret_ids["GOOGLE_API_KEY"],
      version = "latest"
    },
    GOOGLE_ADS_DEVELOPER_TOKEN = {
      name    = module.secret_manager.secret_ids["GOOGLE_ADS_DEVELOPER_TOKEN"],
      version = "latest"
    },
    GOOGLE_ADS_CLIENT_ID = {
      name    = module.secret_manager.secret_ids["GOOGLE_ADS_CLIENT_ID"],
      version = "latest"
    },
    GOOGLE_ADS_CLIENT_SECRET = {
      name    = module.secret_manager.secret_ids["GOOGLE_ADS_CLIENT_SECRET"],
      version = "latest"
    },
    GOOGLE_ADS_REFRESH_TOKEN = {
      name    = module.secret_manager.secret_ids["GOOGLE_ADS_REFRESH_TOKEN"],
      version = "latest"
    },
    GOOGLE_POLLEN_API_KEY = {
      name    = module.secret_manager.secret_ids["GOOGLE_POLLEN_API_KEY"],
      version = "latest"
    },
    GOOGLE_WEATHER_API_KEY = {
      name    = module.secret_manager.secret_ids["GOOGLE_WEATHER_API_KEY"],
      version = "latest"
    }
  }
  depends_on = [google_project_service.apis, module.secret_manager]
}

# Service Account for Scheduler
resource "google_service_account" "scheduler_sa" {
  account_id   = "dsta-scheduler"
  display_name = "DSTA Scheduler SA"
  project      = var.project_id
}

# # Grant scheduler SA permission to invoke cloud run service
# resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
#   provider = google-beta
#   project  = module.cloud_run_service.project_id
#   location = module.cloud_run_service.location
#   name     = module.cloud_run_service.name
#   role     = "roles/run.invoker"
#   member   = "serviceAccount:${google_service_account.scheduler_sa.email}"
# }

# # Scheduler job to trigger agent daily
# resource "google_cloud_scheduler_job" "dsta_automation" {
#   project     = var.project_id
#   region      = var.region
#   name        = "dsta-daily-automation"
#   description = "Daily trigger for DSTA marketing automation agent"
#   schedule    = var.scheduler_cron
#   time_zone   = "UTC"

#   http_target {
#     http_method = "POST"
#     uri         = "${module.cloud_run_service.service_url}/sessions"
#     body = base64encode(jsonencode({
#       agent_name = "marketing_campaign_manager",
#       query      = "Run daily check based on current demand signals and business rules."
#     }))
#     headers = {
#       "Content-Type" = "application/json"
#     }

#     oidc_token {
#       service_account_email = google_service_account.scheduler_sa.email
#       audience              = module.cloud_run_service.service_url
#     }
#   }

#   depends_on = [google_cloud_run_v2_service_iam_member.scheduler_invoker]
# }
# Add this to the end of infra/main.tf

output "debug_root_secrets_keys" {
  description = "Keys of the map constructed for secret_manager input"
  value = keys({
    GOOGLE_API_KEY             = var.google_api_key
    GOOGLE_ADS_DEVELOPER_TOKEN = var.google_ads_developer_token
    GOOGLE_ADS_CLIENT_ID       = var.google_ads_client_id
    GOOGLE_ADS_CLIENT_SECRET   = var.google_ads_client_secret
    GOOGLE_ADS_REFRESH_TOKEN   = var.google_ads_refresh_token
    GOOGLE_POLLEN_API_KEY      = var.google_pollen_api_key
    GOOGLE_WEATHER_API_KEY     = var.google_weather_api_key
  })
  sensitive = true # <--- ADD THIS
}

output "debug_root_var_google_api_key_is_null" {
  description = "Is var.google_api_key null?"
  value       = var.google_api_key == null
  sensitive   = true # <--- ADD THIS
}

output "debug_root_var_google_ads_developer_token_is_null" {
  description = "Is var.google_ads_developer_token null?"
  value       = var.google_ads_developer_token == null
  sensitive   = true # <--- ADD THIS
}

# Add similar _is_null checks for the other 5 secret vars if you want to be exhaustive,
# making sure to include sensitive = true for each.
