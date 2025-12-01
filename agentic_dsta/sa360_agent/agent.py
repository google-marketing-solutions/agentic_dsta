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
"""Decision agent for managing SA360 campaigns."""

from pathlib import Path
from .tools.sa360_manager import SA360ManagerToolset
from google.adk import agents
import yaml

# Load agent configuration from YAML file
config_path = Path(__file__).parent / "config.yaml"
with open(config_path, "r") as f:
  config = yaml.safe_load(f)

model = config["model"]
instruction = config["instruction"]

# The root_agent definition for the decision_agent.
root_agent = agents.LlmAgent(
    instruction=instruction,
    model=model,
    name="sa360_agent",
    tools=[
        SA360ManagerToolset(),
    ],
)
