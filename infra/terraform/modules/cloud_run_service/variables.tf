# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

variable "secret_env_vars" {
  description = "Environment variables sourced from Secret Manager secrets. Map key is env var name, value is object with secret name and version."
  type = map(object({
    name    = string
    version = string
  }))
  default = {}
}
