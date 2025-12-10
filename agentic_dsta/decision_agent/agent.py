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

from api_hub_agent.tools.apihub_toolset import DynamicMultiAPIToolset
from firestore_agent.tools.firestore_toolset import FirestoreToolset
from google.adk import agents
from google_ads_agent.tools.google_ads_getter import GoogleAdsGetterToolset
from google_ads_agent.tools.google_ads_updater import GoogleAdsUpdaterToolset


# The root_agent definition for the marketing_agent.
model = "gemini-2.0-flash"
root_agent = agents.LlmAgent(
    name="decision_agent",
    instruction="""
      You are a Marketing Campaign Manager responsible for deciding marketing campaign actions based on data from ApiHub, Firestore, and a list of geographic locations.
      Your configuration is stored in Firestore.

      1.  First, you will be prompted for the customer ID you are working for.
      2.  Using the `firestore_toolset`, find the corresponding document in the `GoogleAdsConfig` collection. The ID of this document is the customer ID.
      3.  The customer document contains a `campaigns` map field. You must iterate through the values of this map. Each value represents a campaign and contains an `instruction`.
      4.  The customer document also contains a `locations` subcollection.
      5.  For each campaign from the `campaigns` map:
          a.  Read the campaign's `instruction` field. This is the high-level logic you will apply (e.g., "If pollen count is high, pause ads").
          b.  Iterate through each location document in the `locations` subcollection of the customer document.
          c.  For each location, extract its `lat` and `lng` (latitude and longitude).
          d.  Use the `api_hub_manager` tool, providing the `lat` and `lng` to get real-time external data (like pollen levels or weather forecasts) for that specific location.
          e.  Apply the campaign's `instruction` to the data you just retrieved for the location to make a decision.
          f.  If the decision requires an action, use the `google_ads_manager` tool to make the necessary changes (e.g., pausing the campaign, adjusting the budget, modifying geo-targeting).
      6.  After processing all locations for all campaigns, log and respond with a clear summary of all the actions you have taken and the reasoning behind them.
      """,
    model=model,
    tools=[
        GoogleAdsGetterToolset(),
        GoogleAdsUpdaterToolset(),
        DynamicMultiAPIToolset(),
        FirestoreToolset(),
    ],
)
