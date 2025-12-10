import importlib
import os
import unittest
from unittest import mock

from agentic_dsta import main

patch = mock.patch
MagicMock = mock.MagicMock


class TestMain(unittest.TestCase):
  @patch("agentic_dsta.main.uvicorn")
  @patch("agentic_dsta.main.get_fast_api_app")
  @patch.dict(os.environ, {"PORT": "8000"})
  def test_main(self, mock_get_fast_api_app, mock_uvicorn):
    # Mock the app object
    mock_app = MagicMock()
    mock_get_fast_api_app.return_value = mock_app

    # Call main
    main.main()

    # Assertions
    mock_uvicorn.run.assert_called_once_with(
        main.app, host="0.0.0.0", port=8000
        )

  @patch("agentic_dsta.main.uvicorn")
  @patch("agentic_dsta.main.get_fast_api_app")
  @patch.dict(os.environ, {}, clear=True)
  def test_main_default_port(self, mock_get_fast_api_app, mock_uvicorn):
    # Mock the app object
    mock_app = MagicMock()
    mock_get_fast_api_app.return_value = mock_app

    # Call main
    main.main()

    # Assertions
    mock_uvicorn.run.assert_called_once_with(
        main.app, host="0.0.0.0", port=8080
    )

if __name__ == "__main__":
  unittest.main()
