# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Marketing campaign strategies."""

import re
from typing import Optional

from firestore_agent.tools.firestore_toolset import FirestoreToolset
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types


def fetch_instructions_from_firestore(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
  """
  Inspects the user's request for a customer_id, fetches instructions from
  Firestore, and modifies the system instruction for the LLM call.
  """
  # Step 1: Extract the last user message from the request
  last_user_message = ""
  if llm_request.contents and llm_request.contents[-1].role == "user":
    if llm_request.contents[-1].parts:
      last_user_message = llm_request.contents[-1].parts[0].text

  if not last_user_message:
    # If there's no user message, do nothing.
    return None

  # Step 2: Search for customer_id in the user message with a flexible regex
  customer_id_match = re.search(
      r"customerid\s*[:=]?\s*(\d+)", last_user_message, re.IGNORECASE
  )
  if not customer_id_match:
    # If no customer_id is found, proceed without modification.
    return None
  customer_id = customer_id_match.group(1)

  # Step 3: Fetch instructions from Firestore using the agent's initialized tool
  firestore_toolset = FirestoreToolset()
  if not firestore_toolset:
    error_message = "Error: FirestoreToolset not available in the agent."
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=error_message)])
    )

  instructions_doc = firestore_toolset.get_document(collection="CustomerInstructions", document_id=customer_id)
  fetched_instruction = instructions_doc.get("data", {}).get("instruction", "")
  if not fetched_instruction:
    error_message = f"Error: No instructions found for customer {customer_id}."
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=error_message)])
    )

  print(f"Fetched instructions for customer {customer_id}: {fetched_instruction}")

  # Step 4: Modify the system instruction in the LlmRequest
  original_instruction = (
      llm_request.config.system_instruction or types.Content(role="system", parts=[])
  )
  if not isinstance(original_instruction, types.Content):
    original_instruction = types.Content(
        role="system", parts=[types.Part(text=str(original_instruction))]
    )
  if not original_instruction.parts:
    original_instruction.parts.append(types.Part(text=""))

  base_instruction = original_instruction.parts[0].text or ""
  # Prepend the fetched instructions to the original system instruction
  modified_instruction = (
      f"{fetched_instruction}"
  )
  print(f"Modified system instruction: {modified_instruction}")

  original_instruction.parts[0].text = modified_instruction
  llm_request.config.system_instruction = original_instruction
  print(f"Modified system instruction: {llm_request.config.system_instruction}")
  # Step 5: Return None to allow the modified request to proceed to the LLM
  return None
