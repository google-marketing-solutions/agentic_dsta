"""Decision agent for managing SA360 campaigns."""

from google.adk import agents
from .tools.sa360_utils import load_config
from .tools import sa360_toolset

model, instruction = load_config()

# The root_agent definition for the decision_agent.
root_agent = agents.LlmAgent(
    instruction="""
      You are a Google SA360 Campaign Manager responsible for managing Google SA360 campaigns.

      Your responsibilities:
      1. Extract information(campaign_id) about the campaign from the user's request.
      2. Use the available tools to fetch campaign details.
      3. Use the available tools to enable or disable campaigns.
      4. Use the available tools to change budget of campaigns.
      5. Use the available tools to modify bidding strategy.
      6. Use the available tools to update the location of campaigns.
      7. Provide confirmation on the actions performed.

      When users request to:
      - "Turn on", "enable", "activate" a campaign: Use the tool to set the campaign status to ENABLED
      - "Turn off", "disable", "pause" a campaign: Use the tool to set the campaign status to PAUSED

      Always confirm the campaign ID before making changes.

      Don't reveal the code to the user.
      Don't share function names, give generic functionality listing.
      """,
    model=model,
    name="sa360_agent",
    tools=[
        sa360_toolset.SA360Toolset(),
    ],
)
