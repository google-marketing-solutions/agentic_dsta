"""Tools for updating SA360 campaigns via a Google Sheet."""

import logging
from typing import Any, Dict, List, Optional

from agentic_dsta.tools.sa360.sa360_utils import get_sheets_service, get_reporting_api_client, compare_campaign_data
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def get_locations(campaign_id: str, customer_id: str, service):
  # 1. Fetch the IDs
  ids_query = f"""
      SELECT
        campaign_criterion.location.geo_target_constant
      FROM campaign_criterion
      WHERE campaign.id = {campaign_id}
        AND campaign_criterion.type = 'LOCATION'
  """
  request = service.customers().searchAds360().search(
        customerId=customer_id,
        body={'query': ids_query}
    )
  response = request.execute()

  # Collect all resource names into a list
  geo_resource_names = []
  if "results" in response:
    for result in response["results"]:
      criterion = result.get("campaignCriterion", {})
      location = criterion.get("location", {})
      geo_target = location.get("geoTargetConstant")
      if geo_target:
        geo_ind = geo_target.rfind("/")
        geo_resource_names.append(f"'geoTargetConstants/{geo_target[geo_ind+1:]}'")
        # geo_resource_names.append(geo_target)


  # 2. Fetch the Names (if locations were found)
  if geo_resource_names:
      names_query = f"""
          SELECT
            geo_target_constant.resource_name,
            geo_target_constant.name,
            geo_target_constant.canonical_name,
            geo_target_constant.country_code
          FROM geo_target_constant
          WHERE geo_target_constant.resource_name IN ({",".join(geo_resource_names)})
      """
      request = service.customers().searchAds360().search(
        customerId=customer_id,
        body={'query': names_query}
      )
  response = request.execute()

  geo_list = []

  for row in response.get('results', []):
      # Extract the canonical name from the geoTargetConstant object
      location_string = row.get('geoTargetConstant', {}).get('canonicalName')
      if location_string:
          geo_list.append(location_string)

  return geo_list


def get_sa360_campaign_details(campaign_id: str, customer_id: str) -> Dict[str, Any]:
  """Fetches details for a specific SA360 campaign.

  Args:
      campaign_id: The ID of the campaign to fetch.
      customer_id: The ID of the customer.

  Returns:
      A dictionary containing the campaign details.

  Raises:
    ValueError: If the campaign with the given ID is not found or if the
      customer_id is not a valid 10-digit value.
    RuntimeError: If an API error occurs.
  """
  if not customer_id.isdigit() or len(customer_id) != 10:
    raise ValueError("customer_id must be a 10-digit value.")
  service = get_reporting_api_client()
  if not service:
    raise RuntimeError("Failed to get SA360 Reporting API client.")

  search_query = f"""
      SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.labels,
        campaign.tracking_url_template,
        campaign.url_custom_parameters,
        campaign.url_expansion_opt_out,
        -- Valid budget fields in v0
        campaign.campaign_budget, -- This returns the resource_name (contains the ID)
        campaign_budget.amount_micros,
        campaign_budget.delivery_method,
        campaign_budget.period,
        -- Campaign settings
        campaign.geo_target_type_setting.negative_geo_target_type,
        campaign.geo_target_type_setting.positive_geo_target_type,
        campaign.serving_status,
        campaign.ad_serving_optimization_status,
        campaign.advertising_channel_type,  --campaign type
        campaign.advertising_channel_sub_type,
        campaign.engine_id,
        campaign.start_date,
        campaign.end_date,
        campaign.bidding_strategy_type,
        campaign.bidding_strategy,
        campaign.tracking_url_template,
        campaign.final_url_suffix,
        campaign.network_settings.target_google_search,  --networks
        campaign.network_settings.target_search_network,
        campaign.network_settings.target_content_network,
        campaign.network_settings.target_partner_search_network,  --networks
        campaign.target_cpa.target_cpa_micros,
        campaign.target_roas.target_roas,
        campaign.target_impression_share.location,
        campaign.target_impression_share.cpc_bid_ceiling_micros,
        campaign.selective_optimization.conversion_actions,
        campaign.dynamic_search_ads_setting.domain_name
      FROM campaign
      WHERE campaign.id = {campaign_id}
    """

  criterion_query = f"""
    SELECT
        campaign.id,
        campaign_criterion.criterion_id,
        campaign_criterion.type,
        campaign_criterion.negative,
        campaign_criterion.device.type,
        campaign_criterion.bid_modifier
        FROM campaign_criterion
        WHERE campaign_criterion.type IN ('LANGUAGE', 'DEVICE')
        AND campaign.id = {campaign_id}
  """

  try:
    request = service.customers().searchAds360().search(
        customerId=customer_id,
        body={'query': search_query}
    )
    response = request.execute()

    request_criterion = service.customers().searchAds360().search(
        customerId=customer_id,
        body={'query': criterion_query}
    )
    criterion_response = request_criterion.execute()
    response["results"][0]["campaignCriterion"] = criterion_response["results"]

    if "results" in response and response["results"]:
      res = {"campaign": response["results"][0].get("campaign",{}), "campaignBudget":response["results"][0].get("campaignBudget",{}), "campaignCriterion":response["results"][0].get("campaignCriterion")}
      if res["campaignBudget"].get("amountMicros") and res["campaignBudget"]["amountMicros"].isdigit():
        res["campaign"]["budget"] = float(res["campaignBudget"]["amountMicros"]) / 1000000
      else:
        res["campaign"]["budget"] = 0.0
      res["campaign"]["location"] = get_locations(campaign_id, customer_id, service)
      return res
    raise ValueError(f"Campaign with ID '{campaign_id}' not found.")
  except HttpError as err:
    logging.exception(err)
    raise RuntimeError(f"Failed to fetch campaign details: {err}") from err


