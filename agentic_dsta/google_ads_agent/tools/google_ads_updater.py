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
"""Tools for updating Google Ads campaigns."""

import os
from typing import Any, Dict, List, Optional

from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
import google.ads.googleads.client
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2


def get_google_ads_client(customer_id: str):
  """Initializes and returns a GoogleAdsClient."""
  try:
    # Load credentials from environment variables.
    config_data = {
        "login_customer_id": customer_id,
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "use_proto_plus": True,
    }
    client = google.ads.googleads.client.GoogleAdsClient.load_from_dict(
        config_data
    )
    return client
  except GoogleAdsException as ex:
    print(f"Failed to create GoogleAdsClient: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return None

def update_campaign_status(customer_id: str, campaign_id: str, status: str):
  """Enables or disables a Google Ads campaign.

  Args:
    customer_id: The Google Ads customer ID (without hyphens).
    campaign_id: The ID of the campaign to update.
    status: The desired status ("ENABLED" or "PAUSED").

  Returns:
    A dictionary with the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    return {"error": "Failed to get Google Ads client."}

  campaign_service = client.get_service("CampaignService")
  campaign_op = client.get_type("CampaignOperation")
  campaign = campaign_op.update
  campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)

  CampaignStatusEnum = client.get_type("CampaignStatusEnum")
  if status == "ENABLED":
    campaign.status = CampaignStatusEnum.CampaignStatus.ENABLED
  elif status == "PAUSED":
    campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED
  else:
    return {"error": f"Invalid status provided: {status}. Use 'ENABLED' or 'PAUSED'."}

  client.copy_from(campaign_op.update_mask, field_mask_pb2.FieldMask(paths=["status"]))
  campaign_op.update_mask.paths.append("status")

  request = client.get_type("MutateCampaignsRequest")
  request.customer_id = customer_id
  request.operations.append(campaign_op)

  try:
    response = campaign_service.mutate_campaigns(request=request)
    campaign_response = response.results[0]
    print(f"Updated campaign '{campaign_response.resource_name}'")
    return {"success": True, "resource_name": campaign_response.resource_name}
  except GoogleAdsException as ex:
    print(f"Failed to update campaign: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return {"error": f"Failed to update campaign: {ex.failure}"}


def update_campaign_budget(
    customer_id: str, campaign_id: str, new_budget_micros: int
) -> Dict[str, Any]:
  """Updates the budget for a specific Google Ads campaign.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      campaign_id: The ID of the campaign to update the budget for.
      new_budget_micros: The new budget amount in micros.

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    return {"error": "Failed to get Google Ads client."}

  # First, get the campaign's budget resource name.
  ga_service = client.get_service("GoogleAdsService")
  query = f"""
        SELECT campaign.campaign_budget
        FROM campaign
        WHERE campaign.id = '{campaign_id}'"""
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    campaign_budget_resource_name = None
    for batch in stream:
      for row in batch.results:
        campaign_budget_resource_name = row.campaign.campaign_budget
        break
      if campaign_budget_resource_name:
        break

    if not campaign_budget_resource_name:
      return {
          "error":
              f"Campaign with ID '{campaign_id}' not found or has no budget."
      }

  except GoogleAdsException as ex:
    return {"error": f"Failed to fetch campaign budget: {ex.failure}"}

  campaign_budget_service = client.get_service("CampaignBudgetService")
  campaign_budget_op = client.get_type("CampaignBudgetOperation")
  budget = campaign_budget_op.update
  budget.resource_name = campaign_budget_resource_name
  budget.amount_micros = new_budget_micros

  field_mask = field_mask_pb2.FieldMask(paths=["amount_micros"])
  client.copy_from(campaign_budget_op.update_mask, field_mask)

  try:
    response = campaign_budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[campaign_budget_op]
    )
    budget_response = response.results[0]
    print(f"Updated budget '{budget_response.resource_name}'")
    return {"success": True, "resource_name": budget_response.resource_name}
  except GoogleAdsException as ex:
    print(f"Failed to update campaign budget: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return {"error": f"Failed to update campaign budget: {ex.failure}"}


def update_campaign_geo_targets(
    customer_id: str,
    campaign_id: str,
    location_ids: List[str],
    negative: bool = False,
) -> Dict[str, Any]:
  """Updates the geo targeting for a specific Google Ads campaign.

  This function replaces all existing geo targets with the new ones.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      campaign_id: The ID of the campaign to update.
      location_ids: A list of location IDs (e.g., "2840" for USA) to target.
      negative: Whether to negatively target these locations.

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    return {"error": "Failed to get Google Ads client."}

  # First, get existing geo target criteria to remove them.
  ga_service = client.get_service("GoogleAdsService")
  query = f"""
        SELECT campaign_criterion.resource_name
        FROM campaign_criterion
        WHERE campaign.id = '{campaign_id}'
        AND campaign_criterion.type = 'LOCATION'"""

  remove_operations = []
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        op = client.get_type("CampaignCriterionOperation")
        op.remove = row.campaign_criterion.resource_name
        remove_operations.append(op)
  except GoogleAdsException as ex:
    return {"error": f"Failed to fetch existing geo targets: {ex.failure}"}

  # Now, create new geo target criteria to add.
  campaign_criterion_service = client.get_service("CampaignCriterionService")
  campaign_service = client.get_service("CampaignService")
  geo_target_constant_service = client.get_service("GeoTargetConstantService")

  add_operations = []
  for location_id in location_ids:
    if not location_id.isdigit():
      return {
          "error": (
              f"Invalid location_id: '{location_id}'. Location ID must be a"
              " numeric string (e.g., '2840' for USA)."
          )
      }
    op = client.get_type("CampaignCriterionOperation")
    criterion = op.create
    criterion.campaign = campaign_service.campaign_path(
        customer_id, campaign_id
    )
    criterion.location.geo_target_constant = (
        geo_target_constant_service.geo_target_constant_path(location_id)
    )
    criterion.negative = negative
    add_operations.append(op)

  operations = remove_operations + add_operations

  if not operations:
    return {"success": True, "message": "No changes to apply."}

  try:
    response = campaign_criterion_service.mutate_campaign_criteria(
        customer_id=customer_id, operations=operations
    )
    # Process response
    resource_names = [r.resource_name for r in response.results]
    return {"success": True, "resource_names": resource_names}
  except GoogleAdsException as ex:
    print(f"Failed to update campaign geo targets: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return {"error": f"Failed to update campaign geo targets: {ex.failure}"}


def update_ad_group_geo_targets(
    customer_id: str,
    ad_group_id: str,
    location_ids: List[str],
    negative: bool = False,
) -> Dict[str, Any]:
  """Updates the geo targeting for a specific Google Ads ad group.

  This function replaces all existing geo targets with the new ones.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      ad_group_id: The ID of the ad group to update.
      location_ids: A list of location IDs (e.g., "2840" for USA) to target.
      negative: Whether to negatively target these locations.

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    return {"error": "Failed to get Google Ads client."}

  # First, get existing geo target criteria to remove them.
  ga_service = client.get_service("GoogleAdsService")
  query = f"""
        SELECT ad_group_criterion.resource_name
        FROM ad_group_criterion
        WHERE ad_group.id = '{ad_group_id}'
        AND ad_group_criterion.type = 'LOCATION'"""

  remove_operations = []
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        op = client.get_type("AdGroupCriterionOperation")
        op.remove = row.ad_group_criterion.resource_name
        remove_operations.append(op)
  except GoogleAdsException as ex:
    return {"error": f"Failed to fetch existing geo targets: {ex.failure}"}

  # Now, create new geo target criteria to add.
  ad_group_criterion_service = client.get_service("AdGroupCriterionService")
  ad_group_service = client.get_service("AdGroupService")
  geo_target_constant_service = client.get_service("GeoTargetConstantService")

  add_operations = []
  for location_id in location_ids:
    if not location_id.isdigit():
      return {
          "error": (
              f"Invalid location_id: '{location_id}'. Location ID must be a"
              " numeric string (e.g., '2840' for USA)."
          )
      }
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.create
    criterion.ad_group = ad_group_service.ad_group_path(
        customer_id, ad_group_id
    )
    criterion.location.geo_target_constant = (
        geo_target_constant_service.geo_target_constant_path(location_id)
    )
    criterion.negative = negative
    add_operations.append(op)

  operations = remove_operations + add_operations

  if not operations:
    return {"success": True, "message": "No changes to apply."}

  try:
    response = ad_group_criterion_service.mutate_ad_group_criteria(
        customer_id=customer_id, operations=operations
    )
    # Process response
    resource_names = [r.resource_name for r in response.results]
    return {"success": True, "resource_names": resource_names}
  except GoogleAdsException as ex:
    print(f"Failed to update ad group geo targets: {ex}")
    for error in ex.failure.errors:
      print(f"Error: {error.error_code} - {error.message}")
    return {"error": f"Failed to update ad group geo targets: {ex.failure}"}


class GoogleAdsUpdaterToolset(BaseToolset):
  """Toolset for managing Google Ads campaigns."""

  def __init__(self):
    super().__init__()
    self._update_campaign_status_tool = FunctionTool(
        func=update_campaign_status,
    )
    self._update_campaign_budget_tool = FunctionTool(
        func=update_campaign_budget,
    )
    self._update_campaign_geo_targets_tool = FunctionTool(
        func=update_campaign_geo_targets,
    )
    self._update_ad_group_geo_targets_tool = FunctionTool(
        func=update_ad_group_geo_targets
    )

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [
        self._update_campaign_status_tool,
        self._update_campaign_budget_tool,
        self._update_campaign_geo_targets_tool,
        self._update_ad_group_geo_targets_tool,
    ]
