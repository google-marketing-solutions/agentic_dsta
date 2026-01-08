"""Tools for updating SA360 campaigns via a Google Sheet."""

import logging
from typing import Any, Dict, List, Optional

from agentic_dsta.tools.sa360.sa360_utils import get_sheets_service
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


def get_campaign_details(campaign_id: str, sheet_id: str, sheet_name: str) -> Dict[str, Any]:
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
        .get(spreadsheetId=sheet_id, range=sheet_name)
        .execute()
    )
    values = result.get("values", [])
    if not values:
      raise ValueError(f"No data found in sheet '{sheet_name}'.")

    header = values[0]
    campaign_id_index = header.index("Campaign ID")

    for row in values[1:]:
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        logger.info(f"Campaign details: {row[campaign_id_index]}")
        return dict(zip(header, row))

    raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

  except (HttpError, IndexError) as err:
    logger.error(err)
    raise RuntimeError(f"Failed to fetch campaign details: {err}") from err


def _update_campaign_property(
    campaign_id: str, property_name: str, property_value: Any, sheet_id: str, sheet_name: str
) -> Dict[str, Any]:
  """Helper function to update a property for a campaign in the Google Sheet."""
  service = get_sheets_service()
  if not service:
    raise RuntimeError("Failed to get Google Sheets service.")

  try:
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=sheet_id, range=sheet_name)
        .execute()
    )
    values = result.get("values", [])

    if not values:
      raise ValueError(f"No data found in sheet '{sheet_name}'.")

    header = values[0]
    try:
      campaign_id_index = header.index("Campaign ID")
      property_index = header.index(property_name)
    except ValueError as err:
      logger.error(err)
      raise ValueError(f"Column not found in sheet: {err}") from err

    row_to_update = -1
    for i, row in enumerate(values[1:]):
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        row_to_update = i + 2
        break

    if row_to_update == -1:
      raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

    property_column_letter = chr(ord("A") + property_index)
    range_to_update = f"{sheet_name}!{property_column_letter}{row_to_update}"

    body = {"values": [[property_value]]}
    sheet.values().update(
        spreadsheetId=sheet_id,
        range=range_to_update,
        valueInputOption="RAW",
        body=body,
    ).execute()
    logger.info(f"Campaign property updated: {property_name} to {property_value}")
    return {
        "success": (
            f"Campaign '{campaign_id}' {property_name} updated to"
            f" '{property_value}'."
        )
    }

  except (HttpError, IndexError) as err:
    logger.error(err)
    raise RuntimeError(f"Failed to update campaign property: {err}") from err


def update_campaign_status(
    campaign_id: str, status: str, sheet_id: str, sheet_name: str
) -> Dict[str, Any]:
  """Updates the status of an SA360 campaign to 'ENABLED' or 'PAUSED'.

  Args:
      campaign_id: The ID of the campaign to update.
      status: The new status for the campaign ('ENABLED' or 'PAUSED').

  Returns:
      A dictionary containing a success or error message.
  """
  upper_status = status.upper()
  if upper_status not in ["ENABLED", "PAUSED"]:
    return {"error": "Status must be either 'ENABLED' or 'PAUSED'."}
  return _update_campaign_property(
      campaign_id, "Campaign status", upper_status, sheet_id, sheet_name
  )


def update_campaign_geolocation(
    campaign_id: str,
    location_name: str,
    sheet_id: str,
    sheet_name: str,
    remove: bool = False,
) -> Dict[str, Any]:
  """Updates or removes the geo-targeting for an SA360 campaign in the Google Sheet.

  If 'remove' is True, a new record is created in the sheet to remove the
  geo-location. If 'remove' is False, the existing campaign's location is updated.

  Args:
      campaign_id: The ID of the campaign to modify.
      location_name: The name of the location to update or remove.
      sheet_id: The ID of the Google Sheet.
      sheet_name: The name of the sheet.
      remove: If True, the location will be removed. Defaults to False.

  Returns:
      A dictionary containing a success or error message.
  """
  if remove:
    details = get_campaign_details(campaign_id, sheet_id, sheet_name)
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
          .get(spreadsheetId=sheet_id, range=f"{sheet_name}!1:1")
          .execute()
      )
      header = header_result.get("values", [[]])[0]
      if not header:
        raise ValueError("Could not read header row from the sheet.")

      # Check for required columns for this operation
      if "Associated Campaign ID" not in header:
        raise ValueError("Sheet must contain 'Associated Campaign ID' column.")
      if "Action" not in header:
        raise ValueError("Sheet must contain 'Action' column.")
      if "Row Type" not in header:
        raise ValueError("Sheet must contain 'Row Type' column.")

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
          spreadsheetId=sheet_id,
          range=sheet_name,
          valueInputOption="RAW",
          body={"values": [new_row_values]},
      ).execute()
      logger.info(f"Geolocation removal record added for {location_name} for campaign {campaign_id}")
      return {
          "success": (
              f"Geolocation removal record for '{location_name}' added for campaign"
              f" '{campaign_id}'."
          )
      }

    except (HttpError, ValueError, IndexError) as err:
      logger.error(err)
      raise RuntimeError(f"Failed to remove campaign geolocation: {err}") from err
  else:
    return _update_campaign_property(
        campaign_id, "Location", location_name, sheet_id, sheet_name
    )


def update_campaign_budget(
    campaign_id: str, budget: float, sheet_id: str, sheet_name: str
) -> Dict[str, Any]:
  """Updates the budget for an SA360 campaign in the Google Sheet."""
  return _update_campaign_property(campaign_id, "Budget", budget, sheet_id, sheet_name)


class SA360Toolset(BaseToolset):
  """Toolset for managing SA360 campaigns via a Google Sheet."""

  def __init__(self):
    super().__init__()
    # Get sheet id and name here
    # get_firestore_data()
    self._get_campaign_details_tool = FunctionTool(
        func=get_campaign_details,
    )
    self._update_campaign_status_tool = FunctionTool(func=update_campaign_status)
    self._update_campaign_geolocation_tool = FunctionTool(
        func=update_campaign_geolocation
    )
    self._update_campaign_budget_tool = FunctionTool(
        func=update_campaign_budget
    )

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [
        self._get_campaign_details_tool,
        self._update_campaign_status_tool,
        self._update_campaign_geolocation_tool,
        self._update_campaign_budget_tool,
    ]
