
import functools
import os

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yaml
import logging


def load_config():
  """Load agent configuration from YAML file."""
  #config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
  # Get the directory of the current file (utils.py)
  current_dir = os.path.dirname(__file__)

  # Go up one level and join with config.yaml
  config_path = os.path.abspath(os.path.join(current_dir, '..', 'config.yaml'))


  with open(config_path, "r") as f:
    config = yaml.safe_load(f)
  return config["model"], config["instruction"]


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
    logging.exception(f"Failed to create Google Sheets service: {err}")
    return None
