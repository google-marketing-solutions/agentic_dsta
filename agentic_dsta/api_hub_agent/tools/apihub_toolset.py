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
"""
Dynamic Multi-API Toolset - Loads APIs from API Hub at runtime without redeployment.

This approach queries API Hub for available APIs and loads them dynamically,
eliminating the need for redeployment when new APIs are registered.
"""

import os
from typing import Any, Dict, List, Optional
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.apihub_tool.apihub_toolset import APIHubToolset as ADKAPIHubToolset
from google.auth import default
from google.auth.transport.requests import Request
import requests
import logging


logger = logging.getLogger(__name__)


def _get_access_token() -> str:
    """Get OAuth2 access token for API Hub API."""
    import os
    credentials, project_id = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])

    # Set quota project to avoid warnings
    if hasattr(credentials, 'quota_project_id') and not credentials.quota_project_id:
        quota_project = os.environ.get('GOOGLE_CLOUD_PROJECT') or project_id
        if quota_project:
            credentials = credentials.with_quota_project(quota_project)

    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def _list_apis_from_apihub(project_id: str, location: str) -> List[Dict[str, Any]]:
    """
    Query API Hub to get list of available APIs.

    Returns list of APIs with their metadata.
    """
    access_token = _get_access_token()
    base_url = "https://apihub.googleapis.com/v1"
    parent = f"projects/{project_id}/locations/{location}"
    url = f"{base_url}/{parent}/apis"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    logger.info("Querying API Hub: %s", url)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.error("API Hub query failed: %s - %s", response.status_code, response.text)
        response.raise_for_status()

    data = response.json()
    apis = data.get("apis", [])
    logger.info("Found %s APIs in API Hub", len(apis))
    return apis


