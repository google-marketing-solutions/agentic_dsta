import functools
import logging

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Any, Dict, List, Optional


@functools.lru_cache()
def get_sheets_service():
  """Initializes and returns a Google Sheets API service."""
  try:
    # Authentication is handled by the environment using Application Default
    # Credentials (ADC). When running locally, you can authenticate by running:
    # gcloud auth application-default login
    #
    # To write to Google Sheets, the credentials need the right OAuth scope.
    # Added sheet and drive scopes for now
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.readonly"]
    )

    # The principal (user or service account) that authenticated also needs to
    # have at least "Editor" access to the Google Sheet.
    service = build("sheets", "v4", credentials=credentials)
    return service
  except google.auth.exceptions.DefaultCredentialsError:
    logging.exception(
        "Could not find default credentials. Please run "
        "'gcloud auth application-default login' if you are running locally."
    )
    return None
  except HttpError as err:
    logging.exception("Failed to create Google Sheets service: %s", err)
    return None


@functools.lru_cache()
def get_reporting_api_client():
  """Initializes and returns a SA360 Reporting API service."""
  try:
    # Authentication is handled by the environment using Application Default
    # Credentials (ADC). When running locally, you can authenticate by running:
    # gcloud auth application-default login
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/doubleclicksearch"]
    )

    service = build(
        serviceName="searchads360",
        version="v0",
        credentials=credentials,
        static_discovery=False,
    )
    return service
  except google.auth.exceptions.DefaultCredentialsError:
    logging.exception(
        "Could not find default credentials. Please run "
        "'gcloud auth application-default login' if you are running locally."
    )
    return None
  except HttpError as err:
    logging.exception("Failed to create SA360 Reporting service: %s", err)
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
  print("*******************************************")
  print(sheet_row.get("Campaign ID"))
  print(sheet_row.get("Campaign"))
  print(sheet_row.get("Campaign status"))
  print(sheet_row.get("Campaign type"))
  print(sheet_row.get("Budget"))
  print(sheet_row.get("Bid strategy type"))
  print(sheet_row.get("Campaign start date"))
  print(sheet_row.get("Campaign end date"))
  print(sheet_row.get("Location"))
  print("*******************************************")
  print(sa360_campaign["campaign"]["id"])
  print(sa360_campaign["campaign"]["name"])
  print(sa360_campaign["campaign"].get("status"))
  print(sa360_campaign["campaign"].get("advertisingChannelType"))
  print(sa360_campaign["campaign"].get("budget"))
  print(sa360_campaign["campaign"].get("biddingStrategyType"))
  print(sa360_campaign["campaign"].get("startDate"))
  print(sa360_campaign["campaign"].get("endDate"))
  print(sa360_campaign["campaign"].get("location"))
  print("*******************************************")
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