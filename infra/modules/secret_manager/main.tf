locals {
  all_secret_names = concat(var.secret_names, var.additional_secrets)
}

# Data source to look up the secrets that are now created by the deploy.sh script
data "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.all_secret_names)
  project   = var.project_id
  secret_id = each.key
}

# IAM binding to allow a service account to access these secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each  = var.service_account_email != "" ? toset(local.all_secret_names) : []
  secret_id = data.google_secret_manager_secret.secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}
