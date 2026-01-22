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
import logging
import os
import sys
import json
import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "code_function": record.funcName,
            "code_line": record.lineno,
        }
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        excluded_keys = [
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'msg', 'name',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'thread', 'threadName'
        ]
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in log_record and k not in excluded_keys
        }
        log_record.update(extra_fields)

        return json.dumps(log_record)

def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger = logging.getLogger('agentic_dsta')

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    print(f"Logging setup complete for 'agentic_dsta' with level {log_level}", file=sys.stderr)

