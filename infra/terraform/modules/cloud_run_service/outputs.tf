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

# Output the URL of the service
output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.uri
}

output "name" {
  description = "The name of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.name
}

output "location" {
  description = "The location of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.location
}

output "project_id" {
  description = "The project id of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.default.project
}
