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

#!/bin/sh
set -e

PROJECT_ID=$1
LOCATION=$2
SPECS_DIR=$3

echo "Initializing API Hub in project $PROJECT_ID location $LOCATION"
echo "Specs dir: $SPECS_DIR"

if [ -z "$ACCOUNT_EMAIL" ]; then
  echo "Error: ACCOUNT_EMAIL environment variables must be set."
  exit 1
fi

if [ -z "$ACCESS_TOKEN" ]; then
  echo "Error: Failed to retrieve access token for $ACCOUNT_EMAIL."
  exit 1
fi

# Wrapper for curl to handle HTTP errors
# Returns 1 if 409 Conflict occurs, exits on any other error >= 400
run_curl() {
  local outfile
  outfile=$(mktemp)
  local http_code
  http_code=$(curl -sSk -w "%{http_code}" -o "$outfile" "$@")
  local exit_status=0
  if [ "$http_code" -ge 400 ] && [ "$http_code" -ne 409 ]; then
    echo "ERROR: curl command failed with HTTP status $http_code:" >&2
    cat "$outfile" >&2
    rm "$outfile"
    exit 1
  elif [ "$http_code" -eq 409 ]; then
    echo "WARN: Resource already exists (HTTP 409)." >&2
    exit_status=1
  fi
  rm "$outfile"
  return $exit_status
}

# Source variables
. "$(dirname "$0")/apihub_vars.sh"

API_HUB_URL="https://apihub.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION"

create_api() {
  local api_id=$1
  local display_name=$2
  local payload="{
      \"displayName\": \"$display_name\",
      \"owner\": {
         \"email\": \"$ACCOUNT_EMAIL\"
      }
    }"

  echo "Attempting to create API: $api_id"
  if run_curl -X POST "$API_HUB_URL/apis?apiId=$api_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload"
  then
    echo "API $api_id created successfully."
  else
    echo "API $api_id seems to exist (got 409), attempting update..."
    run_curl -X PATCH "$API_HUB_URL/apis/$api_id?updateMask=displayName,owner" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload"
    echo "API $api_id updated."
  fi
}

create_version() {
  local api_id=$1
  local version_id=$2
  local display_name=$3
  local payload="{
      \"displayName\": \"$display_name\"
    }"

  echo "Attempting to create Version: $version_id for API $api_id"
  if run_curl -X POST "$API_HUB_URL/apis/$api_id/versions?versionId=$version_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload"
  then
    echo "Version $version_id for API $api_id created successfully."
  else
    echo "Version $version_id for API $api_id seems to exist (got 409), attempting update..."
    run_curl -X PATCH "$API_HUB_URL/apis/$api_id/versions/$version_id?updateMask=displayName" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$payload"
    echo "Version $version_id for API $api_id updated."
  fi
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

  SPEC_TYPE_ATTR_NAME="projects/$PROJECT_ID/locations/$LOCATION/attributes/$SPEC_TYPE_ATTRIBUTE_ID"

  # JSON payload for creating the spec
  JSON_PAYLOAD=$(cat <<EOF
{
  "displayName": "$SPEC_DISPLAY_NAME_PREFIX $api_id",
  "specType": {
    "attribute": "$SPEC_TYPE_ATTR_NAME",
    "enumValues": {
      "values": [{"id": "$SPEC_TYPE_ID"}]
    }
  },
  "contents": {
    "contents": "$content_b64",
    "mimeType": "$SPEC_MIME_TYPE"
  }
}
EOF
)

  echo "Payload for $spec_id:"
  echo "$JSON_PAYLOAD"

  echo "Attempting to create spec $spec_id..."
  if run_curl -X POST "$API_HUB_URL/apis/$api_id/versions/$version_id/specs?specId=$spec_id" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD"
  then
    echo "Spec $spec_id created successfully."
  else
    echo "Spec $spec_id seems to exist (got 409), attempting update..."
    # 409 means it exists, so we PATCH to update
    run_curl -X PATCH "$API_HUB_URL/apis/$api_id/versions/$version_id/specs/$spec_id?updateMask=displayName,contents,specType" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$JSON_PAYLOAD"
    echo "Spec $spec_id updated."
  fi
}

# Pollen API
create_api "$POLLEN_API_ID" "$POLLEN_API_DISPLAY_NAME"
create_version "$POLLEN_API_ID" "$API_VERSION_ID" "$API_VERSION_DISPLAY_NAME"
create_spec "$POLLEN_API_ID" "$API_VERSION_ID" "$API_SPEC_ID" "$SPECS_DIR/$POLLEN_API_SPEC_FILE"

# Weather API
create_api "$WEATHER_API_ID" "$WEATHER_API_DISPLAY_NAME"
create_version "$WEATHER_API_ID" "$API_VERSION_ID" "$API_VERSION_DISPLAY_NAME"
create_spec "$WEATHER_API_ID" "$API_VERSION_ID" "$API_SPEC_ID" "$SPECS_DIR/$WEATHER_API_SPEC_FILE"

# Air Quality API
create_api "$AIR_QUALITY_API_ID" "$AIR_QUALITY_API_DISPLAY_NAME"
create_version "$AIR_QUALITY_API_ID" "$API_VERSION_ID" "$API_VERSION_DISPLAY_NAME"
create_spec "$AIR_QUALITY_API_ID" "$API_VERSION_ID" "$API_SPEC_ID" "$SPECS_DIR/$AIR_QUALITY_API_SPEC_FILE"

echo "API Hub initialization complete."