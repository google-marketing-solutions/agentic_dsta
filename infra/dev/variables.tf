variable "project_id" {
  description = "The GCP project ID for the development environment"
  type        = string
  # Example: default = "my-gcp-project-dev" # <--- !!! SET YOUR PROJECT ID
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "agentic-dsta-dev"
}

variable "image_url" {
  description = "The URL of the container image in Artifact Registry. Set by CI/CD."
  type        = string
  default     = "" # This will often be overridden by CI/CD
}

variable "service_account_email" {
  description = "Service account email for the Cloud Run service instance"
  type        = string
  default     = "" # Example: agentic-dsta-dev-sa@my-gcp-project-dev.iam.gserviceaccount.com
                   # Best practice is to use a dedicated, least-privileged service account.
}
