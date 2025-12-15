project_id                 = "styagi-test"
image_url                  = "us-central1-docker.pkg.dev/styagi-test/agentic-dsta-repo/agentic-dsta:latest"
google_api_key             = google_api_key
google_ads_developer_token = google_ads_developer_token
google_ads_client_id       = google_ads_client_id
google_ads_client_secret   = google_ads_client_secret
google_ads_refresh_token   = google_ads_refresh_token
google_pollen_api_key      = google_pollen_api_key
google_weather_api_key     = google_weather_api_key
region = "us-central1"
service_name = "cloud-run-dsta-tf"
allow_unauthenticated = false# Firestore Configuration
# =============================================================================

# The name of the Firestore database
# Default: "dsta-agentic-firestore"
firestore_database_name = "dsta-agentic-firestore-tf"

# The location ID for the Firestore database (e.g., nam5 for us-central)
# Default: "nam5"
firestore_location_id = "nam5"

# The type of the Firestore database (FIRESTORE_NATIVE or DATASTORE_MODE)
# Default: "FIRESTORE_NATIVE"
firestore_database_type = "FIRESTORE_NATIVE"

# =============================================================================
# Artifact Registry Configuration
# =============================================================================

# The ID of the Artifact Registry repository
# Default: "agentic-dsta-repo"
artifact_repository_id = "agentic-dsta-repo"

# =============================================================================
# API Hub Configuration
# =============================================================================
# API Hub Configuration
# =============================================================================
account_email = "agentic-dsta-runner@styagi-test.iam.gserviceaccount.com"
access_token = access_token


# The ID of the API Hub instance
# Default: "default-instance"
apihub_instance_id = "default-instance"

# =============================================================================
# Scheduler Configuration
# =============================================================================

# The cron schedule for the agent trigger
# Default: "0 0 * * *" (Every day at midnight UTC)
scheduler_cron = "0 0 * * *"

# =============================================================================