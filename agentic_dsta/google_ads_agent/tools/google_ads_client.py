# Copyright 2025 Google LLC
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
"""Shared utility for initializing the Google Ads API client."""

import os
import google.ads.googleads.client
from google.ads.googleads.errors import GoogleAdsException
import google.auth
import google.auth.exceptions


def get_google_ads_client(customer_id: str):
  """Initializes and returns a GoogleAdsClient."""
  try:
    try:
      # First, try to use Application Default Credentials.
      credentials, _ = google.auth.default()
      # Pass the credentials object directly to the client constructor.
      return google.ads.googleads.client.GoogleAdsClient(
          credentials,
          login_customer_id=customer_id,
          developer_token=os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
          use_proto_plus=True,
      )
    except google.auth.exceptions.DefaultCredentialsError:
      # If ADC are not found, fall back to environment variables.
      config_data = {
          "login_customer_id": customer_id,
          "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
          "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
          "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
          "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
          "token_uri": "https://oauth2.googleapis.com/token",
          "use_proto_plus": True,
      }
      return google.ads.googleads.client.GoogleAdsClient.load_from_dict(
          config_data
      )
  except GoogleAdsException as ex:
    print(f"Failed to create GoogleAdsClient: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return None