class DynamicMultiAPIToolset(BaseToolset):
    """
    Dynamically loads ALL APIs from API Hub at initialization.

    No redeployment needed - automatically picks up new APIs when agent restarts.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        filter_tags: Optional[List[str]] = None,
        max_apis: int = 50
    ):
        """
        Initialize and discover APIs from API Hub.

        Args:
            project_id: GCP project ID
            location: API Hub location
            filter_tags: Optional list of tags to filter APIs (e.g., ["production", "internal"])
            max_apis: Maximum number of APIs to load (default: 50)
        """
        super().__init__()
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._location = location
        self._filter_tags = filter_tags or []
        self._max_apis = max_apis
        self._api_toolsets = []

        # Discover and load APIs dynamically
        self._discover_and_load_apis()

    def _discover_and_load_apis(self):
        """Discover APIs from API Hub and create toolsets."""
        if not self._project_id:
            logger.error("No project_id provided. Set GOOGLE_CLOUD_PROJECT environment variable.")
            return

        logger.info(
            "Discovering APIs from API Hub (project: %s, location: %s)",
            self._project_id,
            self._location
        )

        try:
            # Query API Hub for available APIs
            apis = _list_apis_from_apihub(self._project_id, self._location)

            if not apis:
                logger.warning(
                    "No APIs found in API Hub. Please ensure:\n"
                    "  1. APIs are registered in API Hub\n"
                    "  2. You have apihub.apis.list permission\n"
                    "  3. API Hub is enabled in your project"
                )
                return

            access_token = _get_access_token()

            loaded_count = 0
            skipped_count = 0

            for api in apis:
                if loaded_count >= self._max_apis:
                    break

                # Extract API info
                api_name = api.get("name", "")  # Full resource name
                display_name = api.get("displayName", "")
                description = api.get("description", "")

                # Extract API ID from resource name
                # Format: projects/*/locations/*/apis/{api-id}
                api_id = api_name.split("/")[-1]

                # Filter by tags if specified
                if self._filter_tags:
                    api_attributes = api.get("attributes", {})
                    api_tags = api_attributes.get("tags", [])
                    if not any(tag in api_tags for tag in self._filter_tags):
                        logger.info(
                            "Skipping %s: missing required tags %s",
                            api_id,
                            self._filter_tags,
                            extra={'api_id': api_id}
                        )
                        skipped_count += 1
                        continue

                try:
                    logger.info(
                        "Loading API: %s",
                        api_id,
                        extra={'api_id': api_id, 'display_name': display_name}
                    )

                    # Check for API key requirement and use environment variable if available
                    # Improved API Key Discovery
                    api_key_env_variable = f"{display_name.upper().replace(' ', '_')}_API_KEY"
                    api_key = os.environ.get(api_key_env_variable) or None

                    if not api_key:
                        # Fallback to a generic key if the specific one is not found
                        api_key = os.environ.get("GOOGLE_API_KEY")

                    auth_scheme = None
                    auth_credential = None

                    if api_key:
                        logger.info(
                            "Configuring API key authentication for %s (%s)",
                            display_name,
                            api_id,
                            extra={'api_id': api_id, 'display_name': display_name}
                        )
                        from google.adk.tools.openapi_tool.auth.auth_helpers import (
                            token_to_scheme_credential
                        )
                        # Pollen API uses 'key' as the query parameter name
                        auth_scheme, auth_credential = token_to_scheme_credential(
                            "apikey", "query", "key", api_key
                        )
                    else:
                        logger.warning(
                            "No API key found for %s",
                            display_name,
                            extra={'api_id': api_id, 'display_name': display_name}
                        )

                    # Create APIHubToolset for this API
                    toolset = ADKAPIHubToolset(
                        name=api_id,
                        description=description or f"API Hub API: {display_name}",
                        access_token=access_token,
                        apihub_resource_name=api_name,
                        auth_scheme=auth_scheme,
                        auth_credential=auth_credential,
                    )
                    self._api_toolsets.append(toolset)
                    loaded_count += 1
                    logger.info("✓ Loaded API: %s", api_id, extra={'api_id': api_id})
                except Exception as e:
                    # Skip APIs that can't be loaded (e.g., no spec)
                    logger.warning(
                        "✗ Skipping API %s: %s",
                        api_id,
                        str(e),
                        extra={'api_id': api_id},
                        exc_info=True
                    )
                    skipped_count += 1
                    continue

            logger.info(
                "\n=== API Discovery Summary ===\n"
                "Total APIs in API Hub: %s\n"
                "Successfully loaded: %s\n"
                "Skipped: %s\n"
                "Filter tags: %s",
                len(apis),
                loaded_count,
                skipped_count,
                self._filter_tags if self._filter_tags else 'None'
            )

        except Exception as e:
            logger.error("ERROR discovering APIs from API Hub: %s", str(e), exc_info=True)
            # Continue with empty toolsets - agent will work without API Hub APIs

    async def get_tools(self, readonly_context: Optional[Any] = None) -> List[FunctionTool]:
        """Returns all tools from all discovered APIs."""
        all_tools = []
        for toolset in self._api_toolsets:
            try:
                tools = await toolset.get_tools(readonly_context)
                all_tools.extend(tools)
            except Exception as e:
                logger.error("Error loading tools from toolset: %s", str(e), exc_info=True)
                continue
        return all_tools


class LazyLoadAPIToolset(BaseToolset):
    """
    Lazy-loading approach - APIs are loaded on-demand when first used.

    Even more dynamic - can discover and load APIs during agent execution.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        cache_duration_seconds: int = 300  # Refresh API list every 5 minutes
    ):
        """
        Initialize lazy-loading API toolset.

        Args:
            project_id: GCP project ID
            location: API Hub location
            cache_duration_seconds: How long to cache the API list
        """
        super().__init__()
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._location = location
        self._cache_duration = cache_duration_seconds
        self._cached_tools = None
        self._cache_timestamp = 0

    async def get_tools(self, readonly_context: Optional[Any] = None) -> List[FunctionTool]:
        """
        Get tools with lazy loading and caching.

        This method is called by ADK each time it needs the tools list.
        We can refresh the API list periodically.
        """
        import time

        current_time = time.time()

        # Check if cache is still valid
        if (self._cached_tools is not None and
            current_time - self._cache_timestamp < self._cache_duration):
            return self._cached_tools

        # Refresh cache by discovering APIs
        all_tools = []
        try:
            apis = _list_apis_from_apihub(self._project_id, self._location)
            access_token = _get_access_token()

            for api in apis[:50]:  # Limit to 50 APIs
                api_name = api.get("name", "")
                api_id = api_name.split("/")[-1]
                description = api.get("description", "")

                try:
                    toolset = ADKAPIHubToolset(
                        name=api_id,
                        description=description or f"API: {api_id}",
                        access_token=access_token,
                        apihub_resource_name=api_name,
                    )
                    tools = await toolset.get_tools(readonly_context)
                    all_tools.extend(tools)
                except Exception:
                    continue

            # Update cache
            self._cached_tools = all_tools
            self._cache_timestamp = current_time

        except Exception as e:
            logger.error("Error loading APIs: %s", str(e), exc_info=True)
            # Return cached tools or empty list
            return self._cached_tools or []

        return all_tools


