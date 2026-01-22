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
import os
import sys

# Ensure agentic_dsta is importable
sys.path.append(os.getcwd())

import agentic_dsta.main

# Mock uvicorn and get_fast_api_app at the class level to affect imports
@mock.patch('agentic_dsta.main.uvicorn')
@mock.patch('google.adk.cli.fast_api.get_fast_api_app') # Correct target
class TestMain(unittest.TestCase):

    @mock.patch.dict(os.environ, {'PORT': '8000'})
    def test_main(self, mock_get_fast_api_app, mock_uvicorn):
        mock_app = mock.MagicMock()
        with mock.patch.object(agentic_dsta.main, 'app', mock_app):
            agentic_dsta.main.main()

        mock_uvicorn.run.assert_called_once_with(mock_app, host='0.0.0.0', port=8000)

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_main_default_port(self, mock_get_fast_api_app, mock_uvicorn):
        mock_app = mock.MagicMock()
        with mock.patch.object(agentic_dsta.main, 'app', mock_app):
            agentic_dsta.main.main()

        mock_uvicorn.run.assert_called_once_with(mock_app, host='0.0.0.0', port=8080)

if __name__ == '__main__':
    unittest.main()
