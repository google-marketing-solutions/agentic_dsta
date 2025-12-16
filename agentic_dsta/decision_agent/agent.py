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

from .strategies import fetch_instructions_from_firestore


# The root_agent definition for the marketing_agent.
model = "gemini-2.0-flash"
tools = [
    GoogleAdsGetterToolset(),
    GoogleAdsUpdaterToolset(),
    DynamicMultiAPIToolset(),
    FirestoreToolset(),
]

root_agent = agents.LlmAgent(
    name="decision_agent",
    instruction="""
      You are a Marketing Campaign Manager.
      Your task is to follow the user's request and the customer-specific instructions that will be provided to you.
      Use the available tools to execute the instructions and then provide a summary of the actions you have taken.
      """,
    model=model,
    tools=tools,
    before_model_callback=fetch_instructions_from_firestore,
)
