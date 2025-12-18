#!/bin/bash
set -e

# Change to the script's directory to ensure relative paths are correct.
cd "$(dirname "$0")"

# --- Configuration ---
CONFIG_FILE="config.yaml"
TFVARS_FILE="terraform.tfvars"
IMAGE_BUILD_SCRIPT="./scripts/build_image.sh"
TFVARS_GEN_SCRIPT="./scripts/generate_tfvars.py"

# --- Functions ---
function get_config_value() {
  python3 -c "import yaml; print(yaml.safe_load(open('$1'))['$2'])"
}

function create_secret_if_not_exists() {
  local secret_name="$1"
  local project_id="$2"

  if ! gcloud secrets describe "$secret_name" --project="$project_id" &>/dev/null; then
    echo "   Secret '$secret_name' not found. Please provide the value."
    echo -n "Enter value for $secret_name: "
    read -s secret_value
    echo
    if [ -z "$secret_value" ]; then
      echo "Error: Value cannot be empty."
      exit 1
    fi
    # Create the secret and pipe the value to its first version
    echo "$secret_value" | gcloud secrets create "$secret_name" \
      --project="$project_id" \
      --data-file=- \
      --replication-policy=automatic
    echo "   ✓ Secret '$secret_name' created successfully."
  else
    echo "   ✓ Secret '$secret_name' already exists."
  fi
}

# --- Main Script ---

# 1. Check for dependencies
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud is not installed."
    exit 1
fi
if ! command -v terraform &> /dev/null; then
    echo "Error: terraform is not installed."
    exit 1
fi
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found."
    exit 1
fi
if [ ! -f "$TFVARS_GEN_SCRIPT" ]; then
    echo "Error: Tfvars generation script '$TFVARS_GEN_SCRIPT' not found."
    exit 1
fi

# 2. Get configuration from config.yaml
PROJECT_ID=$(get_config_value "$CONFIG_FILE" "project_id")
REGION=$(get_config_value "$CONFIG_FILE" "region")
RESOURCE_PREFIX=$(get_config_value "$CONFIG_FILE" "resource_prefix")
ADDITIONAL_SECRETS=$(python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$CONFIG_FILE')).get('additional_secrets', [])))")

# --- Derived Resource Names ---
SA_NAME="${RESOURCE_PREFIX}-deployer"
TF_STATE_BUCKET="${RESOURCE_PREFIX}-tf-state"
IMAGE_NAME="${RESOURCE_PREFIX}-image"
REPO_NAME="${RESOURCE_PREFIX}-repo"
TAG="latest"
IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$RESOURCE_PREFIX" ]; then
  echo "Error: 'project_id', 'region', and 'resource_prefix' must be set in $CONFIG_FILE."
  exit 1
fi

# 2a. Ensure Secrets Exist in Secret Manager
echo "--- Checking for secrets in Secret Manager ---"
SECRETS_TO_CHECK=(
  "GOOGLE_API_KEY"
  "GOOGLE_ADS_DEVELOPER_TOKEN"
  "GOOGLE_ADS_CLIENT_ID"
  "GOOGLE_ADS_CLIENT_SECRET"
  "GOOGLE_ADS_REFRESH_TOKEN"
  "GOOGLE_POLLEN_API_KEY"
  "GOOGLE_WEATHER_API_KEY"
)
# Add any user-defined secrets from the config file
if [ -n "$ADDITIONAL_SECRETS" ]; then
  SECRETS_TO_CHECK+=($ADDITIONAL_SECRETS)
fi

for secret in "${SECRETS_TO_CHECK[@]}"; do
  create_secret_if_not_exists "$secret" "$PROJECT_ID"
done
echo "✅ All required secrets are present in Secret Manager."

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 3. Set up Service Account for deployment
echo "--- Ensuring deployment Service Account '$SA_NAME' exists and has permissions ---"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  echo "   Creating Service Account: $SA_NAME"
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Agentic DSTA Deployer" \
    --project="$PROJECT_ID"
  # Add a delay to allow the service account to propagate
  echo "   Waiting for 10 seconds for the service account to propagate..."
  sleep 10
else
  echo "   Service Account '$SA_NAME' already exists."
fi

gcloud config unset auth/impersonate_service_account

ROLES=(
  "roles/viewer"
  "roles/serviceusage.serviceUsageAdmin"
  "roles/storage.admin"
  "roles/cloudbuild.builds.editor"
  "roles/artifactregistry.admin"
  "roles/run.admin"
  "roles/iam.serviceAccountUser"
  "roles/iam.serviceAccountTokenCreator"
  "roles/secretmanager.admin"
  "roles/cloudscheduler.admin"
  "roles/firebase.admin"
  "roles/resourcemanager.projectIamAdmin"
)

for role in "${ROLES[@]}"; do
  echo "   Applying project-level role: $role"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role" \
    --condition=None > /dev/null
done

# Add a delay to allow IAM permissions to propagate
echo "   Waiting for 10 seconds for IAM permissions to propagate..."
sleep 10

RUNNER_USER=$(gcloud config get-value account)
if [ -z "$RUNNER_USER" ]; then
  echo "Error: Could not determine the user running the script. Please make sure you are authenticated with gcloud."
  exit 1
fi
echo "   Granting permissions to '$RUNNER_USER' on '$SA_NAME' for impersonation"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="user:$RUNNER_USER" \
  --role="roles/iam.serviceAccountUser" \
  --project="$PROJECT_ID" > /dev/null

echo "✅ Service Account permissions are set."

# 4. Configure gcloud to use service account impersonation
echo "--- Configuring authentication to impersonate Service Account: $SA_EMAIL ---"
gcloud config set auth/impersonate_service_account "$SA_EMAIL"

# 5. Generate terraform.tfvars
echo "--- Generating terraform.tfvars (without image_url) ---"
python3 "$TFVARS_GEN_SCRIPT" "$CONFIG_FILE" "$TFVARS_FILE"
echo "account_email = \"$SA_EMAIL\"" >> "$TFVARS_FILE"

# 6. Create GCS bucket for Terraform state if it doesn't exist
echo "--- Ensuring Terraform state bucket '$TF_STATE_BUCKET' exists ---"
if ! gcloud storage buckets describe "gs://${TF_STATE_BUCKET}" --project="$PROJECT_ID" &>/dev/null; then
  echo "   Creating GCS bucket: gs://${TF_STATE_BUCKET}"
  gcloud storage buckets create "gs://${TF_STATE_BUCKET}" \
    --project="$PROJECT_ID" \
    --location="${REGION}" \
    --uniform-bucket-level-access
  echo "   Enabling versioning on GCS bucket..."
  gcloud storage buckets update "gs://${TF_STATE_BUCKET}" --project="$PROJECT_ID" --versioning
else
  echo "   Bucket 'gs://${TF_STATE_BUCKET}' already exists."
fi

echo "✅ Terraform state bucket is ready."



# 7. Build container image
echo "--- Building and pushing container image ---"
# The IMAGE_URL is now constructed above. The build script will run and push to this tag.
# All output from the build script will be streamed directly to the console.
if ! $IMAGE_BUILD_SCRIPT "$PROJECT_ID" "$REGION" "$REPO_NAME" "$IMAGE_NAME"; then
    echo "Error: Image build failed."
    exit 1
fi
echo "Image successfully built. Using URL: $IMAGE_URL"

# 8. Append the dynamic image_url to terraform.tfvars
echo "--- Appending image_url to terraform.tfvars ---"
# Remove any existing image_url line to avoid duplicates
sed -i '/^image_url/d' "$TFVARS_FILE"
echo "image_url = \"$IMAGE_URL\"" >> "$TFVARS_FILE"

# 9. Initialize Terraform
echo "--- Generating temporary ADC access token for Terraform ---"
if ! TF_ACCESS_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null); then
    echo "Error: Failed to get Application Default Credentials. Please run 'gcloud auth application-default login' to configure your credentials."
    exit 1
