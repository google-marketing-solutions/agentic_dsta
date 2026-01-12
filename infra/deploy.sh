#!/bin/bash
set -e

# Change to the script's directory to ensure relative paths are correct.
cd "$(dirname "$0")"

# --- Cleanup ---
# This function is called when the script exits (normally or on error)
# to ensure the gcloud impersonation setting is always removed.
cleanup() {
  echo "--- Cleaning up authentication settings ---"
  gcloud config unset auth/impersonate_service_account >/dev/null 2>&1 || true
}
trap cleanup EXIT

# --- Configuration ---
CONFIG_FILE="config/app/config.yaml"
TFVARS_FILE="terraform/terraform.tfvars"
IMAGE_BUILD_SCRIPT="./scripts/deployment/build_image.sh"
TFVARS_GEN_SCRIPT="./scripts/deployment/generate_tfvars.py"

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
RESOURCE_PREFIX=$(get_config_value "$CONFIG_FILE" "resource_prefix")
ADDITIONAL_SECRETS=$(python3 -c "import yaml; print(' '.join(yaml.safe_load(open('$CONFIG_FILE')).get('additional_secrets', [])))")

# --- Derived Resource Names ---
SA_NAME="${RESOURCE_PREFIX}-deployer"
# Append the project ID to the bucket name to ensure global uniqueness.
TF_STATE_BUCKET="agentic-dsta-tf-state-v5-${PROJECT_ID}"
IMAGE_NAME="${RESOURCE_PREFIX}-image"
REPO_NAME="${RESOURCE_PREFIX}-repo"
TAG="latest"
IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"

# ---- Firestore DB Name ---
FIRESTORE_DB="${RESOURCE_PREFIX}-firestore"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$RESOURCE_PREFIX" ]; then
  echo "Error: 'project_id', 'region', and 'resource_prefix' must be set in $CONFIG_FILE."
  exit 1
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# 3. Set up Service Account for deployment
echo "--- Ensuring deployment Service Account '$SA_NAME' exists and has permissions ---"

# Use a more robust check for the service account's existence
SA_DESCRIPTION_OUTPUT=$(gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" 2>&1 || true)
if [[ "$SA_DESCRIPTION_OUTPUT" == *"NOT_FOUND"* ]]; then
  echo "   Service Account '$SA_NAME' not found. Creating it..."
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="Agentic DSTA Deployer" \
    --project="$PROJECT_ID"
  # Add a delay to allow the service account to propagate
  echo "   Waiting for 10 seconds for the service account to propagate..."
  sleep 10
elif [[ "$SA_DESCRIPTION_OUTPUT" == *"ERROR"* ]]; then
  # A different error occurred (e.g., permission denied)
  echo "   Error checking for Service Account '$SA_NAME'."
  echo "   This may be due to a lack of 'iam.serviceAccounts.get' permission."
  echo "   gcloud output:"
  echo "$SA_DESCRIPTION_OUTPUT"
  exit 1
else
  echo "   Service Account '$SA_NAME' already exists."
fi

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
  "roles/iam.serviceAccountAdmin"
  "roles/apihub.admin"
)

for role in "${ROLES[@]}"; do
  # Check if the policy binding already exists
  if gcloud projects get-iam-policy "$PROJECT_ID" --format="json" | \
    python3 -c "import sys, json; policy = json.load(sys.stdin); print(any(b['role'] == '$role' and 'serviceAccount:$SA_EMAIL' in b.get('members', []) for b in policy.get('bindings', [])))" | \
    grep -q "True"; then
    echo "   Project-level role for SA already exists: $role"
  else
    echo "   Applying project-level role for SA: $role"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$SA_EMAIL" \
      --role="$role" \
      --condition=None > /dev/null
  fi
done

# Add a longer delay to allow IAM permissions to propagate. This is crucial
# to prevent race conditions where Terraform runs before the new permissions are effective.
echo "   Waiting for 30 seconds for IAM permissions to propagate..."
sleep 30

# Grant the default Compute Engine service account the ability to read from GCS,
# which is required by Cloud Build to fetch the source code.
echo "   Granting Cloud Build worker permission to read source code..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
GCE_DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
GCE_ROLE="roles/storage.objectViewer"

if gcloud projects get-iam-policy "$PROJECT_ID" --format="json" | \
  python3 -c "import sys, json; policy = json.load(sys.stdin); print(any(b['role'] == '$GCE_ROLE' and 'serviceAccount:$GCE_DEFAULT_SA' in b.get('members', []) for b in policy.get('bindings', [])))" | \
  grep -q "True"; then
  echo "   Project-level role for GCE SA already exists: $GCE_ROLE"
else
  echo "   Applying project-level role for GCE SA: $GCE_ROLE"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$GCE_DEFAULT_SA" \
    --role="$GCE_ROLE" \
    --condition=None > /dev/null
fi

RUNNER_USER=$(gcloud config get-value account)
if [ -z "$RUNNER_USER" ]; then
  echo "Error: Could not determine the user running the script. Please make sure you are authenticated with gcloud."
  exit 1
fi
echo "   Granting permissions to '$RUNNER_USER' on '$SA_NAME' for impersonation"
# To grant multiple roles, add them to this array.
USER_ROLES_ON_SA=(
  "roles/iam.serviceAccountUser"
  "roles/iam.serviceAccountTokenCreator"
  "roles/iam.serviceAccountAdmin"
)

