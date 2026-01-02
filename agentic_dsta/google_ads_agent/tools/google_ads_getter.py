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
"""Tools for getting information from the Google Ads API."""

import os
from typing import Any, Dict, List, Optional

from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
import google.ads.googleads.client
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf.json_format import MessageToDict
from .google_ads_client import get_google_ads_client
import logging


logger = logging.getLogger(__name__)

def get_campaign_details(customer_id: str, campaign_id: str) -> Dict[str, Any]:
  """Fetches details for a specific Google Ads campaign.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      campaign_id: The ID of the campaign to fetch.

  Returns:
      A dictionary containing the campaign details.
  """

  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  ga_service = client.get_service("GoogleAdsService")

  query = f"""
        SELECT
          campaign_budget.id,
          campaign_budget.name,
          campaign_budget.amount_micros,
          campaign_budget.status,
          campaign_budget.delivery_method,
          campaign_budget.type,
          campaign.app_campaign_setting.bidding_strategy_goal_type,
          campaign.advertising_channel_type,
          campaign.asset_automation_settings,
          campaign.audience_setting.use_audience_grouped,
          campaign.base_campaign,
          campaign.bidding_strategy,
          campaign.bidding_strategy_system_status,
          campaign.bidding_strategy_type,
          campaign.campaign_budget,
          campaign.dynamic_search_ads_setting.domain_name,
          campaign.dynamic_search_ads_setting.language_code,
          campaign.dynamic_search_ads_setting.use_supplied_urls_only,
          campaign.end_date,
          campaign.geo_target_type_setting.negative_geo_target_type,
          campaign.geo_target_type_setting.positive_geo_target_type,
          campaign.id,
          campaign.labels,
          campaign.local_campaign_setting.location_source_type,
          campaign.maximize_conversion_value.target_roas,
          campaign.maximize_conversions.target_cpa_micros,
          campaign.name,
          campaign.optimization_goal_setting.optimization_goal_types,
          campaign.optimization_score,
          campaign.real_time_bidding_setting.opt_in,
          campaign.resource_name,
          campaign.serving_status,
          campaign.start_date,
          campaign.status,
          campaign.target_cpa.cpc_bid_ceiling_micros,
          campaign.target_cpa.cpc_bid_floor_micros,
          campaign.target_cpa.target_cpa_micros,
          campaign.target_impression_share.cpc_bid_ceiling_micros,
          campaign.target_impression_share.location,
          campaign.target_impression_share.location_fraction_micros,
          campaign.target_roas.cpc_bid_ceiling_micros,
          campaign.target_roas.cpc_bid_floor_micros,
          campaign.target_roas.target_roas,
          campaign.target_spend.cpc_bid_ceiling_micros,
          campaign.target_spend.target_spend_micros
        FROM campaign
        WHERE campaign.id = '{campaign_id}'"""

  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        campaign = row.campaign
        return MessageToDict(campaign._pb)
      raise ValueError(f"Campaign with ID '{campaign_id}' not found.")

  except GoogleAdsException as ex:
    logger.error(
        "Failed to fetch campaign details",
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

    raise RuntimeError(f"Failed to fetch campaign details: {ex.failure}") from ex


def search_geo_target_constants(
    customer_id: str, location_name: str
) -> Dict[str, Any]:
  """Searches for geo target constants by location name.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      location_name: The name of the location to search for (e.g., "USA",
        "New York City").

  Returns:
      A dictionary containing a list of matching geo target constants.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  gtc_service = client.get_service("GeoTargetConstantService")
  request = client.get_type("SuggestGeoTargetConstantsRequest")
  request.location_names.names.append(location_name)

  try:
    response = gtc_service.suggest_geo_target_constants(request=request)
    suggestions = []
    for suggestion in response.geo_target_constant_suggestions:
      suggestions.append(
          MessageToDict(suggestion.geo_target_constant._pb)
      )
    return {"suggestions": suggestions}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to search for geo target constants",
        exc_info=True,
        extra={'customer_id': customer_id, 'location_name': location_name}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code,
          error.message,
          extra={
              'customer_id': customer_id,
              'location_name': location_name,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to search for geo target constants: {ex.failure}") from ex


def get_geo_targets(customer_id: str, campaign_id: str) -> Dict[str, Any]:
  """Fetches geo targets for a campaign and its ad groups.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      campaign_id: The ID of the campaign to fetch geo targets for.

  Returns:
      A dictionary containing the geo targets for the campaign and its ad
      groups.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  ga_service = client.get_service("GoogleAdsService")

  # Get campaign-level geo targets
  campaign_query = f"""
        SELECT
          campaign_criterion.resource_name,
          campaign_criterion.negative,
          campaign_criterion.location.geo_target_constant
        FROM campaign_criterion
        WHERE campaign.id = '{campaign_id}'
        AND campaign_criterion.type = 'LOCATION'"""

  campaign_targets = []
  try:
    stream = ga_service.search_stream(
        customer_id=customer_id, query=campaign_query
    )
    for batch in stream:
      for row in batch.results:
        campaign_targets.append(MessageToDict(row.campaign_criterion._pb))
  except GoogleAdsException as ex:
    raise RuntimeError(f"Failed to fetch campaign geo targets: {ex.failure}") from ex

  # Get ad group-level geo targets
  ad_group_query = f"""
        SELECT
            ad_group.id,
            ad_group_criterion.resource_name,
            ad_group_criterion.negative,
            ad_group_criterion.location.geo_target_constant
        FROM ad_group_criterion
        WHERE campaign.id = '{campaign_id}'
        AND ad_group_criterion.type = 'LOCATION'
    """
  ad_group_targets = {}
  try:
    stream = ga_service.search_stream(
        customer_id=customer_id, query=ad_group_query
    )
    for batch in stream:
      for row in batch.results:
        ad_group_id = str(row.ad_group.id)
        if ad_group_id not in ad_group_targets:
          ad_group_targets[ad_group_id] = []
        ad_group_targets[ad_group_id].append(
            MessageToDict(row.ad_group_criterion._pb)
        )
  except GoogleAdsException as ex:
    raise RuntimeError(f"Failed to fetch ad group geo targets: {ex.failure}") from ex

  return {
      "campaign_targets": campaign_targets,
      "ad_group_targets": ad_group_targets,
  }


def list_shared_budgets(customer_id: str) -> Dict[str, Any]:
  """Fetches explicitly shared budgets for a customer.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).

  Returns:
      A dictionary containing a list of shared budgets or an error.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  ga_service = client.get_service("GoogleAdsService")
  query = """
        SELECT
          campaign_budget.id,
          campaign_budget.name,
          campaign_budget.resource_name,
          campaign_budget.amount_micros,
          campaign_budget.status,
          campaign_budget.delivery_method,
          campaign_budget.type
        FROM campaign_budget
        WHERE campaign_budget.explicitly_shared = TRUE
          AND campaign_budget.status = 'ENABLED'
    """

  budgets = []
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        budgets.append(MessageToDict(row.campaign_budget._pb))
    return {"shared_budgets": budgets}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to fetch shared budgets",
        exc_info=True,
        extra={'customer_id': customer_id}
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
    raise RuntimeError(f"Failed to fetch shared budgets: {ex.failure}") from ex



def get_campaigns_by_bidding_strategy(
    customer_id: str,
    bidding_strategy_resource_name: str
) -> Dict[str, Any]:
  """Fetches campaigns attached to a specific portfolio bidding strategy.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).
      bidding_strategy_resource_name: The resource name of the portfolio bidding strategy.

  Returns:
      A dictionary containing a list of campaigns or an error.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  ga_service = client.get_service("GoogleAdsService")
  query = f"""
        SELECT
          campaign.id,
          campaign.name,
          campaign.resource_name,
          campaign.status
        FROM campaign
        WHERE campaign.bidding_strategy = '{bidding_strategy_resource_name}'
    """

  campaigns = []
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        campaigns.append(MessageToDict(row.campaign._pb))
    return {"campaigns": campaigns}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to fetch campaigns by bidding strategy",
        exc_info=True,
        extra={
            'customer_id': customer_id,
            'bidding_strategy': bidding_strategy_resource_name
        }
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
    raise RuntimeError(f"Failed to fetch campaigns by bidding strategy: {ex.failure}") from ex



