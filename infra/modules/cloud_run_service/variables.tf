variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "location" {
  description = "GCP region for the service"
  type        = string
}

variable "image_url" {
  description = "Full URL of the container image"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for the Cloud Run service. Defaults to Compute Engine default SA if null."
  type        = string
  default     = null
}

variable "env_vars" {
  description = "Environment variables to set in the container"
  type        = map(string)
  default     = {}
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8080
}

variable "allow_unauthenticated" {
  description = "If true, allows unauthenticated invocations to the service"
  type        = bool
  default     = false # Set to true only if it's a public API
}