fi
export GOOGLE_OAUTH_ACCESS_TOKEN="$TF_ACCESS_TOKEN"

echo "--- Initializing Terraform ---"
terraform init -upgrade -backend-config="bucket=$TF_STATE_BUCKET"

# 10. Import existing resources into Terraform state (if they exist)
echo "--- Importing existing infrastructure into Terraform state (if they exist) ---"
# Construct resource names from config values
RUN_SA_ACCOUNT_ID="${RESOURCE_PREFIX}-runner"
RUN_SA_EMAIL="${RUN_SA_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULER_SA_ACCOUNT_ID="${RESOURCE_PREFIX}-scheduler"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
AGENTIC_DSTA_SA_ACCOUNT_ID="${RESOURCE_PREFIX}-sa"
AGENTIC_DSTA_SA_EMAIL="${AGENTIC_DSTA_SA_ACCOUNT_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
FIRESTORE_DB_NAME="${RESOURCE_PREFIX}-firestore"
STORAGE_BUCKET_NAME="${RESOURCE_PREFIX}-bucket"
TF_STATE_BUCKET_IN_MODULE="${RESOURCE_PREFIX}-tf-state"
APP_BUCKET_NAME="${STORAGE_BUCKET_NAME}-${PROJECT_ID}"

# The import commands will fail if the resources are already in the state.
# We ignore these errors with '|| true' so the script can continue.
echo "   Importing resources (errors for already-imported resources can be ignored)..."
terraform import "google_service_account.run_sa" "${RUN_SA_EMAIL}" || true
terraform import "google_service_account.scheduler_sa" "${SCHEDULER_SA_EMAIL}" || true
terraform import "google_service_account.agentic_dsta_sa" "${AGENTIC_DSTA_SA_EMAIL}" || true
terraform import "module.firestore.google_firestore_database.database" "projects/${PROJECT_ID}/databases/${FIRESTORE_DB_NAME}" || true
terraform import "module.storage.google_storage_bucket.buckets[\"${TF_STATE_BUCKET_IN_MODULE}\"]" "${TF_STATE_BUCKET_IN_MODULE}" || true
terraform import "module.storage.google_storage_bucket.buckets[\"${APP_BUCKET_NAME}\"]" "${APP_BUCKET_NAME}" || true
echo "✅ Infrastructure import attempts complete."

# 11. Run Terraform to deploy all infrastructure
echo "--- Generating temporary access token for API Hub initialization ---"
ACCESS_TOKEN=$(gcloud auth print-access-token --impersonate-service-account="$SA_EMAIL")
if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to retrieve access token for $SA_EMAIL."
    exit 1
fi

echo "--- Running Terraform to deploy all services ---"
terraform apply -auto-approve -var-file="$TFVARS_FILE" -var="access_token=$ACCESS_TOKEN"

echo "--- Deployment complete! ---"

# 11. Unset impersonation at the end of the script
echo "--- Cleaning up authentication settings ---"
gcloud config unset auth/impersonate_service_account
unset GOOGLE_OAUTH_ACCESS_TOKEN
