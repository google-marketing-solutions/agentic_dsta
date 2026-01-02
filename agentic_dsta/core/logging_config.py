# agentic_dsta/core/logging_config.py
import logging
import os
import sys
import json
import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.datetime.utcnow().isoformat() + 'Z',
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

    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


    print(f"Logging setup complete for 'agentic_dsta' with level {log_level}", file=sys.stderr)

# Example usage in other modules:
# import logging
# from agentic_dsta.core.logging_config import setup_logging
#
# setup_logging()
# logger = logging.getLogger(__name__)
# logger.info("Something happened", extra={'customer_id': '123'})
