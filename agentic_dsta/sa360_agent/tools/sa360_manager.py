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
"""Manages SA360 campaigns using the google-ads-python library."""

import os
from typing import Any, Dict, List, Optional
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
import google.ads.googleads.client
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2
import logging
from agentic_dsta.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


def list_accessible_customers():
  """Lists customer IDs accessible to the authenticated user."""
  try:
    # Load credentials from environment variables, but omit login_customer_id
    config_data = {
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
    customer_service = client.get_service("CustomerService")
    response = customer_service.list_accessible_customers()
    return {"accessible_customers": response.resource_names}
  except GoogleAdsException as ex:
    logger.error("Failed to list accessible customers: %s", ex, exc_info=True)
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          str(error.error_code),
          error.message,
          extra={
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to list accessible customers: {ex.failure}") from ex


def get_google_ads_client(customer_id: str):
  """Initializes and returns a GoogleAdsClient for SA360.

  Assumes SA360 credentials are provided via environment variables similar to
  Google Ads credentials.
  The Google Ads API is used for both Google Ads and Search Ads 360 (SA360).
  This client connects to SA360 by authenticating with credentials
  (developer token, OAuth2 tokens) that have access to the SA360 account
  specified in 'customer_id', and by setting 'login_customer_id' to
  this SA360 customer ID.
  """
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
    logger.error(
        "Failed to create GoogleAdsClient: %s",
        ex,
        exc_info=True,
        extra={'customer_id': customer_id}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          str(error.error_code),
          error.message,
          extra={
              'customer_id': customer_id,
              'error_code': str(error.error_code),
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to create GoogleAdsClient: {ex.failure}") from ex


def update_campaign_status(customer_id: str, campaign_id: str, status: str):
  """Enables or disables an SA360 campaign.

  Args:
    customer_id: The SA360 customer ID (without hyphens).
    campaign_id: The ID of the campaign to update.
    status: The desired status ("ENABLED" or "PAUSED").

  Returns:
    A dictionary with the result of the operation.
  """
  client = get_google_ads_client(customer_id)
  if not client:
    raise RuntimeError("Failed to get Google Ads client for SA360.")

  campaign_service = client.get_service("CampaignService")
  campaign_op = client.get_type("CampaignOperation")
  campaign = campaign_op.update
  campaign.resource_name = campaign_service.campaign_path(
      customer_id, campaign_id
  )

  CampaignStatusEnum = client.get_type("CampaignStatusEnum")
  if status == "ENABLED":
    campaign.status = CampaignStatusEnum.CampaignStatus.ENABLED
  elif status == "PAUSED":
    campaign.status = CampaignStatusEnum.CampaignStatus.PAUSED
  else:
    raise ValueError(f"Invalid status provided: {status}. Use 'ENABLED' or 'PAUSED'.")

  client.copy_from(
      campaign_op.update_mask, field_mask_pb2.FieldMask(paths=["status"])
  )
  campaign_op.update_mask.paths.append("status")

  request = client.get_type("MutateCampaignsRequest")
  request.customer_id = customer_id
  request.operations.append(campaign_op)

  try:
    response = campaign_service.mutate_campaigns(request=request)
    campaign_response = response.results[0]
    logger.info(
        "Updated campaign '%s'",
        campaign_response.resource_name,
        extra={
            'customer_id': customer_id,
            'campaign_id': campaign_id,
            'resource_name': campaign_response.resource_name
        }
    )
    return {"success": True, "resource_name": campaign_response.resource_name}
  except GoogleAdsException as ex:
    logger.error(
        "Failed to update campaign: %s",
        ex,
        exc_info=True,
        extra={'customer_id': customer_id, 'campaign_id': campaign_id, 'status': status}
    )
    for error in ex.failure.errors:
      logger.error(
          "Google Ads API Error: %s - %s",
          error.error_code.name,
          error.message,
          extra={
              'customer_id': customer_id,
              'campaign_id': campaign_id,
              'error_code': error.error_code.name,
              'error_message': error.message
          }
      )
    raise RuntimeError(f"Failed to update campaign: {ex.failure}") from ex


class SA360ManagerToolset(BaseToolset):
  """Toolset for managing SA360 campaigns."""

  def __init__(self):
    super().__init__()
    self._update_campaign_status_tool = FunctionTool(
        func=update_campaign_status,
    )
    self._list_accessible_customers_tool = FunctionTool(
        func=list_accessible_customers,
    )

  async def get_tools(
      self, readonly_context: Optional[Any] = None
  ) -> List[FunctionTool]:
    """Returns a list of tools in this toolset."""
    return [self._update_campaign_status_tool, self._list_accessible_customers_tool]
