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
from google.ads.googleads.v22.enums.types.target_impression_share_location import (
    TargetImpressionShareLocationEnum
)
from .google_ads_client import get_google_ads_client
from .google_ads_getter import get_campaign_details
from .bidding_strategy_utils import validate_strategy_change
import logging


logger = logging.getLogger(__name__)

def _apply_maximize_conversions(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies MAXIMIZE_CONVERSIONS strategy details."""
  strategy_obj.maximize_conversions  # Activate oneof
  if strategy_details and "target_cpa_micros" in strategy_details:
    strategy_obj.maximize_conversions.target_cpa_micros = strategy_details["target_cpa_micros"]
  field_mask_paths.append("maximize_conversions.target_cpa_micros")
  return True


def _apply_maximize_conversion_value(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies MAXIMIZE_CONVERSION_VALUE strategy details."""
  strategy_obj.maximize_conversion_value  # Activate oneof
  if strategy_details and "target_roas" in strategy_details:
    strategy_obj.maximize_conversion_value.target_roas = strategy_details["target_roas"]
  field_mask_paths.append("maximize_conversion_value.target_roas")
  return True


def _apply_target_spend(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies TARGET_SPEND strategy details."""
  strategy_obj.target_spend  # Activate oneof
  if strategy_details and "cpc_bid_ceiling_micros" in strategy_details:
    strategy_obj.target_spend.cpc_bid_ceiling_micros = strategy_details["cpc_bid_ceiling_micros"]
  field_mask_paths.append("target_spend.cpc_bid_ceiling_micros")
  return True


def _apply_manual_cpc(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies MANUAL_CPC strategy details."""
  strategy_obj.manual_cpc  # Activate oneof
  if strategy_details and "enhanced_cpc_enabled" in strategy_details:
      strategy_obj.manual_cpc.enhanced_cpc_enabled = strategy_details["enhanced_cpc_enabled"]
  field_mask_paths.append("manual_cpc.enhanced_cpc_enabled")
  return True


def _apply_target_impression_share(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies TARGET_IMPRESSION_SHARE strategy details."""
  if (not strategy_details or
          "location" not in strategy_details or
          "location_fraction_micros" not in strategy_details):
    logger.error("Missing details for TARGET_IMPRESSION_SHARE")
    return False
  strategy_obj.target_impression_share  # Activate oneof
  location_str = strategy_details["location"].upper()
  try:
    location_enum = TargetImpressionShareLocationEnum.TargetImpressionShareLocation[location_str]
    strategy_obj.target_impression_share.location = location_enum
  except KeyError:
    logger.error("Invalid location for TARGET_IMPRESSION_SHARE: %s", location_str)
    return False
  strategy_obj.target_impression_share.location_fraction_micros = (
      strategy_details["location_fraction_micros"]
  )
  field_mask_paths.extend([
      "target_impression_share.location",
      "target_impression_share.location_fraction_micros"
  ])
  if "cpc_bid_ceiling_micros" in strategy_details:
    strategy_obj.target_impression_share.cpc_bid_ceiling_micros = (
        strategy_details["cpc_bid_ceiling_micros"]
    )
    field_mask_paths.append("target_impression_share.cpc_bid_ceiling_micros")
  return True


def _apply_percent_cpc(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies PERCENT_CPC strategy details."""
  strategy_obj.percent_cpc
  if strategy_details and "cpc_bid_ceiling_micros" in strategy_details:
      strategy_obj.percent_cpc.cpc_bid_ceiling_micros = (
          strategy_details["cpc_bid_ceiling_micros"]
      )
  if strategy_details and "enhanced_cpc_enabled" in strategy_details:
      strategy_obj.percent_cpc.enhanced_cpc_enabled = strategy_details["enhanced_cpc_enabled"]
  field_mask_paths.append("percent_cpc.cpc_bid_ceiling_micros")
  return True


def _apply_commission(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies COMMISSION strategy details."""
  strategy_obj.commission
  if strategy_details and "commission_rate_micros" in strategy_details:
      strategy_obj.commission.commission_rate_micros = (
          strategy_details["commission_rate_micros"]
      )
  field_mask_paths.append("commission.commission_rate_micros")
  return True


def _apply_target_cpa(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies TARGET_CPA strategy details (Portfolio)."""
  strategy_obj.target_cpa
  if strategy_details and "target_cpa_micros" in strategy_details:
      strategy_obj.target_cpa.target_cpa_micros = strategy_details["target_cpa_micros"]
      field_mask_paths.append("target_cpa.target_cpa_micros")
      return True
  logger.error("target_cpa_micros required for TARGET_CPA portfolio")
  return False


def _apply_target_roas(
    strategy_obj: Any,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Applies TARGET_ROAS strategy details (Portfolio)."""
  strategy_obj.target_roas
  if strategy_details and "target_roas" in strategy_details:
      strategy_obj.target_roas.target_roas = strategy_details["target_roas"]
      field_mask_paths.append("target_roas.target_roas")
      return True
  logger.error("target_roas required for TARGET_ROAS portfolio")
  return False


def _apply_bidding_strategy_details(
    strategy_obj: Any,
    strategy_type: str,
    field_mask_paths: List[str],
    strategy_details: Optional[Dict[str, Any]] = None
) -> bool:
  """Helper function to apply strategy details to a campaign or bidding_strategy object."""
  if strategy_type == "MAXIMIZE_CONVERSIONS":
    return _apply_maximize_conversions(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "MAXIMIZE_CONVERSION_VALUE":
    return _apply_maximize_conversion_value(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "TARGET_SPEND":
    return _apply_target_spend(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "MANUAL_CPC":
    return _apply_manual_cpc(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "TARGET_IMPRESSION_SHARE":
    return _apply_target_impression_share(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "MANUAL_CPM":
    strategy_obj.manual_cpm
    return True
  elif strategy_type == "MANUAL_CPV":
    strategy_obj.manual_cpv
    return True
  elif strategy_type == "PERCENT_CPC":
    return _apply_percent_cpc(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "COMMISSION":
    return _apply_commission(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "TARGET_CPA":
    return _apply_target_cpa(strategy_obj, field_mask_paths, strategy_details)
  elif strategy_type == "TARGET_ROAS":
    return _apply_target_roas(strategy_obj, field_mask_paths, strategy_details)
  else:
    logger.error("Unsupported strategy type: %s", strategy_type)
    return False


def update_bidding_strategy(
    customer_id: str,
    campaign_id: str,
    strategy_type: str,
    strategy_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
  """Updates the bidding strategy for a specific Google Ads campaign.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      campaign_id: The ID of the campaign to update.
      strategy_type: The target bidding strategy type (e.g., 'MAXIMIZE_CONVERSIONS').
      strategy_details: Optional dictionary containing specific details for the strategy
                        (e.g., {'target_cpa_micros': 1000000}).

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  # 1. Get current campaign details
  campaign_data = get_campaign_details(customer_id, campaign_id)
  if campaign_data.get("error"):
    return campaign_data

  advertising_channel_type = campaign_data.get("advertisingChannelType")
  if not advertising_channel_type:
    raise ValueError("Could not determine advertising_channel_type.")

  # 2. Validate the strategy change
  logger.debug(
      "Raw advertising_channel_type: '%s'",
      advertising_channel_type,
      extra={'customer_id': customer_id, 'campaign_id': campaign_id}
  )
  logger.debug(
      "Raw strategy_type: '%s'",
      strategy_type,
      extra={'customer_id': customer_id, 'campaign_id': campaign_id}
  )
  logger.debug(
      "Validating strategy change: Channel Type='%s', Target Strategy='%s'",
      advertising_channel_type,
      strategy_type,
      extra={'customer_id': customer_id, 'campaign_id': campaign_id}
  )
  is_valid = validate_strategy_change(advertising_channel_type, strategy_type)
  logger.debug(
      "Validation Result for ('%s', '%s'): %s",
      advertising_channel_type.upper(),
      strategy_type.upper(),
      is_valid,
      extra={
          'customer_id': customer_id,
          'campaign_id': campaign_id
      }
  )
  if not is_valid:
    raise ValueError(
        f"Bidding strategy '{strategy_type}' is not allowed for "
        f"channel type '{advertising_channel_type}'."
    )

  # 3. Construct the mutation
  campaign_service = client.get_service("CampaignService")
  campaign_op = client.get_type("CampaignOperation")
  campaign = campaign_op.update
  campaign.resource_name = campaign_service.campaign_path(customer_id, campaign_id)

  field_mask_paths = []
  if strategy_type.startswith("customers/"):
      campaign.bidding_strategy = strategy_type
      field_mask_paths.append("bidding_strategy")
  elif not _apply_bidding_strategy_details(
      campaign,
      strategy_type,
      field_mask_paths,
      strategy_details
  ):
    raise ValueError(f"Failed to apply bidding strategy details for type: {strategy_type}")
  else: # Standard strategy applied, ensure portfolio link is cleared
      field_mask_paths.append("bidding_strategy")


  logger.debug(
      "Field Mask Paths: %s",
      field_mask_paths,
      extra={'customer_id': customer_id, 'campaign_id': campaign_id}
  )
  client.copy_from(campaign_op.update_mask, field_mask_pb2.FieldMask(paths=field_mask_paths))

  # 4. Execute the mutation
  try:
    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[campaign_op]
    )
    campaign_response = response.results[0]
    return {"success": True, "resource_name": campaign_response.resource_name}
  except GoogleAdsException as ex:
    error_details = [str(error) for error in ex.failure.errors]
    logger.error(
        "Failed to update bidding strategy: %s",
        error_details,
        exc_info=True,
        extra={
            'customer_id': customer_id,
            'campaign_id': campaign_id,
            'strategy_type': strategy_type
        }
    )
    raise RuntimeError(f"Failed to update bidding strategy: {ex.failure}") from ex
    
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
    raise RuntimeError("Failed to get Google Ads client.")

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
    raise ValueError(f"Invalid status provided: {status}. Use 'ENABLED' or 'PAUSED'.")

  client.copy_from(campaign_op.update_mask, field_mask_pb2.FieldMask(paths=["status"]))
  campaign_op.update_mask.paths.append("status")

  request = client.get_type("MutateCampaignsRequest")
  request.customer_id = customer_id
  request.operations.append(campaign_op)

  try:
    response = campaign_service.mutate_campaigns(request=request)
    campaign_response = response.results[0]
    logger.info(
        "Updated campaign status to %s",
        status,
        extra={
            'customer_id': customer_id,
            'campaign_id': campaign_id,
            'resource_name': campaign_response.resource_name
        }
    )
    return {"success": True, "resource_name": campaign_response.resource_name}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to update campaign status",
        exc_info=True,
        extra={'customer_id': customer_id, 'campaign_id': campaign_id, 'status': status}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'campaign_id': campaign_id,
              'error_code': error.error_code.name,
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update campaign: {ex.failure}") from ex


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
    raise RuntimeError("Failed to get Google Ads client.")

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
    raise RuntimeError(f"Failed to fetch campaign budget: {ex.failure}") from ex

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
    logger.info(
        "Updated campaign budget",
        extra={
            'customer_id': customer_id,
            'campaign_id': campaign_id,
            'resource_name': budget_response.resource_name,
            'new_budget_micros': new_budget_micros
        }
    )
    return {"success": True, "resource_name": budget_response.resource_name}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to update campaign budget",
        exc_info=True,
        extra={'customer_id': customer_id, 'campaign_id': campaign_id}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'campaign_id': campaign_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update campaign budget: {ex.failure}") from ex


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
    raise RuntimeError("Failed to get Google Ads client.")

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
    raise RuntimeError(f"Failed to fetch existing geo targets: {ex.failure}") from ex

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
    logger.error(
        "Failed to update campaign geo targets",
        exc_info=True,
        extra={'customer_id': customer_id, 'campaign_id': campaign_id}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'campaign_id': campaign_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update campaign geo targets: {ex.failure}") from ex


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
    raise RuntimeError("Failed to get Google Ads client.")

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
    raise RuntimeError(f"Failed to fetch existing geo targets: {ex.failure}") from ex

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
    logger.error(
        "Failed to update ad group geo targets",
        exc_info=True,
        extra={'customer_id': customer_id, 'ad_group_id': ad_group_id}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'ad_group_id': ad_group_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update ad group geo targets: {ex.failure}") from ex



def update_shared_budget(
    customer_id: str,
    budget_resource_name: str,
    new_amount_micros: int
) -> Dict[str, Any]:
  """Updates the amount for a shared budget.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      budget_resource_name: The resource name of the shared budget to update.
      new_amount_micros: The new budget amount in micros.

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  if not budget_resource_name.startswith(f"customers/{customer_id}/campaignBudgets/"):
    raise ValueError(f"Invalid budget_resource_name format for customer {customer_id}.")

  campaign_budget_service = client.get_service("CampaignBudgetService")
  campaign_budget_op = client.get_type("CampaignBudgetOperation")
  budget = campaign_budget_op.update
  budget.resource_name = budget_resource_name
  budget.amount_micros = new_amount_micros

  field_mask = field_mask_pb2.FieldMask(paths=["amount_micros"])
  client.copy_from(campaign_budget_op.update_mask, field_mask)

  try:
    response = campaign_budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[campaign_budget_op]
    )
    budget_response = response.results[0]
    logger.info(
        "Updated shared budget amount",
        extra={
            'customer_id': customer_id,
            'resource_name': budget_response.resource_name,
            'new_amount_micros': new_amount_micros
        }
    )
    return {"success": True, "resource_name": budget_response.resource_name}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to update shared budget",
        exc_info=True,
        extra={'customer_id': customer_id, 'budget_resource_name': budget_resource_name}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update shared budget: {ex.failure}") from ex



def update_portfolio_bidding_strategy(
    customer_id: str,
    bidding_strategy_resource_name: str,
    strategy_type: str,
    strategy_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
  """Updates the type and details of a portfolio bidding strategy.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      bidding_strategy_resource_name: The resource name of the portfolio bidding strategy to update.
      strategy_type: The new bidding strategy type (e.g., 'MAXIMIZE_CONVERSIONS').
      strategy_details: Optional dictionary containing specific details for the new strategy type.

  Returns:
      A dictionary containing the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  if not bidding_strategy_resource_name.startswith(f"customers/{customer_id}/biddingStrategies/"):
    raise ValueError(f"Invalid bidding_strategy_resource_name format for customer {customer_id}.")

  bidding_strategy_service = client.get_service("BiddingStrategyService")
  bs_op = client.get_type("BiddingStrategyOperation")
  bidding_strategy = bs_op.update
  bidding_strategy.resource_name = bidding_strategy_resource_name

  field_mask_paths = []
  if not _apply_bidding_strategy_details(
      bidding_strategy, strategy_type, field_mask_paths, strategy_details
  ):
    raise ValueError(f"Failed to apply bidding strategy details for type: {strategy_type}")  


  # Remove duplicates
  final_mask_paths = sorted(list(set(field_mask_paths)))

  client.copy_from(bs_op.update_mask, field_mask_pb2.FieldMask(paths=final_mask_paths))

  try:
    response = bidding_strategy_service.mutate_bidding_strategies(
        customer_id=customer_id, operations=[bs_op]
    )
    logger.info(
        "Updated portfolio bidding strategy %s to %s",
        bidding_strategy_resource_name,
        strategy_type,
        extra={'customer_id': customer_id, 'resource_name': response.results[0].resource_name}
    )
    return {"success": True, "resource_name": response.results[0].resource_name}
  except GoogleAdsException as ex:
    error_details = [str(error) for error in ex.failure.errors]
    logger.error(
        "Failed to update portfolio bidding strategy: %s",
        error_details,
        exc_info=True,
        extra={
            'customer_id': customer_id,
            'bidding_strategy_resource_name': bidding_strategy_resource_name
        }
    )
    raise RuntimeError(f"Failed to update portfolio bidding strategy: {ex.failure}") from ex


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
    self._update_bidding_strategy_tool = FunctionTool(
        func=update_bidding_strategy,
    )
    self._update_shared_budget_tool = FunctionTool(func=update_shared_budget)
    self._update_portfolio_bidding_strategy_tool = FunctionTool(
        func=update_portfolio_bidding_strategy
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
        self._update_bidding_strategy_tool,
        self._update_shared_budget_tool,
        self._update_portfolio_bidding_strategy_tool,
    ]
