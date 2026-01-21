variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "secret_names" {
  description = "A list of secret names to be accessed."
  type        = list(string)
  default = [
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "USER_REFRESH_TOKEN",
    "USER_CLIENT_ID",
    "USER_CLIENT_SECRET"
  ]
}

variable "service_account_email" {
  description = "Service account email to grant access to secrets"
  type        = string
  default     = ""
}

variable "additional_secrets" {
  description = "A list of additional secret names to manage."
  type        = list(string)
  default     = []
}

variable "secret_values" {
  description = "A map of secret names to their values. Used to create secret versions."
  type        = map(string)
  sensitive   = true
  default     = {}
}
