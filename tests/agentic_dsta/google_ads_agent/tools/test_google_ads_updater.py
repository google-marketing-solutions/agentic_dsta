import asyncio
import os
import unittest
from unittest import mock

from agentic_dsta.google_ads_agent.tools import google_ads_updater
from google.ads.googleads.errors import GoogleAdsException


AsyncMock = mock.AsyncMock
MagicMock = mock.MagicMock
patch = mock.patch

class TestGoogleAdsUpdater(unittest.TestCase):

    @patch.dict(os.environ, {
        "GOOGLE_ADS_CLIENT_ID": "test_client_id",
        "GOOGLE_ADS_CLIENT_SECRET": "test_client_secret",
        "GOOGLE_ADS_REFRESH_TOKEN": "test_refresh_token",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "test_token",
    })
    @patch('google.ads.googleads.client.GoogleAdsClient.load_from_dict')
    def test_get_google_ads_client_with_oauth(self, mock_load_from_dict):
        google_ads_updater.get_google_ads_client("12345")
        mock_load_from_dict.assert_called_with({
            "login_customer_id": "12345",
            "developer_token": "test_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "use_proto_plus": True,
        })

    @patch('google.ads.googleads.client.GoogleAdsClient.load_from_dict', side_effect=GoogleAdsException(None, None, MagicMock(), "request_id"))
    def test_get_google_ads_client_exception(self, mock_load_from_dict):
        client = google_ads_updater.get_google_ads_client("12345")
        self.assertIsNone(client)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_updater.get_google_ads_client')
    def test_update_campaign_status(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_campaign_service = MagicMock()
        mock_client.get_service.return_value = mock_campaign_service
        mock_get_google_ads_client.return_value = mock_client

        mock_campaign_service.mutate_campaigns.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_campaign_status("12345", "67890", "ENABLED")
        self.assertTrue(result['success'])

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_updater.get_google_ads_client')
    def test_update_campaign_status_invalid(self, mock_get_google_ads_client):
        result = google_ads_updater.update_campaign_status("12345", "67890", "INVALID")
        self.assertIn('error', result)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_updater.get_google_ads_client')
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

        result = google_ads_updater.update_campaign_budget("12345", "67890", 50000)
        self.assertTrue(result['success'])

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_updater.get_google_ads_client')
    def test_update_campaign_geo_targets(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_criterion_service = MagicMock()
        mock_client.get_service.side_effect = [mock_ga_service, mock_criterion_service, MagicMock(), MagicMock()] # campaign, geo
        mock_get_google_ads_client.return_value = mock_client

        mock_criterion_service.mutate_campaign_criteria.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_campaign_geo_targets("12345", "67890", ["2840"])
        self.assertTrue(result['success'])

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_updater.get_google_ads_client')
    def test_update_ad_group_geo_targets(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_criterion_service = MagicMock()
        mock_client.get_service.side_effect = [mock_ga_service, mock_criterion_service, MagicMock(), MagicMock()] # adgroup, geo
        mock_get_google_ads_client.return_value = mock_client

        mock_criterion_service.mutate_ad_group_criteria.return_value = MagicMock(results=[MagicMock(resource_name="test_resource")])

        result = google_ads_updater.update_ad_group_geo_targets("12345", "adgroup1", ["2840"])
        self.assertTrue(result['success'])

    def test_google_ads_updater_toolset(self):
        toolset = google_ads_updater.GoogleAdsUpdaterToolset()
        tools = asyncio.run(toolset.get_tools())
        self.assertEqual(len(tools), 4)

if __name__ == '__main__':
    unittest.main()
