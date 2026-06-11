"""
Structured JSON logging configuration for production-grade observability.

Usage (in main.py):
    from backend.app.core.logging_config import configure_logging
    configure_logging()

All loggers throughout the application will automatically emit JSON-formatted
lines with consistent fields: timestamp, level, logger, message, and any
bound extra context fields.
"""
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that serializes log records as single-line JSON objects.

    Each log record is emitted with the following fields:
    - timestamp: ISO-8601 UTC timestamp string
    - level: log level name (INFO, WARNING, ERROR, etc.)
    - logger: originating logger name
    - message: human-readable log message
    - module: source module name
    - line: source line number
    - *extra: any additional keyword arguments passed to the log call
    """

    RESERVED_ATTRS = {
        "args", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message",
        "module", "msecs", "msg", "name", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "taskName",
        "thread", "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        # Use datetime for microsecond precision — time.strftime('%f') is unsupported on Windows
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        log_object: Dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "line": record.lineno,
        }

        # Attach any extra fields injected via logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                log_object[key] = value

        # Attach exception info if present
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_object, default=str)


class RequestTimingFilter(logging.Filter):
    """Injects a relative timestamp (seconds since process start) into every record."""
    _start = time.time()

    def filter(self, record: logging.LogRecord) -> bool:
        record.uptime = round(time.time() - self._start, 3)
        return True


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """
    Configure the root logger with consistent formatting for all modules.

    Args:
        level:       Minimum log severity (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        json_output: If True, emit JSON lines. If False, emit human-readable text
                     (useful for local development).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any handlers already attached (e.g. by basicConfig elsewhere)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestTimingFilter())

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    root_logger.addHandler(handler)

    # Suppress overly verbose library loggers
    for noisy_logger in ("httpx", "httpcore", "asyncio", "urllib3", "openai"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
