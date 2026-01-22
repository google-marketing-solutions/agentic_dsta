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

variable "database_name" {
  description = "The name of the Firestore database"
  type        = string
  default     = "(default)"
}

variable "location_id" {
  description = "The location ID for the database"
  type        = string
}

variable "database_type" {
  description = "The type of the database (FIRESTORE_NATIVE or DATASTORE_MODE)"
  type        = string
  default     = "FIRESTORE_NATIVE"
}
