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
SA_NAME=$(get_config_value "$CONFIG_FILE" "deployment_sa_name")
TF_STATE_BUCKET=$(get_config_value "$CONFIG_FILE" "tf_state_bucket")

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$SA_NAME" ] || [ -z "$TF_STATE_BUCKET" ]; then
  echo "Error: 'project_id', 'region', 'deployment_sa_name', and 'tf_state_bucket' must be set in $CONFIG_FILE."
  exit 1
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 3. Set up Service Account for deployment
echo "--- Ensuring deployment Service Account '$SA_NAME' exists and has permissions ---"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  echo "   Creating Service Account: $SA_NAME"
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Agentic DSTA Deployer" \
    --project="$PROJECT_ID"
else
  echo "   Service Account '$SA_NAME' already exists."
fi

ROLES=(
  "roles/serviceusage.serviceUsageAdmin"
  "roles/storage.admin"
  "roles/cloudbuild.builds.editor"
  "roles/artifactregistry.admin"
  "roles/run.admin"
  "roles/iam.serviceAccountUser"
  "roles/iam.serviceAccountTokenCreator"
  "roles/secretmanager.admin"
)

for role in "${ROLES[@]}"; do
  echo "   Applying project-level role: $role"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role" \
    --condition=None > /dev/null
done

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

# 7. Initialize Terraform and create the Artifact Registry first
echo "--- Generating temporary ADC access token for Terraform ---"
if ! TF_ACCESS_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null); then
    echo "Error: Failed to get Application Default Credentials. Please run 'gcloud auth application-default login' to configure your credentials."
    exit 1
fi
export GOOGLE_OAUTH_ACCESS_TOKEN="$TF_ACCESS_TOKEN"

echo "--- Initializing Terraform and creating Artifact Registry repository ---"
terraform init -upgrade -backend-config="bucket=$TF_STATE_BUCKET"
terraform apply -auto-approve -var-file="$TFVARS_FILE" -target="module.artifact_registry"

# 8. Build container image and get the URL
echo "--- Building and pushing container image ---"
IMAGE_URL=$($IMAGE_BUILD_SCRIPT "$PROJECT_ID" "$REGION" | grep "image_url =" | awk -F '"' '{print $2}')

if [ -z "$IMAGE_URL" ]; then
    echo "Error: Failed to get image_url from the build script."
    exit 1
fi
echo "Image URL: $IMAGE_URL"

# 9. Append the dynamic image_url to terraform.tfvars
echo "--- Appending image_url to terraform.tfvars ---"
echo "image_url = \"$IMAGE_URL\"" >> "$TFVARS_FILE"

# 10. Run Terraform again to deploy the remaining infrastructure
echo "--- Running Terraform to deploy all services ---"
terraform apply -auto-approve -var-file="$TFVARS_FILE"

echo "--- Deployment complete! ---"

# 11. Unset impersonation at the end of the script
echo "--- Cleaning up authentication settings ---"
gcloud config unset auth/impersonate_service_account
unset GOOGLE_OAUTH_ACCESS_TOKEN
