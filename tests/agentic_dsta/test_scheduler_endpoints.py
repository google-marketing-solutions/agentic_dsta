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
"""Unit tests for Cloud Scheduler endpoint OIDC authentication and execution."""

import os
import sys
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

# Ensure we can import from agentic_dsta
sys.path.append(os.getcwd())

from agentic_dsta.main import app  # pylint: disable=g-import-not-at-top

client = TestClient(app)

AUTHORIZED_SCHEDULER_SA = "adsta-runner@demo-project.iam.gserviceaccount.com"
VALID_CLAIMS = {
    "iss": "https://accounts.google.com",
    "email": AUTHORIZED_SCHEDULER_SA,
    "email_verified": True,
}


def test_scheduler_init_and_run_unauthenticated_rejected():
  """Requests without an Authorization header must be rejected with 401."""
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
      "usecase": "GoogleAds",
  }
  response = client.post("/scheduler/init_and_run", json=payload)
  assert response.status_code == 401
  assert response.headers.get("www-authenticate") == "Bearer"
  assert "Missing or invalid Authorization header" in response.json()["detail"]


@pytest.mark.parametrize(
    "auth_header",
    ["Basic dXNlcjpwYXNz", "Bearer ", "Bearer    ", "Token abc123"],
)
def test_scheduler_init_and_run_malformed_auth_header_rejected(
    auth_header: str,
):
  """Non-Bearer or empty Bearer headers must be rejected with 401."""
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
  }
  response = client.post(
      "/scheduler/init_and_run",
      json=payload,
      headers={"Authorization": auth_header},
  )
  assert response.status_code == 401


def test_scheduler_init_and_run_invalid_token_rejected_without_leaking_error():
  """Invalid or expired OIDC tokens must return generic 401 without internal trace."""
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
      "usecase": "GoogleAds",
  }
  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      side_effect=ValueError("internal signature verification detail"),
  ):
    response = client.post(
        "/scheduler/init_and_run",
        json=payload,
        headers={"Authorization": "Bearer expired_or_forged_token"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail == "Invalid authentication token."
    assert "internal signature verification detail" not in detail


def test_scheduler_init_and_run_untrusted_issuer_rejected():
  """Tokens from non-Google issuers must be rejected with 401."""
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
  }
  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value={"iss": "https://evil.example.com"},
  ):
    response = client.post(
        "/scheduler/init_and_run",
        json=payload,
        headers={"Authorization": "Bearer untrusted_issuer_token"},
    )
    assert response.status_code == 401


def test_scheduler_init_and_run_unauthorized_service_account_rejected(
    monkeypatch: pytest.MonkeyPatch,
):
  """Valid Google OIDC tokens from another principal must be rejected with 403."""
  monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT_EMAIL", AUTHORIZED_SCHEDULER_SA)
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
  }
  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value={
          "iss": "https://accounts.google.com",
          "email": "attacker@other-project.iam.gserviceaccount.com",
          "email_verified": True,
      },
  ):
    response = client.post(
        "/scheduler/init_and_run",
        json=payload,
        headers={"Authorization": "Bearer valid_other_sa_token"},
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]


def test_scheduler_init_and_run_unverified_email_rejected(
    monkeypatch: pytest.MonkeyPatch,
):
  """OIDC tokens with email_verified=False must be rejected with 403."""
  monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT_EMAIL", AUTHORIZED_SCHEDULER_SA)
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
  }
  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value={
          "iss": "https://accounts.google.com",
          "email": AUTHORIZED_SCHEDULER_SA,
          "email_verified": False,
      },
  ):
    response = client.post(
        "/scheduler/init_and_run",
        json=payload,
        headers={"Authorization": "Bearer unverified_email_token"},
    )
    assert response.status_code == 403


def test_scheduler_init_and_run_internal_failure_hides_details():
  """Internal agent exceptions return generic 500 without leaking raw traces."""
  payload = {
      "app_name": "decision_agent",
      "customer_id": "4086619433",
      "usecase": "GoogleAds",
  }
  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value=VALID_CLAIMS,
  ):
    with patch(
        "agentic_dsta.main.run_decision_agent",
        new_callable=AsyncMock,
        side_effect=RuntimeError("secret_db_connection_string_failure"),
    ):
      response = client.post(
          "/scheduler/init_and_run",
          json=payload,
          headers={"Authorization": "Bearer valid_oidc_token"},
      )
      assert response.status_code == 500
      assert (
          response.json()["detail"]
          == "Internal server error while running decision agent."
      )
      assert "secret_db_connection_string_failure" not in response.text


def test_scheduler_init_and_run_success(monkeypatch: pytest.MonkeyPatch):
  """Authorized Cloud Scheduler OIDC requests execute run_decision_agent."""
  monkeypatch.setenv("SCHEDULER_SERVICE_ACCOUNT_EMAIL", AUTHORIZED_SCHEDULER_SA)
  monkeypatch.setenv(
      "SCHEDULER_OIDC_AUDIENCE",
      "https://adsta-app.a.run.app/scheduler/init_and_run",
  )
  payload = {
      "app_name": "decision_agent",
      "new_message": {
          "parts": [{"text": "Analyse and update customerid: 4086619433"}],
          "role": "user",
      },
      "session_id": "session-2026-01-04T15:39:43Z",
      "streaming": False,
      "user_id": AUTHORIZED_SCHEDULER_SA,
      "customer_id": "4086619433",
  }

  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value=VALID_CLAIMS,
  ) as mock_verify:
    with patch(
        "agentic_dsta.main.run_decision_agent", new_callable=AsyncMock
    ) as mock_run_agent:
      mock_run_agent.return_value = {"status": "success"}

      response = client.post(
          "/scheduler/init_and_run",
          json=payload,
          headers={"Authorization": "Bearer valid_oidc_token"},
      )

      assert response.status_code == 200
      assert response.json() == {
          "message": "Decision agent run completed for 4086619433",
          "status": "success",
      }
      assert (
          mock_verify.call_args.kwargs["audience"]
          == "https://adsta-app.a.run.app/scheduler/init_and_run"
      )
      mock_run_agent.assert_called_once_with("4086619433", None)


def test_scheduler_init_and_run_session_failure():
  """Authenticated requests missing customer_id return 400."""
  payload = {
      "app_name": "decision_agent",
      "new_message": {
          "parts": [{"text": "No customer id here"}],
          "role": "user",
      },
  }

  with patch(
      "agentic_dsta.main.id_token.verify_oauth2_token",
      return_value=VALID_CLAIMS,
  ):
    response = client.post(
        "/scheduler/init_and_run",
        json=payload,
        headers={"Authorization": "Bearer valid_oidc_token"},
    )
    assert response.status_code == 400
    assert "Missing customer_id" in response.json()["detail"]