def get_sa360_campaign_details_sheet(campaign_id: str, sheet_id: str, sheet_name: str) -> Dict[str, Any]:
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


def update_sa360_campaign_status(
    campaign_id: str, status: str, sheet_id: str, sheet_name: str, customer_id: str
) -> Dict[str, Any]:
  """Updates the status of an SA360 campaign to 'ENABLED' or 'PAUSED'.

  Args:
      campaign_id: The ID of the campaign to update.
      status: The new status for the campaign ('ENABLED' or 'PAUSED').

  Returns:
      A dictionary containing a success or error message.
  """
  if compare_campaign_data(get_sa360_campaign_details_sheet(campaign_id, sheet_id, sheet_name), get_sa360_campaign_details(campaign_id, customer_id)):
    upper_status = status.upper()
    if upper_status not in ["ENABLED", "PAUSED"]:
      return {"error": "Status must be either 'ENABLED' or 'PAUSED'."}
    return _update_campaign_property(
        campaign_id, "Campaign status", upper_status, sheet_id, sheet_name
    )
  else:
    _update_campaign_property(campaign_id, "Row Type", "", sheet_id, sheet_name)
    raise RuntimeError("Data mismatch between Google Sheet and SA360 API.")


def update_sa360_campaign_geolocation(
    campaign_id: str,
    location_name: str,
    sheet_id: str,
    sheet_name: str,
    customer_id: str,
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
      customer_id: The ID of the customer.
      remove: If True, the location will be removed. Defaults to False.

  Returns:
      A dictionary containing a success or error message.
  """
  if compare_campaign_data(get_sa360_campaign_details_sheet(campaign_id, sheet_id, sheet_name), get_sa360_campaign_details(campaign_id, customer_id)):
    if remove:
      details = get_sa360_campaign_details(campaign_id, customer_id)
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
  else:
    _update_campaign_property(campaign_id, "Row Type", "", sheet_id, sheet_name)
    raise RuntimeError("Data mismatch between Google Sheet and SA360 API.")


def update_sa360_campaign_budget(
    campaign_id: str, budget: float, sheet_id: str, sheet_name: str, customer_id: str
) -> Dict[str, Any]:
  """Updates the budget for an SA360 campaign in the Google Sheet."""
  if compare_campaign_data(get_sa360_campaign_details_sheet(campaign_id, sheet_id, sheet_name), get_sa360_campaign_details(campaign_id, customer_id)):
    return _update_campaign_property(campaign_id, "Budget", budget, sheet_id, sheet_name)
  else:
    _update_campaign_property(campaign_id, "Row Type", "", sheet_id, sheet_name)
    raise RuntimeError("Data mismatch between Google Sheet and SA360 API.")


class SA360Toolset(BaseToolset):
  """Toolset for managing SA360 campaigns via a Google Sheet."""

  def __init__(self):
    super().__init__()

    self._get_campaign_details_sa360_sheet_tool = FunctionTool(
        func=get_sa360_campaign_details_sheet,
    )
    self._get_campaign_details_sa360_tool = FunctionTool(
        func=get_sa360_campaign_details,
    )
    self._update_campaign_status_tool = FunctionTool(func=update_sa360_campaign_status)
    self._update_campaign_geolocation_tool = FunctionTool(
        func=update_sa360_campaign_geolocation
    )
    self._update_campaign_budget_tool = FunctionTool(
        func=update_sa360_campaign_budget
    )

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [
        self._get_campaign_details_sa360_sheet_tool,
        self._get_campaign_details_sa360_tool,
        self._update_campaign_status_tool,
        self._update_campaign_geolocation_tool,
        self._update_campaign_budget_tool,
    ]
