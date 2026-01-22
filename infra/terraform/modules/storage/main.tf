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

resource "google_storage_bucket" "buckets" {
  for_each = var.buckets

  name                        = each.key
  project                     = var.project_id
  location                    = each.value.location
  storage_class               = each.value.storage_class
  force_destroy               = each.value.force_destroy
  uniform_bucket_level_access = each.value.uniform_bucket_level_access
  public_access_prevention    = each.value.public_access_prevention

  dynamic "soft_delete_policy" {
    for_each = each.value.retention_duration_seconds != null ? [1] : []
    content {
      retention_duration_seconds = each.value.retention_duration_seconds
    }
  }

  labels = merge({
    managed-by-cnrm = "true"
  }, each.value.labels)
}
