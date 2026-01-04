"""Tests for sa360_toolset.
This class takes care of testing all the functions in sa360_toolset.py"""

import unittest
from unittest import mock

from agentic_dsta.sa360_agent.tools import sa360_toolset


class Sa360ToolsetTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_sheets_service = mock.MagicMock()
    self.mock_get_sheets_service = self.enter_context(
        mock.patch.object(
            sa360_toolset, "get_sheets_service", autospec=True
        )
    )
    self.mock_get_sheets_service.return_value = self.mock_sheets_service
    self.sheet_id = "dummy_sheet_id"
    self.sheet_name = "Sheet0"

  def test_get_campaign_details_success(self):
    mock_values = [
        ["Campaign ID", "Campaign status", "Budget"],
        ["123", "ENABLED", "100.0"],
        ["456", "PAUSED", "200.0"],
    ]
    self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        "values": mock_values
    }

    result = sa360_toolset.get_campaign_details(
        "123", self.sheet_id, self.sheet_name
    )

    self.assertEqual(
        result, {"Campaign ID": "123", "Campaign status": "ENABLED", "Budget": "100.0"}
    )

  def test_get_campaign_details_not_found(self):
    mock_values = [
        ["Campaign ID", "Campaign status", "Budget"],
        ["123", "ENABLED", "100.0"],
    ]
    self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        "values": mock_values
    }

    result = sa360_toolset.get_campaign_details(
        "999", self.sheet_id, self.sheet_name
    )

    self.assertEqual(result, {"error": "Campaign with ID '999' not found."})

  def test_get_campaign_details_no_data(self):
    self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        "values": []
    }

    result = sa360_toolset.get_campaign_details(
        "123", self.sheet_id, self.sheet_name
    )

    self.assertEqual(result, {"error": "No data found in sheet 'Sheet0'."})

  def test_update_campaign_property_success(self):
    mock_values = [
        ["Campaign ID", "Campaign status"],
        ["123", "ENABLED"],
    ]
    self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
        "values": mock_values
    }

    result = sa360_toolset._update_campaign_property(
        "123", "Campaign status", "PAUSED", self.sheet_id, self.sheet_name
    )

    self.assertEqual(
        result,
        {
            "success": "Campaign '123' Campaign status updated to 'PAUSED'."
        },
    )
    self.mock_sheets_service.spreadsheets().values().update.assert_called_once()

  def test_enable_campaign_calls_update_property(self):
    with mock.patch.object(
        sa360_toolset, "_update_campaign_property", autospec=True
    ) as mock_update:
      sa360_toolset.enable_campaign("123", self.sheet_id, self.sheet_name)
      mock_update.assert_called_once_with(
          "123", "Campaign status", "ENABLED", self.sheet_id, self.sheet_name
      )

  def test_disable_campaign_calls_update_property(self):
    with mock.patch.object(
        sa360_toolset, "_update_campaign_property", autospec=True
    ) as mock_update:
      sa360_toolset.disable_campaign("123", self.sheet_id, self.sheet_name)
      mock_update.assert_called_once_with(
          "123", "Campaign status", "PAUSED", self.sheet_id, self.sheet_name
      )

  def test_update_campaign_geolocation_calls_update_property(self):
    with mock.patch.object(
        sa360_toolset, "_update_campaign_property", autospec=True
    ) as mock_update:
      sa360_toolset.update_campaign_geolocation(
          "123", "New York", self.sheet_id, self.sheet_name
      )
      mock_update.assert_called_once_with(
          "123", "Location", "New York", self.sheet_id, self.sheet_name
      )

  def test_update_campaign_budget_calls_update_property(self):
    with mock.patch.object(
        sa360_toolset, "_update_campaign_property", autospec=True
    ) as mock_update:
      sa360_toolset.update_campaign_budget(
          "123", 150.0, self.sheet_id, self.sheet_name
      )
      mock_update.assert_called_once_with(
          "123", "Budget", 150.0, self.sheet_id, self.sheet_name
      )

  def test_update_campaign_bid_valid_strategy(self):
    with mock.patch.object(
        sa360_toolset, "_update_campaign_property", autospec=True
    ) as mock_update:
      sa360_toolset.update_campaign_bid(
          "123", "Target CPA", self.sheet_id, self.sheet_name
      )
      mock_update.assert_called_once_with(
          "123", "Bid strategy", "Target CPA", self.sheet_id, self.sheet_name
      )

  def test_update_campaign_bid_invalid_strategy(self):
    result = sa360_toolset.update_campaign_bid(
        "123", "Invalid Strategy", self.sheet_id, self.sheet_name
    )

    self.assertIn("error", result)
    self.assertIn("Invalid value", result["error"])

  def test_remove_campaign_geolocation_success(self):
    with mock.patch.object(
        sa360_toolset, "get_campaign_details", autospec=True
    ) as mock_get_details:
      mock_get_details.return_value = {
          "Campaign ID": "123",
          "Customer ID": "cust1",
          "Campaign": "Test Campaign",
      }
      header = [
          "Row Type",
          "Action",
          "Customer ID",
          "Campaign",
          "Location",
          "Associated Campaign ID",
      ]
      self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
          "values": [header]
      }

      result = sa360_toolset.remove_campaign_geolocation(
          "123", "New York", self.sheet_id, self.sheet_name
      )

      self.assertIn("success", result)
      self.mock_sheets_service.spreadsheets().values().append.assert_called_once()

  def test_remove_campaign_geolocation_campaign_not_found(self):
    with mock.patch.object(
        sa360_toolset, "get_campaign_details", autospec=True
    ) as mock_get_details:
      mock_get_details.return_value = {"error": "Campaign not found."}

      result = sa360_toolset.remove_campaign_geolocation(
          "123", "New York", self.sheet_id, self.sheet_name
      )

      self.assertEqual(result, {"error": "Campaign not found."})

  def test_remove_campaign_geolocation_missing_header(self):
    with mock.patch.object(
        sa360_toolset, "get_campaign_details", autospec=True
    ) as mock_get_details:
      mock_get_details.return_value = {"Campaign ID": "123"}
      self.mock_sheets_service.spreadsheets().values().get().execute.return_value = {
          "values": [["Some", "Other", "Header"]]
      }

      result = sa360_toolset.remove_campaign_geolocation(
          "123", "New York", self.sheet_id, self.sheet_name
      )

      self.assertIn("error", result)
      self.assertIn("Sheet must contain", result["error"])

  async def test_sa360_toolset_get_tools(self):
    toolset = sa360_toolset.SA360Toolset()

    tools = await toolset.get_tools()

    self.assertLen(tools, 6)
    tool_names = [tool.func.__name__ for tool in tools]
    self.assertIn("get_campaign_details", tool_names)
    self.assertIn("enable_campaign", tool_names)
    self.assertIn("disable_campaign", tool_names)
    self.assertIn("update_campaign_geolocation", tool_names)
    self.assertIn("update_campaign_budget", tool_names)
    self.assertIn("remove_campaign_geolocation", tool_names)


if __name__ == "__main__":
  unittest.main()
