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
import asyncio
import os
import unittest
from unittest import mock

from agentic_dsta.tools.google_ads import google_ads_updater
import google.auth.exceptions
from google.ads.googleads.errors import GoogleAdsException


AsyncMock = mock.AsyncMock
MagicMock = mock.MagicMock
patch = mock.patch

class TestGoogleAdsUpdater(unittest.TestCase):

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_get_google_ads_client_with_oauth(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        client = google_ads_updater.get_google_ads_client("12345")
        mock_get_client.assert_called_once_with("12345")
        self.assertEqual(client, mock_client)

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client', return_value=None)
    def test_get_google_ads_client_exception(self, mock_get_client):
        client = google_ads_updater.get_google_ads_client("12345")
        self.assertIsNone(client)
        mock_get_client.assert_called_once_with("12345")

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_campaign_status(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_campaign_service = MagicMock()
        mock_client.get_service.return_value = mock_campaign_service
        mock_get_google_ads_client.return_value = mock_client

        mock_campaign_service.mutate_campaigns.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_google_ads_campaign_status("12345", "67890", "ENABLED")
        self.assertTrue(result['success'])

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_campaign_status_invalid(self, mock_get_google_ads_client):
        with self.assertRaises(ValueError):
            google_ads_updater.update_google_ads_campaign_status("12345", "67890", "INVALID")

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_campaign_budget(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_budget_service = MagicMock()
        mock_client.get_service.side_effect = [mock_ga_service, mock_budget_service]
        mock_get_google_ads_client.return_value = mock_client

        mock_row = MagicMock()
        mock_row.campaign.campaign_budget = "budget_resource"
        mock_ga_service.search_stream.return_value = [MagicMock(results=[mock_row])]
        mock_budget_service.mutate_campaign_budgets.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_google_ads_campaign_budget("12345", "67890", 50000)
        self.assertTrue(result['success'])

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_campaign_geo_targets(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_criterion_service = MagicMock()
        mock_client.get_service.side_effect = [mock_ga_service, mock_criterion_service, MagicMock(), MagicMock()] # campaign, geo
        mock_get_google_ads_client.return_value = mock_client

        mock_criterion_service.mutate_campaign_criteria.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_google_ads_campaign_geo_targets("12345", "67890", ["2840"])
        self.assertTrue(result['success'])

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_ad_group_geo_targets(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_criterion_service = MagicMock()
        mock_client.get_service.side_effect = [mock_ga_service, mock_criterion_service, MagicMock(), MagicMock()] # adgroup, geo
        mock_get_google_ads_client.return_value = mock_client

        mock_criterion_service.mutate_ad_group_criteria.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_google_ads_ad_group_geo_targets("12345", "adgroup1", ["2840"])
        self.assertTrue(result['success'])

    def test_google_ads_updater_toolset(self):
        toolset = google_ads_updater.GoogleAdsUpdaterToolset()
        tools = asyncio.run(toolset.get_tools())
        self.assertEqual(len(tools), 7)

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_shared_budget_success(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_budget_service = MagicMock()
        mock_client.get_service.return_value = mock_budget_service
        mock_get_google_ads_client.return_value = mock_client

        mock_budget_service.mutate_campaign_budgets.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_google_ads_shared_budget("12345", "customers/12345/campaignBudgets/123", 600000)
        self.assertTrue(result['success'])
        mock_budget_service.mutate_campaign_budgets.assert_called_once()

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_shared_budget_exception(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_budget_service = MagicMock()
        mock_client.get_service.return_value = mock_budget_service
        mock_get_google_ads_client.return_value = mock_client

        # Mock API exception
        error = MagicMock()
        error.error_code = "TEST_ERROR"
        error.message = "Test error message"
        failure = MagicMock()
        failure.errors = [error]
        mock_budget_service.mutate_campaign_budgets.side_effect = GoogleAdsException(None, None, failure, "request_id")

        result = google_ads_updater.update_google_ads_shared_budget("12345", "customers/12345/campaignBudgets/123", 600000)
        self.assertFalse(result['success'])
        self.assertIn("Failed to update shared budget", result['error'])

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client', return_value=None)
    def test_update_shared_budget_client_fail(self, mock_get_google_ads_client):
        with self.assertRaises(RuntimeError):
            google_ads_updater.update_google_ads_shared_budget("12345", "customers/12345/campaignBudgets/123", 600000)

    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_campaign_details')
    @patch('agentic_dsta.tools.google_ads.google_ads_updater.get_google_ads_client')
    def test_update_bidding_strategy_api_error(self, mock_get_client, mock_get_campaign):
        mock_client = MagicMock()
        mock_campaign_service = MagicMock()
        mock_client.get_service.return_value = mock_campaign_service
        mock_get_client.return_value = mock_client

        # Mock successful campaign details fetch
        mock_get_campaign.return_value = {"id": "123", "advertisingChannelType": "SEARCH"}

        # Mock API exception during mutate
        error = MagicMock()
        # Mocking error_code to return a string representation akin to what we see in logs
        error.error_code = "bidding_error: BIDDING_STRATEGY_AND_BUDGET_MUST_BE_ALIGNED"
        error.message = "Budget and strategy not aligned"
        failure = MagicMock()
        failure.errors = [error]
        mock_campaign_service.mutate_campaigns.side_effect = GoogleAdsException(None, None, failure, "request_id")

        result = google_ads_updater.update_google_ads_bidding_strategy(
            "12345", "67890", "MAXIMIZE_CONVERSIONS", {"target_cpa_micros": 1000000}
        )

        self.assertFalse(result['success'])
        self.assertIn("Failed to update bidding strategy", result['error'])
        self.assertIn("BIDDING_STRATEGY_AND_BUDGET_MUST_BE_ALIGNED", result['error'])

if __name__ == '__main__':
    unittest.main()