def list_portfolio_bidding_strategies(customer_id: str) -> Dict[str, Any]:
  """Fetches enabled portfolio bidding strategies for a customer.

  Args:
      customer_id: The Google Ads customer ID (without hyphens).

  Returns:
      A dictionary containing a list of bidding strategies or an error.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client.")

  ga_service = client.get_service("GoogleAdsService")
  query = """
        SELECT
          bidding_strategy.id,
          bidding_strategy.name,
          bidding_strategy.resource_name,
          bidding_strategy.type
        FROM bidding_strategy
        WHERE bidding_strategy.status = 'ENABLED'
    """

  strategies = []
  try:
    stream = ga_service.search_stream(customer_id=customer_id, query=query)
    for batch in stream:
      for row in batch.results:
        strategies.append(MessageToDict(row.bidding_strategy._pb))
    return {"bidding_strategies": strategies}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to fetch portfolio bidding strategies",
        exc_info=True,
        extra={'customer_id': customer_id}
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
    raise RuntimeError(f"Failed to fetch portfolio bidding strategies: {ex.failure}") from ex



class GoogleAdsGetterToolset(BaseToolset):
  """Toolset for getting information from Google Ads."""

  def __init__(self):
    super().__init__()
    self._get_campaign_details_tool = FunctionTool(
        func=get_campaign_details,
    )
    self._search_geo_target_constants_tool = FunctionTool(
        func=search_geo_target_constants,
    )
    self._get_geo_targets_tool = FunctionTool(func=get_geo_targets)
    self._list_portfolio_bidding_strategies_tool = FunctionTool(
        func=list_portfolio_bidding_strategies,
    )
    self._get_campaigns_by_bidding_strategy_tool = FunctionTool(
        func=get_campaigns_by_bidding_strategy,
    )
    self._list_shared_budgets_tool = FunctionTool(func=list_shared_budgets)

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [
        self._get_campaign_details_tool,
        self._search_geo_target_constants_tool,
        self._get_geo_targets_tool,
        self._list_portfolio_bidding_strategies_tool,
        self._get_campaigns_by_bidding_strategy_tool,
        self._list_shared_budgets_tool,
    ]
