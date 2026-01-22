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

variable "service_name" {
  description = "API Hub service name to enable."
  type        = string
  default     = "apihub.googleapis.com"
}

variable "service_identity_roles" {
  description = "IAM roles for API Hub service identity."
  type        = list(string)
  default = [
    "roles/apihub.editor",
    "roles/apihub.admin",
    "roles/apihub.runtimeProjectServiceAgent"
  ]
}

variable "spec_files" {
  description = "List of OpenAPI spec file names in specs_dir."
  type        = list(string)
  default = [
    "pollen-api-openapi.yaml",
    "weather-api-openapi.yaml",
    "air-quality-api-openapi.yaml"
  ]
}

variable "init_script_path" {
  description = "Path to API Hub initialization script."
  type        = string
  default     = "../../../scripts/apihub/init_apihub.sh"
}