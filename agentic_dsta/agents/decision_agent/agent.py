# Copyright 2026 Google LLC
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
"""This agent is responsible for managing marketing campaigns for customers stored in Firestore."""
import logging
import os
import uuid
from typing import List, Optional

from google.genai import Client
from google.genai import types
from google.adk.models.google_llm import Gemini
from google.adk import apps
from google.adk import runners

from agentic_dsta.tools.api_hub.apihub_toolset import DynamicMultiAPIToolset
from agentic_dsta.tools.firestore.firestore_toolset import FirestoreToolset
from google.adk import agents
from agentic_dsta.tools.google_ads.google_ads_getter import GoogleAdsGetterToolset
from agentic_dsta.tools.google_ads.google_ads_updater import GoogleAdsUpdaterToolset
from agentic_dsta.tools.sa360.sa360_toolset import SA360Toolset



logger = logging.getLogger(__name__)

# Default model, can be overridden
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")


def create_agent(instruction: str, model: str = DEFAULT_MODEL) -> agents.LlmAgent:
    """
    Creates a new instance of the decision agent with specific instructions.

    Args:
        instruction: The system instruction for this agent instance.
        model: The Gemini model to use.

    Returns:
        A configured LlmAgent instance.
    """
    tools = [
        GoogleAdsGetterToolset(),
        GoogleAdsUpdaterToolset(),
        DynamicMultiAPIToolset(),
        FirestoreToolset(),
        SA360Toolset(),
    ]

    client = Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )

    configured_model = Gemini(model=model)
    configured_model.api_client = client

    return agents.LlmAgent(
        name="decision_agent",
        instruction=instruction,
        model=configured_model,
        tools=tools,
    )


async def run_decision_agent(customer_id: str, usecase: Optional[str] = "GoogleAds") -> None:
    """
    Main entry point for the Decision Agent.
    Controller Logic:
    1. Fetches Customer Intent/Instructions.
    2. Fetches Google Ads Config for Google Ads Tools or SA360Config for SA360 Tools.
    3. Loops through campaigns, creating an isolated agent for each.

    Args:
        customer_id: The customer ID to process.
    """
    logger.info("Starting Decision Agent for Customer: %s", customer_id)

    # 1. Fetch Global Instructions
    firestore_toolset = FirestoreToolset()
    try:
        doc = firestore_toolset.get_document(collection="CustomerInstructions", document_id=customer_id)
        if not doc:
             logger.warning("No CustomerInstructions found for customer_id: %s", customer_id)
             global_instruction = ""
        else:
             global_instruction = doc.get("data", {}).get("instruction", "")
    except Exception as e:
         logger.error("Error fetching CustomerInstructions for %s: %s", customer_id, e)
         global_instruction = ""

    if not global_instruction:
        logger.warning("No global instructions found for customer %s. Aborting.", customer_id)
        return

    # 2. Fetch Campaign Config
    try:
        collection = usecase + "Config"
        doc = firestore_toolset.get_document(collection=collection, document_id=customer_id)
        if not doc:
            logger.warning("No %s found for customer_id: %s", collection, customer_id)
            ads_config = {}
        else:
            ads_config = doc.get("data", {})
    except Exception as e:
        logger.error("Error fetching %s for %s: %s", collection, customer_id, e)
        ads_config = {}
    campaigns = ads_config.get("campaigns", [])
    

    if not campaigns:
        logger.info("No campaigns found for customer %s.", customer_id)
        return

    logger.info("Found %s campaigns for customer %s.", len(campaigns), customer_id)

    # 3. Loop and Process
    for campaign in campaigns:
        campaign_id = campaign.get("campaignId")
        campaign_instruction = campaign.get("instruction", "No specific instruction.")

        if not campaign_id:
            logger.warning("Skipping campaign with missing campaignId.")
            continue

        logger.info("Processing Campaign: %s", campaign_id)

        # Construct the context-rich prompt
        combined_instruction = f"""
        You are a Marketing Campaign Manager Agent.

        **Customer Context:**
        Customer ID: {customer_id}
        Global Strategy: {global_instruction}

        **Current Focus:**
        Campaign ID: {campaign_id}
        Campaign Specific Rules: {campaign_instruction}

        **Task:**
        1. Analyze the current situation for Campaign {campaign_id}.
        2. Check if any external factors (Weather, POLLEN, AQI etc) are relevant based on the instructions.
           If so, use the API Hub tools to fetch that data.
        3. Check the campaign's current performance/status using GoogleAds tools for GoogleAds campaigns.
        4. Decide on an action (Pause, Enable, Change Bid, Change Location, or No Action).
        5. Execute the action if necessary.
        6. Provide a concise summary of your analysis and actions.
        """

        try:
            # Create a fresh agent for this campaign
            agent = create_agent(instruction=combined_instruction)

            # Wrap in App and Runner for execution
            app = apps.App(name="decision_app", root_agent=agent)
            runner = runners.InMemoryRunner(app=app)

            session_id = str(uuid.uuid4())
            await runner.session_service.create_session(
                session_id=session_id,
                user_id=customer_id,
                app_name="decision_app"
            )

            prompt_text = f"Proceed with the analysis and management of Campaign {campaign_id} based on your instructions."
            content = types.Content(parts=[types.Part(text=prompt_text)])

            logger.info("Executing agent via Runner for Campaign %s", campaign_id)
            async for chunk in runner.run_async(
                user_id=customer_id,
                session_id=session_id,
                new_message=content
            ):
                pass

            logger.info("Result for Campaign %s: Execution Completed", campaign_id)

        except Exception as e:
            logger.error("Failed to process campaign %s: %s", campaign_id, e)
            # Continue to next campaign even if this one fails
            continue

    logger.info("Completed run for Customer: %s", customer_id)

root_agent = create_agent(instruction="You are a decision agent helper.")
