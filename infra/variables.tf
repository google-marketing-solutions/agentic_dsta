variable "project_id" {
  description = "The GCP project ID for the development environment"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "The location/region for Cloud Run service (defaults to var.region)"
  type        = string
  default     = "" # If empty, var.region will be used
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "agentic-dsta"
}

variable "image_url" {
  description = "The URL of the container image in Artifact Registry. Set by CI/CD."
  type        = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8080
}

variable "allow_unauthenticated" {
  description = "If true, allows unauthenticated invocations to the service (set to true for public access)"
  type        = bool
  default     = false
}

variable "service_account_email" {
  description = "Service account email for the Cloud Run service instance. If not provided, a dedicated SA will be created."
  type        = string
  default     = "" 
}

# --- Firestore Variables ---

variable "firestore_database_name" {
  description = "The name of the Firestore database"
  type        = string
  default     = "dsta-agentic-firestore"
}

variable "firestore_location_id" {
  description = "The location ID for the Firestore database (e.g. nam5 for us-central)"
  type        = string
  default     = "nam5"
}

variable "firestore_database_type" {
  description = "The type of the Firestore database"
  type        = string
  default     = "FIRESTORE_NATIVE"
}

# --- Artifact Registry Variables ---

variable "artifact_repository_id" {
  description = "The ID of the Artifact Registry repository"
  type        = string
  default     = "agentic-dsta-repo"
}

# --- API Hub Variables ---

# --- Scheduler Variables ---

variable "scheduler_cron" {
  description = "The cron schedule for the agent trigger"
  type        = string
  default     = "0 0 * * *"
}

# --- Secrets ---

variable "google_api_key" {
  description = "Google API Key"
  type        = string
  sensitive   = true
}

variable "google_ads_developer_token" {
  description = "Google Ads Developer Token"
  type        = string
  sensitive   = true
}

variable "google_ads_client_id" {
  description = "Google Ads Client ID"
  type        = string
  sensitive   = true
}

variable "google_ads_client_secret" {
  description = "Google Ads Client Secret"
  type        = string
  sensitive   = true
}

variable "google_ads_refresh_token" {
  description = "Google Ads Refresh Token"
  type        = string
  sensitive   = true
}

variable "google_pollen_api_key" {
  description = "Google Pollen API Key"
  type        = string
  sensitive   = true
}

variable "google_weather_api_key" {
  description = "Google Weather API Key"
  type        = string
  sensitive   = true
}

variable "apihub_vertex_location" {
  description = "The multi-region for API Hub Vertex AI Search data (e.g., 'us' or 'eu')."
  type        = string
  default     = "us"
}

variable "account_email" {
  description = "The service account email to use for API Hub initialization."
  type        = string
}

variable "access_token" {
  description = "The access token to use for API Hub initialization."
  type        = string
  sensitive   = true
}

