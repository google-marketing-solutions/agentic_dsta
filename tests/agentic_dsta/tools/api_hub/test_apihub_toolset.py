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

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import time
import asyncio

from agentic_dsta.tools.api_hub import apihub_toolset

class TestApiHubToolset(unittest.IsolatedAsyncioTestCase):

    @patch('agentic_dsta.tools.api_hub.apihub_toolset.default')
    def test_get_access_token(self, mock_default):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "test_token"
        mock_default.return_value = (mock_creds, "test_project")

        token = apihub_toolset._get_access_token()
        self.assertEqual(token, "test_token")

    @patch('agentic_dsta.tools.api_hub.apihub_toolset.default')
    def test_get_access_token_refresh(self, mock_default):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.token = "refreshed_token"
        mock_default.return_value = (mock_creds, "test_project")

        token = apihub_toolset._get_access_token()
        mock_creds.refresh.assert_called_once()
        self.assertEqual(token, "refreshed_token")

    @patch('agentic_dsta.tools.api_hub.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.tools.api_hub.apihub_toolset.requests.get')
    def test_list_apis_from_apihub(self, mock_get, mock_get_token):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"apis": [{"name": "projects/p/locations/l/apis/a"}]}
        mock_get.return_value = mock_response

        apis = apihub_toolset._list_apis_from_apihub("test_project", "us-central1")
        self.assertEqual(len(apis), 1)

    @patch('agentic_dsta.tools.api_hub.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.tools.api_hub.apihub_toolset.requests.get')
    def test_list_apis_from_apihub_fails(self, mock_get, mock_get_token):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            apihub_toolset._list_apis_from_apihub("test_project", "us-central1")

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.tools.api_hub.apihub_toolset.DynamicMultiAPIToolset._discover_and_load_apis')
    def test_dynamic_multi_api_toolset_init(self, mock_discover):
        toolset = apihub_toolset.DynamicMultiAPIToolset()
        mock_discover.assert_called_once()

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.tools.api_hub.apihub_toolset._list_apis_from_apihub', return_value=[{"name":"p/l/a/test_api", "displayName":"Test API"}])
    @patch('agentic_dsta.tools.api_hub.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.tools.api_hub.apihub_toolset.ADKAPIHubToolset')
    async def test_dynamic_multi_api_toolset_get_tools(self, mock_adk_toolset, mock_get_token, mock_list_apis):
        mock_toolset_instance = MagicMock()
        mock_tool = MagicMock()
        mock_toolset_instance.get_tools = AsyncMock(return_value=[mock_tool])
        mock_adk_toolset.return_value = mock_toolset_instance

        toolset = apihub_toolset.DynamicMultiAPIToolset()
        tools = await toolset.get_tools()

        self.assertEqual(len(tools), 1)


if __name__ == '__main__':
    unittest.main()
