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
import logging
from agentic_dsta.tools import auth_utils

logger = logging.getLogger(__name__)

def get_google_ads_client(customer_id: str):
  logger.debug("get_google_ads_client called", extra={'customer_id': customer_id})
  """Initializes and returns a GoogleAdsClient.\n\n  Authentication is controlled by auth_utils.get_credentials, potentially using\n  the GOOGLE_ADS_FORCE_USER_CREDS environment variable to force user creds\n  from Secret Manager.\n  """
  scopes = ["https://www.googleapis.com/auth/adwords"]
  try:
      credentials = auth_utils.get_credentials(
          scopes=scopes,
          service_name="Google Ads",
          force_user_creds_env="GOOGLE_ADS_FORCE_USER_CREDS"
      )

      if not credentials:
          logger.error("Failed to obtain credentials for Google Ads client")
          return None

      developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
      if not developer_token:
          logger.error("GOOGLE_ADS_DEVELOPER_TOKEN not set in environment.")
          return None

      return google.ads.googleads.client.GoogleAdsClient(
          credentials,
          login_customer_id=customer_id,
          developer_token=developer_token,
          use_proto_plus=True,
      )
  except GoogleAdsException as ex:
    logger.error(
        "Failed to create GoogleAdsClient",
        exc_info=True,
        extra={'customer_id': customer_id}
    )
    if hasattr(ex, 'failure') and ex.failure:
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
  except Exception as e:
      logger.exception(f"Error creating GoogleAdsClient: {e}")
      return None
