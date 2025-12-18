variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "secret_names" {
  description = "A list of secret names to be accessed."
  type        = list(string)
  default = [
    "GOOGLE_API_KEY",
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_POLLEN_API_KEY",
    "GOOGLE_WEATHER_API_KEY"
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
