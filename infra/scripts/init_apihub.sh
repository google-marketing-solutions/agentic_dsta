#!/bin/sh
set -e

PROJECT_ID=$1
LOCATION=$2
SPECS_DIR=$3

echo "Initializing API Hub in project $PROJECT_ID location $LOCATION"
echo "Specs dir: $SPECS_DIR"

if [ -z "$ACCOUNT_EMAIL" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "Error: ACCOUNT_EMAIL and ACCESS_TOKEN environment variables must be set."
  exit 1
fi

API_HUB_URL="https://apihub.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION"

create_api() {
  local api_id=$1
  local display_name=$2

  echo "Creating API: $api_id"
  curl -s -k -X POST "$API_HUB_URL/apis?apiId=$api_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"displayName\": \"$display_name\",
      \"owner\": {
         \"email\": \"$ACCOUNT_EMAIL\"
      }
    }" || echo "API $api_id creation possibly failed or already exists"
}

create_version() {
  local api_id=$1
  local version_id=$2
  local display_name=$3

  echo "Creating Version: $version_id for API $api_id"
  curl -s -k -X POST "$API_HUB_URL/apis/$api_id/versions?versionId=$version_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"displayName\": \"$display_name\"
    }" || echo "Version $version_id for API $api_id creation possibly failed or already exists"
}

create_spec() {
  local api_id=$1
  local version_id=$2
  local spec_id=$3
  local spec_file=$4

  echo "Creating Spec: $spec_id for API $api_id Version $version_id"

  if [ ! -f "$spec_file" ]; then
    echo "Error: Spec file not found: $spec_file"
    return 1
  fi

  content_b64=$(base64 -w 0 < "$spec_file")

  SPEC_TYPE_ATTR_NAME="projects/$PROJECT_ID/locations/$LOCATION/attributes/apihub-spec-type"

  # JSON payload for creating the spec
  JSON_PAYLOAD=$(cat <<EOF
{
  "displayName": "OpenAPI Spec for $api_id",
  "specType": {
    "attribute": "$SPEC_TYPE_ATTR_NAME",
    "enumValues": {
      "values": [{"id": "openapi"}]
    }
  },
  "contents": {
    "contents": "$content_b64",
    "mimeType": "application/vnd.oai.openapi+yaml"
  }
}
EOF
)

  echo "Payload for $spec_id:"
  echo "$JSON_PAYLOAD"

  curl -s -k -X POST "$API_HUB_URL/apis/$api_id/versions/$version_id/specs?specId=$spec_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" || echo "Spec $spec_id creation failed for API $api_id Version $version_id"
}

# Pollen API
create_api "pollen-api" "Google Pollen API"
create_version "pollen-api" "1-0-0" "Version 1.0.0"
create_spec "pollen-api" "1-0-0" "openapi-spec" "$SPECS_DIR/pollen-api-openapi.yaml"

# Weather API
create_api "weather-api" "Google Weather API"
create_version "weather-api" "1-0-0" "Version 1.0.0"
create_spec "weather-api" "1-0-0" "openapi-spec" "$SPECS_DIR/weather-api-openapi.yaml"

# Air Quality API
create_api "air-quality-api" "Google Air Quality API"
create_version "air-quality-api" "1-0-0" "Version 1.0.0"
create_spec "air-quality-api" "1-0-0" "openapi-spec" "$SPECS_DIR/air-quality-api-openapi.yaml"

echo "API Hub initialization complete."
