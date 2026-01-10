import functools
import logging

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


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