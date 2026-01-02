
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import time
import asyncio

from agentic_dsta.api_hub_agent.tools import apihub_toolset

class TestApiHubToolset(unittest.IsolatedAsyncioTestCase):

    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.default')
    def test_get_access_token(self, mock_default):
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.token = "test_token"
        mock_default.return_value = (mock_creds, "test_project")

        token = apihub_toolset._get_access_token()
        self.assertEqual(token, "test_token")

    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.default')
    def test_get_access_token_refresh(self, mock_default):
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.token = "refreshed_token"
        mock_default.return_value = (mock_creds, "test_project")

        token = apihub_toolset._get_access_token()
        mock_creds.refresh.assert_called_once()
        self.assertEqual(token, "refreshed_token")

    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.requests.get')
    def test_list_apis_from_apihub(self, mock_get, mock_get_token):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"apis": [{"name": "projects/p/locations/l/apis/a"}]}
        mock_get.return_value = mock_response

        apis = apihub_toolset._list_apis_from_apihub("test_project", "us-central1")
        self.assertEqual(len(apis), 1)

    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.requests.get')
    def test_list_apis_from_apihub_fails(self, mock_get, mock_get_token):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            apihub_toolset._list_apis_from_apihub("test_project", "us-central1")

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.DynamicMultiAPIToolset._discover_and_load_apis')
    def test_dynamic_multi_api_toolset_init(self, mock_discover):
        toolset = apihub_toolset.DynamicMultiAPIToolset()
        mock_discover.assert_called_once()

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._list_apis_from_apihub', return_value=[{"name":"p/l/a/test_api", "displayName":"Test API"}])
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.ADKAPIHubToolset')
    async def test_dynamic_multi_api_toolset_get_tools(self, mock_adk_toolset, mock_get_token, mock_list_apis):
        mock_toolset_instance = MagicMock()
        mock_tool = MagicMock()
        mock_toolset_instance.get_tools = AsyncMock(return_value=[mock_tool])
        mock_adk_toolset.return_value = mock_toolset_instance

        toolset = apihub_toolset.DynamicMultiAPIToolset()
        tools = await toolset.get_tools()

        self.assertEqual(len(tools), 1)

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._list_apis_from_apihub', return_value=[{"name":"p/l/a/test_api", "displayName":"Test API"}])
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.ADKAPIHubToolset')
    async def test_lazy_load_api_toolset_get_tools(self, mock_adk_toolset, mock_get_token, mock_list_apis):
        mock_toolset_instance = MagicMock()
        mock_tool = MagicMock()
        mock_toolset_instance.get_tools = AsyncMock(return_value=[mock_tool])
        mock_adk_toolset.return_value = mock_toolset_instance

        toolset = apihub_toolset.LazyLoadAPIToolset(cache_duration_seconds=60)

        # First call, should load
        tools = await toolset.get_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(mock_list_apis.call_count, 1)

        # Second call, should still be cached if time hasn't passed
        tools = await toolset.get_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(mock_list_apis.call_count, 1)

        # Force cache to expire
        toolset._cache_timestamp = 0
        tools = await toolset.get_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(mock_list_apis.call_count, 2)


    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._list_apis_from_apihub', return_value=[
        {"name":"p/l/a/api1", "attributes": {"tags": ["prod"]}},
        {"name":"p/l/a/api2", "attributes": {"tags": ["dev"]}}
    ])
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset._get_access_token', return_value="test_token")
    @patch('agentic_dsta.api_hub_agent.tools.apihub_toolset.ADKAPIHubToolset')
    async def test_selective_api_toolset_get_tools(self, mock_adk_toolset, mock_get_token, mock_list_apis):
        mock_toolset_instance = MagicMock()
        mock_tool = MagicMock()
        mock_toolset_instance.get_tools = AsyncMock(return_value=[mock_tool])
        mock_adk_toolset.return_value = mock_toolset_instance

        toolset = apihub_toolset.SelectiveAPIToolset(required_tags=["prod"])
        tools = await toolset.get_tools()

        self.assertEqual(len(tools), 1)


if __name__ == '__main__':
    unittest.main()
