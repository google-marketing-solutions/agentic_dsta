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

#!/bin/bash
set -e
set -x

# Change to the script's directory to ensure relative paths are correct.
cd "$(dirname "$0")"

# --- Cleanup ---
cleanup() {
  echo "--- Cleaning up authentication settings ---"
  gcloud config unset auth/impersonate_service_account >/dev/null 2>&1 || true
}
trap cleanup EXIT

# --- Configuration ---
CONFIG_FILE="config/app/config.yaml"

# --- Functions ---
function get_config_value() {
  python3 -c "import yaml; print(yaml.safe_load(open('$1'))['$2'])"
}

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

# 2. Get configuration from config.yaml
PROJECT_ID=$(get_config_value "$CONFIG_FILE" "project_id")
REGION=$(get_config_value "$CONFIG_FILE" "region")
RESOURCE_PREFIX=$(get_config_value "$CONFIG_FILE" "resource_prefix")

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$RESOURCE_PREFIX" ]; then
  echo "Error: 'project_id', 'region', and 'resource_prefix' must be set in $CONFIG_FILE."
  exit 1
fi

# --- Derived Resource Names ---
SA_NAME="${RESOURCE_PREFIX}-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
TF_STATE_BUCKET="agentic-dsta-tf-state-${PROJECT_ID}"

echo "Configuration for destroy:"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Resource Prefix: $RESOURCE_PREFIX"
echo "Service Account: $SA_EMAIL"
echo "TF State Bucket: $TF_STATE_BUCKET"

# 3. Configure gcloud to use service account impersonation
echo "--- Configuring authentication to impersonate Service Account: $SA_EMAIL ---"
gcloud config set auth/impersonate_service_account "$SA_EMAIL"

# 4. Generate Access Token & Initialize Terraform
echo "--- Generating Access Token and Initializing Terraform for Destroy ---"
ACCESS_TOKEN=$(gcloud auth print-access-token --impersonate-service-account="$SA_EMAIL")
if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to retrieve access token for $SA_EMAIL."
    exit 1
fi

terraform -chdir=terraform init -upgrade -reconfigure \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="access_token=$ACCESS_TOKEN"

# 5. Run Terraform Destroy
echo "--- Running Terraform Destroy ---"
echo "WARNING: This will destroy all resources managed by this Terraform configuration."
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Destroy cancelled."
    exit 0
fi

export GOOGLE_OAUTH_ACCESS_TOKEN="$ACCESS_TOKEN"
terraform -chdir=terraform destroy -var-file="terraform.tfvars" \
  -var="access_token=$ACCESS_TOKEN" -auto-approve

echo "--- Destroy complete! ---"
