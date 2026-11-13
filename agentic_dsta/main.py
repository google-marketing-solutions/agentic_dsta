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
"""Main application file for the FastAPI server."""

from collections.abc import Mapping
import logging
import os
from typing import Any

from dotenv import load_dotenv
import fastapi
from fastapi import HTTPException, Request
from google.adk.cli import fast_api
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import uvicorn

from agentic_dsta.agents.decision_agent.agent import run_decision_agent
from agentic_dsta.core.logging_config import setup_logging


# Load environment variables from .env file for local development
load_dotenv()

# Setup centralized logging
setup_logging()

logger = logging.getLogger(__name__)


FastAPI = fastapi.FastAPI
get_fast_api_app = fast_api.get_fast_api_app

# Get the directory where main.py is located
AGENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents")
# Use an in-memory SQLite database for sessions to avoid file locking issues in
# a scaled environment.
SESSION_SERVICE_URI = "sqlite:///:memory:"
# Example allowed origins for CORS
# For production environments, it is recommended to use a more restrictive list
# of allowed origins.
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True
GOOGLE_OIDC_ISSUERS = frozenset({
    "https://accounts.google.com",
    "accounts.google.com",
})

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('decision_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


def verify_scheduler_oidc_request(request: Request) -> Mapping[str, Any]:
  """Verifies the Google OIDC Bearer token and optional caller SA email."""
  auth_header = request.headers.get("Authorization", "")
  scheme, separator, raw_token = auth_header.partition(" ")
  token = raw_token.strip()
  if scheme != "Bearer" or separator != " " or not token:
    raise HTTPException(
        status_code=401,
        detail="Missing or invalid Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

  expected_audience = os.getenv("SCHEDULER_OIDC_AUDIENCE", "").strip() or None
  try:
    claims = id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        audience=expected_audience,
    )
  except Exception as exc:  # pylint: disable=broad-exception-caught
    logger.warning("Rejected invalid OIDC token on /scheduler/init_and_run: %s", exc)
    raise HTTPException(
        status_code=401,
        detail="Invalid authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    ) from None

  if claims.get("iss") not in GOOGLE_OIDC_ISSUERS:
    logger.warning(
        "Rejected OIDC token with untrusted issuer on /scheduler/init_and_run: %r",
        claims.get("iss"),
    )
    raise HTTPException(
        status_code=401,
        detail="Invalid authentication token issuer.",
        headers={"WWW-Authenticate": "Bearer"},
    )

  expected_service_account = os.getenv(
      "SCHEDULER_SERVICE_ACCOUNT_EMAIL", ""
  ).strip()
  if expected_service_account:
    caller_email = claims.get("email")
    email_verified = claims.get("email_verified")
    if email_verified is not True or caller_email != expected_service_account:
      logger.warning(
          "Rejected unauthorized scheduler principal %r (verified=%r).",
          caller_email,
          email_verified,
      )
      raise HTTPException(
          status_code=403,
          detail="Caller is not authorized to invoke scheduler endpoint.",
      )

  return claims


@app.post("/scheduler/init_and_run")
async def scheduler_init_and_run(request: Request):
  """Combined endpoint for Cloud Scheduler to initialize and run the agent."""
  verify_scheduler_oidc_request(request)

  payload = await request.json()

  # Extract necessary fields for logging/validation
  app_name = payload.get("app_name")
  if app_name != "decision_agent":
    raise HTTPException(
        status_code=400,
        detail="This endpoint is restricted to decision_agent only.",
    )

  # Parse the customer_id from payload
  customer_id = payload.get("customer_id") or payload.get("user_id")
  # Fetch the usecase from payload i.e. either google ads or sa360
  usecase = payload.get("usecase")

  if not customer_id:
    raise HTTPException(
        status_code=400,
        detail="Missing customer_id (or user_id) in payload.",
    )

  logger.info(
      "Scheduler: Triggering decision_agent for customer_id=%s", customer_id
  )

  try:
    await run_decision_agent(customer_id, usecase)
    return {
        "status": "success",
        "message": f"Decision agent run completed for {customer_id}",
    }
  except Exception:  # pylint: disable=broad-exception-caught
    logger.exception(
        "Error running decision agent for customer_id=%s", customer_id
    )
    raise HTTPException(
        status_code=500,
        detail="Internal server error while running decision agent.",
    ) from None


def main():
  """Starts the FastAPI server."""
  # Use the PORT environment variable provided by Cloud Run, defaulting to 8080
  uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


if __name__ == "__main__":
  main()
