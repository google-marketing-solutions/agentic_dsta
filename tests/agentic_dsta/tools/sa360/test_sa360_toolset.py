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
from unittest import mock
import sys
from agentic_dsta.tools.sa360 import sa360_toolset
from googleapiclient.errors import HttpError

MagicMock = mock.MagicMock
patch = mock.patch

class TestSA360Toolset(unittest.TestCase):

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service')
    def test_get_campaign_details_sheet_success(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_sheet = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheet

        mock_result = {
            'values': [
                ['Campaign ID', 'Name', 'Campaign status'],
                ['123', 'Campaign 1', 'ENABLED'],
                ['456', 'Campaign 2', 'PAUSED']
            ]
        }
        mock_sheet.values.return_value.get.return_value.execute.return_value = mock_result

        result = sa360_toolset.get_sa360_campaign_details_sheet('123', 'sheet_id', 'sheet_name')
        self.assertEqual(result, {'Campaign ID': '123', 'Name': 'Campaign 1', 'Campaign status': 'ENABLED'})

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service', return_value=None)
    def test_get_campaign_details_sheet_no_service(self, mock_get_service):
        with self.assertRaisesRegex(RuntimeError, "Failed to get Google Sheets service"):
            sa360_toolset.get_sa360_campaign_details_sheet('123', 'sheet_id', 'sheet_name')

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service')
    def test_get_campaign_details_sheet_not_found(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_sheet = MagicMock()
        mock_service.spreadsheets.return_value = mock_sheet

        mock_result = {
            'values': [
                ['Campaign ID', 'Name', 'Campaign status'],
                ['456', 'Campaign 2', 'PAUSED']
            ]
        }
        mock_sheet.values.return_value.get.return_value.execute.return_value = mock_result

        with self.assertRaisesRegex(ValueError, "Campaign with ID '123' not found"):
            sa360_toolset.get_sa360_campaign_details_sheet('123', 'sheet_id', 'sheet_name')

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service')
    def test_get_campaign_details_sheet_exception(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_sheet = MagicMock()

        # Make execute raise HttpError
        mock_resp = MagicMock()
        mock_resp.status = 500
        error = HttpError(mock_resp, b'Error')
        mock_sheet.values.return_value.get.return_value.execute.side_effect = error
        mock_service.spreadsheets.return_value = mock_sheet

        with self.assertRaisesRegex(RuntimeError, "Failed to fetch campaign details"):
            sa360_toolset.get_sa360_campaign_details_sheet('123', 'sheet_id', 'sheet_name')

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sa360_campaign_details_sheet')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sa360_campaign_details')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.compare_campaign_data', return_value=True)
    @patch('agentic_dsta.tools.sa360.sa360_toolset._update_campaign_property')
    def test_update_campaign_status_success(self, mock_update_prop, mock_compare, mock_get_api_details, mock_get_sheet_details, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_get_sheet_details.return_value = {'Campaign ID': '123', 'Name': 'Campaign 1', 'Campaign status': 'PAUSED'}
        mock_get_api_details.return_value = {"campaign": {"id": "123"}}

        # Return value from the final _update_campaign_property call
        update_return = {"success": "Campaign '123' Campaign status updated to 'ENABLED'."}
        mock_update_prop.side_effect = [None, update_return]

        result = sa360_toolset.update_sa360_campaign_status('123', 'ENABLED', 'sheet_id', 'sheet_name', '1234567890')
        self.assertEqual(result, update_return)
        mock_update_prop.assert_any_call('123', 'Campaign status', 'ENABLED', 'sheet_id', 'sheet_name')

    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sheets_service')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sa360_campaign_details_sheet')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.get_sa360_campaign_details')
    @patch('agentic_dsta.tools.sa360.sa360_toolset.compare_campaign_data', return_value=True)
    @patch('agentic_dsta.tools.sa360.sa360_toolset._update_campaign_property')
    def test_update_campaign_status_not_found(self, mock_update_prop, mock_compare, mock_get_api_details, mock_get_sheet_details, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_get_sheet_details.side_effect = ValueError("Campaign with ID '789' not found")
        mock_get_api_details.return_value = {"campaign": {"id": "789"}}

        with self.assertRaisesRegex(ValueError, "Campaign with ID '789' not found"):
            sa360_toolset.update_sa360_campaign_status('789', 'ENABLED', 'sheet_id', 'sheet_name', '1234567890')

if __name__ == '__main__':
    unittest.main()