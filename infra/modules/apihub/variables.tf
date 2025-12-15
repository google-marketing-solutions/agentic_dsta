variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "location" {
  description = "The location for API Hub"
  type        = string
}

variable "specs_dir" {
  description = "Path to the directory containing OpenAPI specs"
  type        = string
}

variable "vertex_location" {
  description = "The multi-region for API Hub Vertex AI Search data (e.g., 'us' or 'eu')."
  type        = string
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