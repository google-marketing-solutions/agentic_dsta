"""Tools for updating SA360 campaigns via a Google Sheet."""

import logging
from typing import Any, Dict, List, Optional
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from googleapiclient.errors import HttpError

from .sa360_utils import get_sheets_service


def get_campaign_details(campaign_id: str, _SHEET_ID: str, _SHEET_NAME: str) -> Dict[str, Any]:
  """Fetches details for a specific SA360 campaign from the Google Sheet.

  Args:
      campaign_id: The ID of the campaign to fetch.

  Returns:
      A dictionary containing the campaign details, or an error message.
  """
  service = get_sheets_service()
  if not service:
    raise RuntimeError("Failed to get Google Sheets service.")
  try:
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=_SHEET_ID, range=_SHEET_NAME)
        .execute()
    )
    values = result.get("values", [])
    if not values:
      raise ValueError(f"No data found in sheet '{_SHEET_NAME}'.")

    header = values[0]
    campaign_id_index = header.index("Campaign ID")

    for row in values[1:]:
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        return dict(zip(header, row))

    raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

  except (HttpError, IndexError) as err:
    logging.exception(err)
    raise RuntimeError(f"Failed to fetch campaign details: {err}") from err


def _update_campaign_property(
    campaign_id: str, property_name: str, property_value: Any, _SHEET_ID: str, _SHEET_NAME: str
) -> Dict[str, Any]:
  """Helper function to update a property for a campaign in the Google Sheet."""
  service = get_sheets_service()
  if not service:
    raise RuntimeError("Failed to get Google Sheets service.")

  try:
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=_SHEET_ID, range=_SHEET_NAME)
        .execute()
    )
    values = result.get("values", [])

    if not values:
      raise ValueError(f"No data found in sheet '{_SHEET_NAME}'.")

    header = values[0]
    try:
      campaign_id_index = header.index("Campaign ID")
      property_index = header.index(property_name)
    except ValueError as err:
      logging.exception(err)
      raise ValueError(f"Column not found in sheet: {err}") from err

    row_to_update = -1
    for i, row in enumerate(values[1:]):
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        row_to_update = i + 2
        break

    if row_to_update == -1:
      raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

    property_column_letter = chr(ord("A") + property_index)
    range_to_update = f"{_SHEET_NAME}!{property_column_letter}{row_to_update}"

    body = {"values": [[property_value]]}
    sheet.values().update(
        spreadsheetId=_SHEET_ID,
        range=range_to_update,
        valueInputOption="RAW",
        body=body,
    ).execute()

    return {
        "success": (
            f"Campaign '{campaign_id}' {property_name} updated to"
            f" '{property_value}'."
        )
    }

  except (HttpError, IndexError) as err:
    logging.exception(err)
    raise RuntimeError(f"Failed to update campaign property: {err}") from err


def enable_campaign(campaign_id: str, _SHEET_ID: str, _SHEET_NAME: str) -> Dict[str, Any]:
  """Enables an SA360 campaign by setting its status to 'ENABLED'."""
  return _update_campaign_property(
      campaign_id, "Campaign status", "ENABLED", _SHEET_ID, _SHEET_NAME
  )


def disable_campaign(campaign_id: str, _SHEET_ID: str, _SHEET_NAME: str) -> Dict[str, Any]:
  """Disables an SA360 campaign by setting its status to 'PAUSED'."""
  return _update_campaign_property(
      campaign_id, "Campaign status", "PAUSED", _SHEET_ID, _SHEET_NAME
  )


def update_campaign_geolocation(
    campaign_id: str, location_name: str, _SHEET_ID: str, _SHEET_NAME: str
) -> Dict[str, Any]:
  """Updates the geo-targeting for an SA360 campaign in the Google Sheet."""
  return _update_campaign_property(
      campaign_id, "Location", location_name, _SHEET_ID, _SHEET_NAME
  )


