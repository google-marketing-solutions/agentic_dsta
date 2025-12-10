import asyncio
import os
import unittest
from unittest import mock

from agentic_dsta.google_ads_agent.tools import google_ads_getter
from google.ads.googleads.errors import GoogleAdsException


call = mock.call
patch = mock.patch
MagicMock = mock.MagicMock


class TestGoogleAdsGetter(unittest.TestCase):
    """Tests for the google_ads_getter module."""

    @patch.dict(os.environ, {
        "GOOGLE_ADS_CLIENT_ID": "test_client_id",
        "GOOGLE_ADS_CLIENT_SECRET": "test_client_secret",
        "GOOGLE_ADS_REFRESH_TOKEN": "test_refresh_token",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "test_token",
    })
    @patch('google.ads.googleads.client.GoogleAdsClient.load_from_dict')
    def test_get_google_ads_client_with_oauth(self, mock_load_from_dict):
        google_ads_getter.get_google_ads_client("12345")
        mock_load_from_dict.assert_called_with({
            "login_customer_id": "12345",
            "developer_token": "test_token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "refresh_token": "test_refresh_token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "use_proto_plus": True,
        })

    @patch("google.ads.googleads.client.GoogleAdsClient.load_from_dict", side_effect=GoogleAdsException(None, None, MagicMock(), "request_id"))
    def test_get_google_ads_client_exception(self, mock_load_from_dict):
        client = google_ads_getter.get_google_ads_client("12345")
        self.assertIsNone(client)

    @patch("agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client")
    def test_get_campaign_details(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_row = MagicMock()
        mock_row.campaign._pb = MagicMock()
        mock_ga_service.search_stream.return_value = [MagicMock(results=[mock_row])]

        with patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.MessageToDict', return_value={'id': 'test_campaign_id'}) as mock_msg_to_dict:
            result = google_ads_getter.get_campaign_details("12345", "test_campaign_id")

        self.assertIn('id', result)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_get_campaign_details_not_found(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_ga_service.search_stream.return_value = [MagicMock(results=[])]

        result = google_ads_getter.get_campaign_details("12345", "test_campaign_id")

        self.assertEqual(result, {"error": "Campaign with ID 'test_campaign_id' not found."})

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_get_campaign_details_exception(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_ga_service.search_stream.side_effect = GoogleAdsException(None, None, MagicMock(), "request_id")

        result = google_ads_getter.get_campaign_details("12345", "test_campaign_id")

        self.assertIn("error", result)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_search_geo_target_constants(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_gtc_service = MagicMock()
        mock_client.get_service.return_value = mock_gtc_service
        mock_get_google_ads_client.return_value = mock_client

        mock_suggestion = MagicMock()
        mock_suggestion.geo_target_constant._pb = MagicMock()
        mock_gtc_service.suggest_geo_target_constants.return_value = MagicMock(geo_target_constant_suggestions=[mock_suggestion])

        with patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.MessageToDict', return_value={'resourceName': 'geoTargetConstants/1023191'}) as mock_msg_to_dict:
            result = google_ads_getter.search_geo_target_constants("12345", "New York")

        self.assertIn('suggestions', result)
        self.assertEqual(len(result['suggestions']), 1)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_search_geo_target_constants_exception(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_gtc_service = MagicMock()
        mock_client.get_service.return_value = mock_gtc_service
        mock_get_google_ads_client.return_value = mock_client

        mock_gtc_service.suggest_geo_target_constants.side_effect = GoogleAdsException(None, None, MagicMock(), "request_id")

        result = google_ads_getter.search_geo_target_constants("12345", "New York")
        self.assertIn("error", result)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_get_geo_targets(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_campaign_row = MagicMock()
        mock_campaign_row.campaign_criterion._pb = MagicMock()

        mock_adgroup_row = MagicMock()
        mock_adgroup_row.ad_group.id = "adgroup1"
        mock_adgroup_row.ad_group_criterion._pb = MagicMock()

        mock_ga_service.search_stream.side_effect = [
            [MagicMock(results=[mock_campaign_row])],
            [MagicMock(results=[mock_adgroup_row])]
        ]

        with patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.MessageToDict', side_effect=[{'location': {'geoTargetConstant': 'geoTargetConstants/2840'}}, {'location': {'geoTargetConstant': 'geoTargetConstants/1023191'}}]) as mock_msg_to_dict:
            result = google_ads_getter.get_geo_targets("12345", "test_campaign_id")

        self.assertIn("campaign_targets", result)
        self.assertIn("ad_group_targets", result)
        self.assertEqual(len(result['campaign_targets']), 1)
        self.assertEqual(len(result['ad_group_targets']['adgroup1']), 1)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_get_geo_targets_campaign_exception(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_ga_service.search_stream.side_effect = [GoogleAdsException(None, None, MagicMock(), "request_id"), []]

        result = google_ads_getter.get_geo_targets("12345", "test_campaign_id")
        self.assertIn("error", result)

    @patch('agentic_dsta.google_ads_agent.tools.google_ads_getter.get_google_ads_client')
    def test_get_geo_targets_adgroup_exception(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client

        mock_ga_service.search_stream.side_effect = [[], GoogleAdsException(None, None, MagicMock(), "request_id")]

        result = google_ads_getter.get_geo_targets("12345", "test_campaign_id")
        self.assertIn("error", result)

    def test_google_ads_getter_toolset(self):
        toolset = google_ads_getter.GoogleAdsGetterToolset()
        tools = asyncio.run(toolset.get_tools())
        self.assertEqual(len(tools), 3)

if __name__ == '__main__':
    unittest.main()
