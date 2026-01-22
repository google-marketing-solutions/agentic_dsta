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
import functools
import logging
import os

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Any, Dict, List, Optional
from agentic_dsta.tools import auth_utils

logger = logging.getLogger(__name__)

@functools.lru_cache()
def get_sheets_service():
  """Initializes and returns a Google Sheets API service."""
  scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly"]
  try:
      # Using auth_utils for sheets as well for consistency
      credentials = auth_utils.get_credentials(
          scopes=scopes,
          service_name="Google Sheets"
      )

      if not credentials:
          logger.error("Failed to obtain credentials for Google Sheets service")
          return None

      service = build("sheets", "v4", credentials=credentials)
      return service
  except HttpError as err:
    logging.exception("Failed to create Google Sheets service: %s", err)
    return None
  except Exception as e:
      logging.exception(f"Error creating Google Sheets service: {e}")
      return None

@functools.lru_cache()
def get_reporting_api_client():
  """Initializes and returns a SA360 Reporting API service.\n\n  Authentication is controlled by auth_utils.get_credentials, potentially using\n  the SA360_FORCE_USER_CREDS environment variable to force user creds\n  from Secret Manager.
  """
  scopes = ["https://www.googleapis.com/auth/doubleclicksearch"]
  try:
      credentials = auth_utils.get_credentials(
          scopes=scopes, 
          service_name="SA360",
          force_user_creds_env="SA360_FORCE_USER_CREDS"
      )

      if not credentials:
          logger.error("Failed to obtain credentials for SA360 client")
          return None
      logger.debug("Successfully got credentials for SA360")

      service = build(
          serviceName="searchads360",
          version="v0",
          credentials=credentials,
          static_discovery=False,
      )
      logger.debug("SA360 service built successfully")
      return service
  except HttpError as err:
      logging.exception(f"Failed to create SA360 Reporting service: {err}")
      return None
  except Exception as e:
      logging.exception(f"Error creating SA360 client: {e}")
      return None

def compare_campaign_data(
    sheet_row: Dict[str, Any], sa360_campaign: Dict[str, Any]
) -> bool:
  """Compares campaign data from a Google Sheet row and SA360 Reporting API.

  Args:
      sheet_row: A dictionary representing a row from a Google Sheet.
      sa360_campaign: A dictionary representing campaign details from the SA360
        Reporting API.

  Returns:
      True if the specified fields match, False otherwise.
  """
  if sheet_row.get("Campaign ID") and len(str(sheet_row.get("Campaign ID")).strip())>0 and str(sheet_row.get("Campaign ID")) != str(sa360_campaign["campaign"]["id"]):
    return False
  if sheet_row.get("Campaign") and len(str(sheet_row.get("Campaign")).strip())>0 and str(sheet_row.get("Campaign")) != sa360_campaign["campaign"]["name"]:
    return False
  if sheet_row.get("Campaign status") and len(str(sheet_row.get("Campaign status")).strip())>0 and sheet_row.get("Campaign status", "").upper() != sa360_campaign["campaign"].get("status", "").upper():
    return False
  if sheet_row.get("Campaign type") and len(str(sheet_row.get("Campaign type")).strip())>0 and sheet_row.get("Campaign type", "").upper() != sa360_campaign["campaign"].get("advertisingChannelType", "").upper():
    return False
  try:
    if sheet_row.get("Budget"):
      sheet_budget = float(sheet_row.get("Budget", 0.0))
      api_budget = float(sa360_campaign["campaign"].get("budget", 0.0))
      if abs(sheet_budget - api_budget) > 1e-6:
        return False
  except (ValueError, TypeError):
    return False
  if sheet_row.get("Bid strategy type") and len(
      str(sheet_row.get("Bid strategy type")).strip()
  ) > 0:
    sheet_bid_strategy = (
        str(sheet_row.get("Bid strategy type")).lower().replace("_", " ")
    )
    api_bid_strategy = (
        str(sa360_campaign["campaign"].get("biddingStrategyType", ""))
        .lower()
        .replace("_", " ")
    )
    if sheet_bid_strategy != api_bid_strategy:
      return False
  if sheet_row.get("Campaign start date") and len(str(sheet_row.get("Campaign start date")).strip())>0 and sheet_row.get("Campaign start date") != sa360_campaign["campaign"].get("startDate"):
    return False
  if sheet_row.get("Campaign end date") and len(str(sheet_row.get("Campaign end date")).strip())>0 and sheet_row.get("Campaign end date") != sa360_campaign["campaign"].get("endDate"):
    return False

  if sheet_row.get("Location") and len(str(sheet_row.get("Location")).strip())>0:
    sheet_locations_str = sheet_row.get("Location", "")
    if not isinstance(sheet_locations_str, str):
      sheet_locations_str = str(sheet_locations_str)
    sheet_locations = sorted(
        [loc.strip() for loc in sheet_locations_str.split(",") if loc.strip()]
    )
    api_locations = sorted(sa360_campaign["campaign"].get("location", []))
    if sheet_locations != api_locations:
      return False

  return True

if __name__ == '__main__':
    # This block is for local testing and demonstration.
    # It attempts to initialize the SA360 and Sheets clients using Application Default Credentials.
    # Ensure you have run 'gcloud auth application-default login' locally for this to work.
    logging.basicConfig(level=logging.DEBUG)

    print("--- Testing SA360 Client ---")
    try:
        sa360_client = get_reporting_api_client()
        if sa360_client:
            print("Successfully obtained SA360 client locally.")
            # Optional: Try a simple test call
            try:
                # Replace with a customer ID you have access to
                test_customer_id = "6621513488"
                query = "SELECT customer.id FROM customer"
                print(f"Running SA360 test query for customer ID: {test_customer_id}...")
                request = sa360_client.customers().searchAds360().search(
                    customerId=test_customer_id, body={"query": query}
                )
                response = request.execute()
                print(f"SA360 Test query response: {response}")
            except Exception as e:
                print(f"Error during SA360 test query: {e}")
        else:
            print("Failed to obtain SA360 client locally. Client is None.")
    except Exception as e:
        print(f"Error getting SA360 client locally: {e}")

    print("\n--- Testing Sheets Client ---")
    try:
        sheets_client = get_sheets_service()
        if sheets_client:
            print("Successfully obtained Sheets client locally.")
        else:
            print("Failed to obtain Sheets client locally. Client is None.")
    except Exception as e:
        print(f"Error getting Sheets client locally: {e}")