def update_campaign_budget(
    campaign_id: str, budget: float, _SHEET_ID: str, _SHEET_NAME: str
) -> Dict[str, Any]:
  """Updates the budget for an SA360 campaign in the Google Sheet."""
  return _update_campaign_property(campaign_id, "Budget", budget, _SHEET_ID, _SHEET_NAME)


def remove_campaign_geolocation(
    campaign_id: str, location_name: str, _SHEET_ID: str, _SHEET_NAME: str
) -> Dict[str, Any]:
  """Creates a new record in the sheet to remove a geo-location for a campaign.

  This function works by creating a new row in the sheet that acts as a
  negative targeting record. It calls get_campaign_details to get the campaign's
  current settings, then adds a new row to the sheet for the location to be
  removed. It assumes the sheet has columns 'Associated Campaign ID' and
  'Action'.

  Args:
      campaign_id: The ID of the campaign to modify.
      location_name: The name of the location to remove.

  Returns:
      A dictionary containing a success or error message.
  """
  details = get_campaign_details(campaign_id, _SHEET_ID, _SHEET_NAME)
  if "error" in details:
    return details

  service = get_sheets_service()
  if not service:
    raise RuntimeError("Failed to get Google Sheets service.")

  try:
    sheet = service.spreadsheets()
    # Get header row to determine column order
    header_result = (
        sheet.values()
        .get(spreadsheetId=_SHEET_ID, range=f"{_SHEET_NAME}!1:1")
        .execute()
    )
    header = header_result.get("values", [[]])[0]
    if not header:
      raise ValueError(f"Could not read header row from the sheet.")

    # Check for required columns for this operation
    if "Associated Campaign ID" not in header:
      raise ValueError(f"Sheet must contain 'Associated Campaign ID' column.")
    if "Action" not in header:
      raise ValueError(f"Sheet must contain 'Action' column.")
    if "Row Type" not in header:
      raise ValueError(f"Sheet must contain 'Row Type' column.")

    # Prepare the new row
    new_row_dict = {
        "Row Type": "excluded location",
        "Action": "deactivate",
        "Customer ID": details.get("Customer ID"),
        "Campaign": details.get("Campaign"),
        "Location": location_name,
        "EU political ads": details.get("EU political ads"),
        "Associated Campaign ID": campaign_id,
    }

    # Convert dict to list in the correct order for insertion
    new_row_values = [new_row_dict.get(h, "") for h in header]

    # Append the new row to the sheet
    sheet.values().append(
        spreadsheetId=_SHEET_ID,
        range=_SHEET_NAME,
        valueInputOption="RAW",
        body={"values": [new_row_values]},
    ).execute()

    return {
        "success": (
            f"Geolocation removal record for '{location_name}' added for campaign"
            f" '{campaign_id}'."
        )
    }

  except (HttpError, ValueError, IndexError) as err:
    logging.exception(err)
    raise RuntimeError(f"Failed to remove campaign geolocation: {err}") from err


class SA360Toolset(BaseToolset):
  """Toolset for managing SA360 campaigns via a Google Sheet."""

  def __init__(self):
    super().__init__()
    # Get sheet id and name here
    # get_firestore_data()
    self._get_campaign_details_tool = FunctionTool(
        func=get_campaign_details,
    )
    self._enable_campaign_tool = FunctionTool(func=enable_campaign)
    self._disable_campaign_tool = FunctionTool(func=disable_campaign)
    self._update_campaign_geolocation_tool = FunctionTool(
        func=update_campaign_geolocation
    )
    self._update_campaign_budget_tool = FunctionTool(
        func=update_campaign_budget
    )
    self._remove_campaign_geolocation_tool = FunctionTool(
        func=remove_campaign_geolocation
    )

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [
        self._get_campaign_details_tool,
        self._enable_campaign_tool,
        self._disable_campaign_tool,
        self._update_campaign_geolocation_tool,
        self._update_campaign_budget_tool,
        self._remove_campaign_geolocation_tool,
    ]