class SelectiveAPIToolset(BaseToolset):
    """
    Load APIs based on tags/attributes from API Hub.

    Use API Hub metadata to automatically select which APIs to load:
    - Tags: "agent-enabled", "production", "public"
    - Attributes: team, domain, version
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        required_tags: Optional[List[str]] = None,
        required_attributes: Optional[Dict[str, str]] = None
    ):
        """
        Initialize with tag/attribute filtering.

        Args:
            project_id: GCP project ID
            location: API Hub location
            required_tags: APIs must have at least one of these tags
            required_attributes: APIs must have these attributes

        Example:
            # Only load APIs tagged for agent use
            SelectiveAPIToolset(required_tags=["agent-enabled", "production"])

            # Only load APIs from specific team
            SelectiveAPIToolset(required_attributes={"team": "payments"})
        """
        super().__init__()
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._location = location
        self._required_tags = required_tags or []
        self._required_attributes = required_attributes or {}
        self._api_toolsets = []

        self._discover_and_load_apis()

    def _matches_criteria(self, api: Dict[str, Any]) -> bool:
        """Check if API matches the selection criteria."""
        attributes = api.get("attributes", {})

        # Check required tags
        if self._required_tags:
            api_tags = attributes.get("tags", [])
            if not any(tag in api_tags for tag in self._required_tags):
                return False

        # Check required attributes
        for key, value in self._required_attributes.items():
            if attributes.get(key) != value:
                return False

        return True

    def _discover_and_load_apis(self):
        """Discover and load APIs matching criteria."""
        if not self._project_id:
            logger.error("No project_id provided. Set GOOGLE_CLOUD_PROJECT environment variable.")
            return

        logger.info(
            "Discovering APIs from API Hub (project: %s, location: %s)",
            self._project_id,
            self._location
        )
        if self._required_tags:
            logger.info("Filtering by tags: %s", self._required_tags)
        if self._required_attributes:
            logger.info("Filtering by attributes: %s", self._required_attributes)

        try:
            apis = _list_apis_from_apihub(self._project_id, self._location)

            if not apis:
                logger.warning("No APIs found in API Hub.")
                return

            access_token = _get_access_token()
            matched_count = 0

            for api in apis:
                api_name = api.get("name", "")
                api_id = api_name.split("/")[-1]

                if not self._matches_criteria(api):
                    logger.info(
                        "Skipping %s: doesn't match criteria",
                        api_id,
                        extra={'api_id': api_id}
                    )
                    continue

                description = api.get("description", "")

                try:
                    logger.info("Loading API: %s", api_id, extra={'api_id': api_id})
                    toolset = ADKAPIHubToolset(
                        name=api_id,
                        description=description or f"API: {api_id}",
                        access_token=access_token,
                        apihub_resource_name=api_name,
                    )
                    self._api_toolsets.append(toolset)
                    matched_count += 1
                    logger.info("✓ Loaded API: %s", api_id, extra={'api_id': api_id})
                except Exception as e:
                    logger.warning(
                        "✗ Failed to load %s: %s",
                        api_id,
                        str(e),
                        extra={'api_id': api_id},
                        exc_info=True
                    )
                    continue

            logger.info(
                "\n=== API Discovery Summary ===\n"
                "Total APIs in API Hub: %s\n"
                "Loaded %s APIs matching criteria",
                len(apis),
                matched_count
            )

        except Exception as e:
            logger.error("ERROR discovering APIs: %s", str(e), exc_info=True)

    async def get_tools(self, readonly_context: Optional[Any] = None) -> List[FunctionTool]:
        """Returns all tools from matching APIs."""
        all_tools = []
        for toolset in self._api_toolsets:
            try:
                tools = await toolset.get_tools(readonly_context)
                all_tools.extend(tools)
            except Exception:
                continue
        return all_tools
