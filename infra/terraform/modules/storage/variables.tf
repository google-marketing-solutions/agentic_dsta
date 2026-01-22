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

variable "buckets" {
  description = "Map of bucket names to configuration"
  type = map(object({
    location                    = string
    storage_class               = string
    force_destroy               = bool
    uniform_bucket_level_access = bool
    public_access_prevention    = string
    retention_duration_seconds  = optional(number)
    labels                      = optional(map(string))
  }))
}
