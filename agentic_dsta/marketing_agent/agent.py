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
"""Decision agent for managing marketing campaigns."""

from google_ads_agent.tools.google_ads_getter import GoogleAdsGetterToolset
from google_ads_agent.tools.google_ads_updater import GoogleAdsUpdaterToolset
from api_hub_agent.tools.apihub_toolset import DynamicMultiAPIToolset
from firestore_agent.tools.firestore_toolset import FirestoreToolset
from google.adk import agents


# The root_agent definition for the marketing_agent.
model = "gemini-2.0-flash"
root_agent = agents.LlmAgent(
    instruction="""
      You are a Marketing Campaign Manager responsible for deciding marketing campaign actions based on data from ApiHub, Firestore.

      Your responsibilities:
      1. Extract customer_id and campaign_id from the user's request
      2. Use the api_hub_manager tool to gather relevant marketing data
      3. Use the firestore_toolset to read company preferences
      4. Use the google_ads_manager tool to enable or disable campaigns
      5. Provide confirmation of the campaign status change

      When users request to:
        - "Turn on", "enable", "activate" a campaign: Use the tool to set the campaign status to ENABLED

      Always confirm the customer ID and campaign ID before making changes.
      """,
    model=model,
    name="marketing_campaign_manager",
    tools=[
        GoogleAdsGetterToolset(),
        GoogleAdsUpdaterToolset(),
        DynamicMultiAPIToolset(),
        FirestoreToolset(),
    ],
)
