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