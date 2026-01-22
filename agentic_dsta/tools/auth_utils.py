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
import logging
import os
from typing import List, Optional, Tuple

import google.auth
from google.auth.transport.requests import Request
from google.cloud import secretmanager
from google.oauth2 import credentials as oauth2_credentials
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def get_user_credentials_from_secret(scopes: List[str],
                                     service_name: str) -> Optional[oauth2_credentials.Credentials]:
    """Fetches user credentials directly from Secret Manager.

    Expects 'user-client-id', 'user-client-secret', and 'user-refresh-token'
    to exist in Google Secret Manager.

    Args:
        scopes: List of OAuth scopes required.
        service_name: Name of the service for logging.

    Returns:
        A google.oauth2.credentials.Credentials object or None if auth fails.
    """
    try:
        logger.info(f"Fetching {service_name} credentials from Secret Manager.")
        client = secretmanager.SecretManagerServiceClient()
        try:
            _, project_id = google.auth.default()
        except google.auth.exceptions.DefaultCredentialsError:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

        if not project_id:
            logger.error("GOOGLE_CLOUD_PROJECT not set and ADC failed to provide it.")
            return None

        secrets = {
            "client_id": "USER_CLIENT_ID",
            "client_secret": "USER_CLIENT_SECRET",
            "refresh_token": "USER_REFRESH_TOKEN"
        }
        creds_data = {}

        for key, secret_name in secrets.items():
            try:
                secret_path = client.secret_version_path(project_id, secret_name, "latest")
                response = client.access_secret_version(request={"name": secret_path})
                creds_data[key] = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Failed to fetch secret '{secret_name}' for {service_name}: {e}")
                return None

        user_creds = oauth2_credentials.Credentials(
            token=None,
            refresh_token=creds_data["refresh_token"],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=scopes
        )
        logger.info(f"Successfully obtained {service_name} credentials using user creds from Secret Manager")
        logger.info(f"User Secret Credentials for {service_name} used: {user_creds}")
        logger.info("Using User Account credentials fetched from Secret Manager")
        return user_creds
    except Exception as e:
        logger.exception(f"Failed to get {service_name} credentials from Secret Manager: {e}")
        return None

def get_credentials(scopes: List[str],
                    service_name: str,
                    force_user_creds_env: Optional[str] = None) -> Optional[oauth2_credentials.Credentials]:
    """Gets credentials, trying ADC first, then falling back to Secret Manager.

    Allows forcing the use of user credentials from Secret Manager by setting
    the environment variable specified in `force_user_creds_env` to 'true'.

    Args:
        scopes: List of OAuth scopes required.
        service_name: Name of the service for logging.
        force_user_creds_env: Name of an environment variable. If this env var is set to 'true',
                             Secret Manager creds are used, bypassing ADC.

    Returns:
        A google.oauth2.credentials.Credentials object or None if auth fails.
    """
    if force_user_creds_env and os.environ.get(force_user_creds_env, 'false').lower() == 'true':
        logger.info(f"Forcing user credentials from Secret Manager for {service_name} due to env var {force_user_creds_env}.")
        return get_user_credentials_from_secret(scopes, service_name)

    try:
        logger.debug(f"Attempting to get {service_name} credentials using ADC")
        credentials, project_id = google.auth.default(scopes=scopes)

        if credentials:
            valid_creds = False
            try:
                if not credentials.valid:
                    if hasattr(credentials, "refresh") and callable(credentials.refresh):
                        logger.debug(f"Refreshing ADC credentials for {service_name}")
                        credentials.refresh(Request())
                        valid_creds = credentials.valid
                    else:
                        logger.warning(f"ADC for {service_name} not valid and not refreshable.")
                else:
                    valid_creds = True
            except google.auth.exceptions.RefreshError as re:
                logger.warning(f"Failed to refresh ADC for {service_name}: {re}")

            if valid_creds:
                logger.info(f"Successfully obtained {service_name} credentials using ADC")
                logger.info(f"ADC Credentials for {service_name} used: {credentials}")
                if hasattr(credentials, 'service_account_email'):
                    logger.info(f"Using Service Account: {credentials.service_account_email}")
                else:
                    logger.info("Using Service Account: (email not available)")
                return credentials
            else:
                logger.warning(f"ADC for {service_name} not valid after refresh attempt.")
                # Fall through to Secret Manager fallback
        else:
            logger.warning(f"google.auth.default() returned None for {service_name} credentials.")
        # Fall through to Secret Manager fallback

    except google.auth.exceptions.DefaultCredentialsError:
        logger.info(f"ADC not suitable for {service_name}, falling back to user credentials from Secret Manager.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during ADC check for {service_name}: {e}")

    # Fallback to Secret Manager
    return get_user_credentials_from_secret(scopes, service_name)
