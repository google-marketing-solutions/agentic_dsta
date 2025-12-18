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
