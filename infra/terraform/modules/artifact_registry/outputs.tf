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

output "name" {
  value = data.google_artifact_registry_repository.repo.name
}

output "id" {
  value = data.google_artifact_registry_repository.repo.repository_id
}

output "artifact_repository_id" {
  description = "The ID of the Artifact Registry repository"
  value       = data.google_artifact_registry_repository.repo.repository_id
}
