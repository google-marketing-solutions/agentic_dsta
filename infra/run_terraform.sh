#!/bin/bash
set -e

# /google/bin/releases/g3terraform/runner_main --base_service_dir=$(pwd) --config_dir=. "$@"

# --- Configuration ---
CONFIG_FILE="config.yaml"
TFVARS_FILE="terraform.tfvars"
IMAGE_BUILD_SCRIPT="./scripts/build_image.sh"
TFVARS_GEN_SCRIPT="./scripts/generate_tfvars.py"

# gcloud builds submit --tag us-central1-docker.pkg.dev/styagi-test/agentic-dsta-repo/agentic-dsta

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
if [ ! -f "$IMAGE_BUILD_SCRIPT" ]; then
    echo "Error: Image build script '$IMAGE_BUILD_SCRIPT' not found."
    exit 1
fi
if [ ! -f "$TFVARS_GEN_SCRIPT" ]; then
    echo "Error: Tfvars generation script '$TFVARS_GEN_SCRIPT' not found."
    exit 1
fi


# 2. Get Project ID and Region from config.yaml
PROJECT_ID=$(get_config_value "$CONFIG_FILE" "project_id")
REGION=$(get_config_value "$CONFIG_FILE" "region")

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "Error: 'project_id' and 'region' must be set in $CONFIG_FILE"
  exit 1
fi

# 3. Build container image and get the URL
echo "--- Building and pushing container image ---"
# The build_image.sh script outputs the image URL, so we capture it.
IMAGE_URL=$($IMAGE_BUILD_SCRIPT "$PROJECT_ID" "$REGION" | grep "image_url =" | awk -F '"' '{print $2}')

if [ -z "$IMAGE_URL" ]; then
    echo "Error: Failed to get image_url from the build script."
    exit 1
fi
echo "Image URL: $IMAGE_URL"

# 4. Generate terraform.tfvars from config.yaml
echo "--- Generating terraform.tfvars ---"
python3 "$TFVARS_GEN_SCRIPT" "$CONFIG_FILE" "$TFVARS_FILE"

# 5. Append the dynamic image_url to terraform.tfvars
echo "--- Appending image_url to terraform.tfvars ---"
echo "image_url = \"$IMAGE_URL\"" >> "$TFVARS_FILE"

# 6. Run Terraform
echo "--- Running Terraform ---"
terraform init -upgrade
terraform apply -auto-approve -var-file="$TFVARS_FILE"

echo "--- Deployment complete! ---"