for role in "${USER_ROLES_ON_SA[@]}"; do
  # Check if the policy binding already exists
  if gcloud iam service-accounts get-iam-policy "$SA_EMAIL" --project="$PROJECT_ID" --format="json" | \
    python3 -c "import sys, json; policy = json.load(sys.stdin); print(any(b['role'] == '$role' and 'user:$RUNNER_USER' in b.get('members', []) for b in policy.get('bindings', [])))" | \
    grep -q "True"; then
    echo "   User role on SA already exists: $role"
  else
    echo "   Applying role for user on SA: $role"
    gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
      --member="user:$RUNNER_USER" \
      --role="$role" \
      --project="$PROJECT_ID" > /dev/null
  fi
done

# Add a delay to allow user roles on the SA to propagate before impersonation
echo "   Waiting for 30 seconds for user permissions to propagate..."
sleep 30

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



# 7. Build container image (if it doesn't already exist)
echo "--- Checking for existing container image ---"
if gcloud artifacts docker images describe "$IMAGE_URL" --project="$PROJECT_ID" &>/dev/null; then
  echo "   Image already exists: $IMAGE_URL"
  echo "   Skipping image build."
else
  echo "   Image not found. Building and pushing container image..."
  # The IMAGE_URL is now constructed above. The build script will run and push to this tag.
  # All output from the build script will be streamed directly to the console.
  if ! $IMAGE_BUILD_SCRIPT "$PROJECT_ID" "$REGION" "$REPO_NAME" "$IMAGE_NAME"; then
      echo "Error: Image build failed."
      exit 1
  fi
  echo "Image successfully built. Using URL: $IMAGE_URL"
fi

# 8. Append the dynamic image_url to terraform.tfvars
echo "--- Appending image_url to terraform.tfvars ---"
# Remove any existing image_url line to avoid duplicates
sed '/^image_url/d' "$TFVARS_FILE" > "$TFVARS_FILE.tmp" && mv "$TFVARS_FILE.tmp" "$TFVARS_FILE"
echo "image_url = \"$IMAGE_URL\"" >> "$TFVARS_FILE"

# 9. Enable Cloud Resource Manager APIgcloud auth print-access-token --impersonate-service-account="$SA_EMAIL"
# This API is a prerequisite for Terraform to be able to read or enable other APIs.
# We enable it here directly to prevent race conditions during Terraform's plan phase.
echo "--- Enabling prerequisite Cloud Resource Manager API ---"
gcloud services enable cloudresourcemanager.googleapis.com --project="$PROJECT_ID"
echo "   Waiting for 30 seconds for API enablement to propagate..."
sleep 30

# 10. Generate Access Token & Initialize Terraform
echo "--- Generating Access Token and Initializing Terraform ---"
ACCESS_TOKEN=$(gcloud auth print-access-token --impersonate-service-account="$SA_EMAIL")
if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to retrieve access token for $SA_EMAIL."
    exit 1
fi

terraform -chdir=terraform init -upgrade -reconfigure \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="access_token=$ACCESS_TOKEN"

# 11. Import existing resources to prevent "Already Exists" errors
echo "--- Importing existing resources into Terraform state ---"

# Firestore Database
terraform -chdir=terraform -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="access_token=$ACCESS_TOKEN" import \
  module.firestore.google_firestore_database.database projects/${PROJECT_ID}/databases/${FIRESTORE_DB} || echo "Firestore Database import failed or already imported."

# Secret Manager Secrets
echo "--- Importing Secrets ---"

# Additional secrets from config.yaml
for secret_name in ${ADDITIONAL_SECRETS}; do
  echo "Attempting to import secret: ${secret_name}"
  terraform -chdir=terraform -backend-config="bucket=$TF_STATE_BUCKET" -backend-config="access_token=$ACCESS_TOKEN" import \
  "module.secret_manager.google_secret_manager_secret.secrets[\"${secret_name}\"]" projects/${PROJECT_ID}/secrets/${secret_name} || echo "${secret_name} import failed or already imported."
done

echo "--- Finished attempting to import resources ---"


# 11. Run Terraform to deploy all infrastructure
echo "--- Running Terraform to deploy all services ---"
echo "Terraform will now ask you to enter the required secret values."
echo "Please paste the values in the format: { \"SECRET_NAME_1\" = \"value1\", \"SECRET_NAME_2\" = \"value2\" }"
echo "Note: The input will be hidden for security."
export GOOGLE_OAUTH_ACCESS_TOKEN="$ACCESS_TOKEN"
terraform -chdir=terraform apply -auto-approve -var-file="terraform.tfvars" \
  -var="access_token=$ACCESS_TOKEN"

echo "--- Deployment complete! ---"

# 12. Upload Google Ads Configuration to Firestore
echo "--- Uploading Google Ads Configuration to Firestore ---"
CONFIG_JSON="./config/samples/firestore_config.json"
UPLOAD_SCRIPT="./scripts/deployment/upload_config.py"

if [ -f "$CONFIG_JSON" ] && [ -f "$UPLOAD_SCRIPT" ]; then
    echo "   Uploading config from $CONFIG_JSON..."
    # Reuse the ACCESS_TOKEN generated earlier
    python3 "$UPLOAD_SCRIPT" \
        --project_id "$PROJECT_ID" \
        --database "$FIRESTORE_DB" \
        --config "$CONFIG_JSON" \
        --access_token "$ACCESS_TOKEN" || {
            echo "Error: Failed to upload configuration to Firestore."
            exit 1
        }
    echo "✅ Configuration uploaded successfully."
else
    echo "Warning: Configuration file or upload script not found. Skipping upload."
fi
# The cleanup function will be called automatically on exit.