# API Hub Service Identity
resource "google_project_service_identity" "apihub_service_identity" {
  provider = google-beta
  project  = var.project_id
  service  = "apihub.googleapis.com"
}

# Grant Admin role to service identity
resource "google_project_iam_member" "apihub_service_identity_permission" {
  provider = google-beta
  project = var.project_id
  for_each = toset([
    "roles/apihub.editor",
    "roles/apihub.admin",
    "roles/apihub.runtimeProjectServiceAgent"
  ])
  role    = each.key
  member  = "serviceAccount:${google_project_service_identity.apihub_service_identity.email}"
  depends_on = [google_project_service_identity.apihub_service_identity]
}

# Initialization Script
# Registers APIs into API Hub so the agent can discover them.
# Using local-exec with sh because TF resources for apihub api/version/spec
# are not available in the current provider version, and bash is not available
# in g3terraform runner for local-exec.
resource "null_resource" "init_apihub" {
  triggers = {
    project_id = var.project_id
    location   = var.location
    # Trigger re-run if specs change
    pollen_spec_hash  = filemd5("${var.specs_dir}/pollen-api-openapi.yaml")
    weather_spec_hash = filemd5("${var.specs_dir}/weather-api-openapi.yaml")
    air_quality_spec_hash = filemd5("${var.specs_dir}/air-quality-api-openapi.yaml")
  }

  provisioner "local-exec" {
    command = <<EOT
      ACCOUNT_EMAIL='${var.account_email}' ACCESS_TOKEN='${var.access_token}' \
      sh ${path.module}/../../scripts/init_apihub.sh ${var.project_id} ${var.location} ${var.specs_dir}
    EOT
  }

  depends_on = [
    google_project_iam_member.apihub_service_identity_permission
  ]
}
