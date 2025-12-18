output "secret_ids" {
  description = "The IDs of the secrets being accessed."
  value       = [for secret in data.google_secret_manager_secret.secrets : secret.secret_id]
}


