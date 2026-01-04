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
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

from google_ads_agent.tools.google_ads_getter import GoogleAdsGetterToolset
from google_ads_agent.tools.google_ads_updater import GoogleAdsUpdaterToolset
from api_hub_agent.tools.apihub_toolset import DynamicMultiAPIToolset
from firestore_agent.tools.firestore_toolset import FirestoreToolset
from sa360_agent.tools.sa360_toolset import SA360Toolset
from google.adk import agents


import os

# The root_agent definition for the marketing_agent.
model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

# Read the prompt from the external file.
with open(os.path.join(os.path.dirname(__file__), "prompt.txt"), "r", encoding='utf-8') as f:
    prompt = f.read()

root_agent = agents.LlmAgent(
    instruction=prompt,
    model=model,
    name="marketing_campaign_manager",
    tools=[
        GoogleAdsGetterToolset(),
        GoogleAdsUpdaterToolset(),
        DynamicMultiAPIToolset(),
        FirestoreToolset(),
        SA360Toolset(),
    ],
)
