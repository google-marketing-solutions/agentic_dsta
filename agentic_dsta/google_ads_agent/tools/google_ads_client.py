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
import logging


logger = logging.getLogger(__name__)


def get_google_ads_client(customer_id: str):
  logger.debug("get_google_ads_client called", extra={'customer_id': customer_id})
  """Initializes and returns a GoogleAdsClient."""
  try:
    try:
      logger.debug("Attempting to use Application Default Credentials.")
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
      logger.debug("ADC not found, falling back to environment variables.")
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
    logger.error(
        "Failed to create GoogleAdsClient",
        exc_info=True,
        extra={'customer_id': customer_id}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    return None

if __name__ == '__main__':
    logger.info("Testing logger - INFO", extra={'test_case': 123, 'user': 'test_user'})
    logger.warning("Testing logger - WARNING")
    try:
        raise ValueError("Something went wrong")
    except ValueError:
        logger.error("Testing logger - ERROR with exception", exc_info=True, extra={'foo': 'bar'})
    logger.debug("This DEBUG message should not appear with default LOG_LEVEL=INFO")
