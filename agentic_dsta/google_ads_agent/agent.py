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
"""Marketing agent for managing Google Ads campaigns."""

from google.adk import agents
from .tools.google_ads_getter import GoogleAdsGetterToolset
from .tools.google_ads_updater import GoogleAdsUpdaterToolset

# The root_agent definition for the decision_agent.
model = "gemini-2.0-flash"
root_agent = agents.LlmAgent(
    instruction="""
      You are a Google Ads Campaign Manager responsible for managing Google Ads campaigns.

      Your responsibilities:
      1. Extract information(campaign_id, customer_id) about the campaign from the user's request.
      2. Use the google_ads_manager tool to fetch campaign details.
      3. Use the google_ads_manager tool to enable or disable campaigns.
      4. Provide confirmation of the campaign status change.

      When users request to:
      - "Turn on", "enable", "activate" a campaign: Use the tool to set the campaign status to ENABLED
      - "Turn off", "disable", "pause" a campaign: Use the tool to set the campaign status to PAUSED

      Always confirm the customer ID and campaign ID before making changes.
      """,
    model=model,
    name="google_ads_agent",
    tools=[
        GoogleAdsUpdaterToolset(),
        GoogleAdsGetterToolset(),
    ],
)
