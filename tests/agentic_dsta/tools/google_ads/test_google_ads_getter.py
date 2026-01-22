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
from agentic_dsta.tools.google_ads import google_ads_getter
from agentic_dsta.tools import auth_utils
from google.ads.googleads.errors import GoogleAdsException
from google.oauth2 import credentials

call = mock.call
patch = mock.patch
MagicMock = mock.MagicMock

class TestGoogleAdsGetter(unittest.TestCase):
    """Tests for the google_ads_getter module."""

    @patch('agentic_dsta.tools.google_ads.google_ads_client.google.ads.googleads.client.GoogleAdsClient')
    @patch('agentic_dsta.tools.auth_utils.get_credentials')
    def test_get_google_ads_client_default_adc(self, mock_get_credentials, mock_google_ads_client_cls):
        with mock.patch.dict(os.environ, {"GOOGLE_ADS_DEVELOPER_TOKEN": "mock-dev-token"}):
            mock_creds = MagicMock(spec=credentials.Credentials)
            mock_get_credentials.return_value = mock_creds

            client = google_ads_getter.get_google_ads_client("12345")

            mock_get_credentials.assert_called_once_with(
                scopes=["https://www.googleapis.com/auth/adwords"],
                service_name="Google Ads",
                force_user_creds_env="GOOGLE_ADS_FORCE_USER_CREDS"
            )
            mock_google_ads_client_cls.assert_called_once_with(
                mock_creds,
                login_customer_id="12345",
                developer_token="mock-dev-token",
                use_proto_plus=True,
            )
            self.assertEqual(client, mock_google_ads_client_cls.return_value)

    @patch.dict('agentic_dsta.tools.auth_utils.os.environ', {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "mock-dev-token",
        "GOOGLE_ADS_FORCE_USER_CREDS": "true"
    }, clear=True)
    @patch('agentic_dsta.tools.google_ads.google_ads_client.google.ads.googleads.client.GoogleAdsClient')
    @patch('agentic_dsta.tools.auth_utils.get_user_credentials_from_secret')
    def test_get_google_ads_client_forced_user(self, mock_get_user_creds, mock_google_ads_client_cls):
            mock_creds = MagicMock(spec=credentials.Credentials)
            mock_get_user_creds.return_value = mock_creds

            client = google_ads_getter.get_google_ads_client("12345")

            # Check that get_user_credentials_from_secret was called
            mock_get_user_creds.assert_called_once_with(
                ["https://www.googleapis.com/auth/adwords"],
                "Google Ads"
            )

            mock_google_ads_client_cls.assert_called_once_with(
                mock_creds,
                login_customer_id="12345",
                developer_token="mock-dev-token",
                use_proto_plus=True,
            )
            self.assertEqual(client, mock_google_ads_client_cls.return_value)

    @patch('agentic_dsta.tools.auth_utils.get_credentials', return_value=None)
    def test_get_google_ads_client_creds_fail(self, mock_get_credentials):
        with mock.patch.dict(os.environ, {"GOOGLE_ADS_DEVELOPER_TOKEN": "mock-dev-token"}):
            client = google_ads_getter.get_google_ads_client("12345")
            self.assertIsNone(client)

    @patch('agentic_dsta.tools.google_ads.google_ads_client.google.ads.googleads.client.GoogleAdsClient')
    @patch('agentic_dsta.tools.auth_utils.get_credentials')
    def test_get_google_ads_client_exception(self, mock_get_credentials, mock_google_ads_client_cls):
         with mock.patch.dict(os.environ, {"GOOGLE_ADS_DEVELOPER_TOKEN": "mock-dev-token"}):
            mock_creds = MagicMock(spec=credentials.Credentials)
            mock_get_credentials.return_value = mock_creds
            mock_google_ads_client_cls.side_effect = GoogleAdsException(None, None, MagicMock(), "request_id")
            client = google_ads_getter.get_google_ads_client("12345")
            self.assertIsNone(client)

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_get_campaign_details(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client
        mock_row = MagicMock()
        mock_row.campaign._pb = MagicMock()
        mock_ga_service.search_stream.return_value = [MagicMock(results=[mock_row])]
        with patch('agentic_dsta.tools.google_ads.google_ads_getter.MessageToDict', return_value={'id': 'test_campaign_id'}) as mock_msg_to_dict:
            result = google_ads_getter.get_google_ads_campaign_details("12345", "test_campaign_id")
        self.assertIn('id', result)

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_get_campaign_details_not_found(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client
        mock_ga_service.search_stream.return_value = [MagicMock(results=[])]
        with self.assertRaises(ValueError):
            google_ads_getter.get_google_ads_campaign_details("12345", "test_campaign_id")

    # ... Keep other tests as they are, as they mock get_google_ads_client, not the creds part ...

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_search_geo_target_constants(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_gtc_service = MagicMock()
        mock_client.get_service.return_value = mock_gtc_service
        mock_get_google_ads_client.return_value = mock_client
        mock_suggestion = MagicMock()
        mock_suggestion.geo_target_constant._pb = MagicMock()
        mock_gtc_service.suggest_geo_target_constants.return_value = MagicMock(geo_target_constant_suggestions=[mock_suggestion])
        with patch('agentic_dsta.tools.google_ads.google_ads_getter.MessageToDict', return_value={'resourceName': 'geoTargetConstants/1023191'}) as mock_msg_to_dict:
            result = google_ads_getter.search_google_ads_geo_target_constants("12345", "New York")
        self.assertIn('suggestions', result)
        self.assertEqual(len(result['suggestions']), 1)

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
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
        with patch('agentic_dsta.tools.google_ads.google_ads_getter.MessageToDict', side_effect=[{'location': {'geoTargetConstant': 'geoTargetConstants/2840'}}, {'location': {'geoTargetConstant': 'geoTargetConstants/1023191'}}]) as mock_msg_to_dict:
            result = google_ads_getter.get_google_ads_geo_targets("12345", "test_campaign_id")
        self.assertIn("campaign_targets", result)
        self.assertIn("ad_group_targets", result)
        self.assertEqual(len(result['campaign_targets']), 1)
        self.assertEqual(len(result['ad_group_targets']['adgroup1']), 1)

    def test_google_ads_getter_toolset(self):
        toolset = google_ads_getter.GoogleAdsGetterToolset()
        tools = asyncio.run(toolset.get_tools())
        self.assertEqual(len(tools), 6)

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_list_shared_budgets_success(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client
        mock_row = MagicMock()
        mock_row.campaign_budget._pb = MagicMock()
        mock_ga_service.search_stream.return_value = [MagicMock(results=[mock_row])]
        with patch('agentic_dsta.tools.google_ads.google_ads_getter.MessageToDict', return_value={'id': 'budget1'}) as mock_msg_to_dict:
            result = google_ads_getter.list_google_ads_shared_budgets("12345")
        self.assertIn('shared_budgets', result)
        self.assertEqual(len(result['shared_budgets']), 1)
        self.assertEqual(result['shared_budgets'][0]['id'], 'budget1')

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_get_specific_budget_success(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client
        mock_row = MagicMock()
        mock_row.campaign_budget._pb = MagicMock()
        mock_ga_service.search_stream.return_value = [MagicMock(results=[mock_row])]
        
        with patch('agentic_dsta.tools.google_ads.google_ads_getter.MessageToDict', return_value={'id': 'budget1', 'resource_name': 'customers/123/campaignBudgets/456'}) as mock_msg_to_dict:
            result = google_ads_getter.list_google_ads_shared_budgets("12345", budget_resource_name="customers/123/campaignBudgets/456")
            
        self.assertIn('shared_budgets', result)
        self.assertEqual(len(result['shared_budgets']), 1)
        self.assertEqual(result['shared_budgets'][0]['resource_name'], 'customers/123/campaignBudgets/456')
        
        args, kwargs = mock_ga_service.search_stream.call_args
        self.assertIn("campaign_budget.resource_name = 'customers/123/campaignBudgets/456'", kwargs['query'])

    @patch('agentic_dsta.tools.google_ads.google_ads_getter.get_google_ads_client')
    def test_list_shared_budgets_none(self, mock_get_google_ads_client):
        mock_client = MagicMock()
        mock_ga_service = MagicMock()
        mock_client.get_service.return_value = mock_ga_service
        mock_get_google_ads_client.return_value = mock_client
        mock_ga_service.search_stream.return_value = [MagicMock(results=[])]
        result = google_ads_getter.list_google_ads_shared_budgets("12345")
        self.assertEqual(result, {'shared_budgets': []})

if __name__ == '__main__':
    unittest.main()
