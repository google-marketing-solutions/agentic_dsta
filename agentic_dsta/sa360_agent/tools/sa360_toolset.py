"""Tools for updating SA360 campaigns via a Google Sheet."""

import logging
import os
from typing import Any, Dict, List, Optional

from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from googleapiclient.errors import HttpError

from .sa360_utils import get_sheets_service

_SHEET_ID = os.environ.get("GOOGLE_SHEETS_ID")
_SHEET_NAME = os.environ.get("GOOGLE_SHEETS_NAME")

def get_campaign_details(campaign_id: str) -> Dict[str, Any]:
  """Fetches details for a specific SA360 campaign from the Google Sheet.

  Args:
      campaign_id: The ID of the campaign to fetch.

  Returns:
      A dictionary containing the campaign details, or an error message.
  """
  service = get_sheets_service()
  if not service:
    return {"error": "Failed to get Google Sheets service."}
  try:
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=_SHEET_ID, range=_SHEET_NAME)
        .execute()
    )
    values = result.get("values", [])
    if not values:
      return {"error": f"No data found in sheet '{_SHEET_NAME}'."}

    header = values[0]
    campaign_id_index = header.index("Campaign ID")

    for row in values[1:]:
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        return dict(zip(header, row))

    return {"error": f"Campaign with ID '{campaign_id}' not found."}

  except (HttpError, ValueError, IndexError) as err:
    logging.exception(err)
    return {"error": f"Failed to fetch campaign details: {err}"}


def _update_campaign_property(
    campaign_id: str, property_name: str, property_value: Any
) -> Dict[str, Any]:
  """Helper function to update a property for a campaign in the Google Sheet."""
  service = get_sheets_service()
  if not service:
    return {"error": "Failed to get Google Sheets service."}

  try:
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=_SHEET_ID, range=_SHEET_NAME)
        .execute()
    )
    values = result.get("values", [])

    if not values:
      return {"error": f"No data found in sheet '{_SHEET_NAME}'."}

    header = values[0]
    try:
      campaign_id_index = header.index("Campaign ID")
      property_index = header.index(property_name)
    except ValueError as err:
      logging.exception(err)
      return {"error": f"Column not found in sheet: {err}"}

    row_to_update = -1
    for i, row in enumerate(values[1:]):
      if len(row) > campaign_id_index and row[campaign_id_index] == campaign_id:
        row_to_update = i + 2
        break

    if row_to_update == -1:
      return {"error": f"Campaign with ID '{campaign_id}' not found."}

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

  except (HttpError, ValueError, IndexError) as err:
    logging.exception(err)
    return {"error": f"Failed to update campaign property: {err}"}


def enable_campaign(campaign_id: str) -> Dict[str, Any]:
  """Enables an SA360 campaign by setting its status to 'ENABLED'."""
  return _update_campaign_property(campaign_id, "Campaign status", "ENABLED")


def disable_campaign(campaign_id: str) -> Dict[str, Any]:
  """Disables an SA360 campaign by setting its status to 'PAUSED'."""
  return _update_campaign_property(campaign_id, "Campaign status", "PAUSED")


def update_campaign_geolocation(
    campaign_id: str, location_name: str
) -> Dict[str, Any]:
  """Updates the geo-targeting for an SA360 campaign in the Google Sheet."""
  return _update_campaign_property(
      campaign_id, "Location", location_name
  )


def update_campaign_budget(
    campaign_id: str, budget: float
) -> Dict[str, Any]:
  """Updates the budget for an SA360 campaign in the Google Sheet."""
  return _update_campaign_property(campaign_id, "Budget", budget)


class SA360Toolset(BaseToolset):
  """Toolset for managing SA360 campaigns via a Google Sheet."""

  def __init__(self):
    super().__init__()
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
    ]
