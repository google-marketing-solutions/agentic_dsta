#!/bin/bash
set -e

# Usage: ./build_image.sh <PROJECT_ID> <REGION> <REPO_NAME> <IMAGE_NAME>
PROJECT_ID=$1
REGION=$2
REPO_NAME=$3
IMAGE_NAME=$4
TAG="latest"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$REPO_NAME" ] || [ -z "$IMAGE_NAME" ]; then
  echo "Error: Missing required arguments."
  echo "Usage: $0 <PROJECT_ID> <REGION> <REPO_NAME> <IMAGE_NAME>"
  exit 1
fi

echo "1. Enabling required APIs (Artifact Registry & Cloud Build)..."
gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com --project "$PROJECT_ID" >/dev/null 2>&1

echo "2. Checking Artifact Registry repository '$REPO_NAME'..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --project "$PROJECT_ID" --location "$REGION" &>/dev/null; then
  echo "   Creating repository '$REPO_NAME' in '$REGION'..."
  gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker repository for Agentic DSTA" \
    --project="$PROJECT_ID"
else
  echo "   Repository '$REPO_NAME' already exists."
fi

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"

echo "3. Building and Pushing container image to: $IMAGE_URL"
# Determine the source directory relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The source directory is two levels up from the script directory
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="$PROJECT_ROOT/agentic_dsta"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source directory not found at $SOURCE_DIR"
  exit 1
fi

BUILD_ID=$(gcloud builds submit "$SOURCE_DIR" \
  --tag "$IMAGE_URL" \
  --project "$PROJECT_ID" \
  --format='value(id)')

# The image URL is now constructed in the deploy.sh script.

echo "✅ Build Complete."
