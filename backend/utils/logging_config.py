"""Structured JSON logging setup for the backend."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    RESERVED = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        obj: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Attach any extra fields passed via extra={...}
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                obj[key] = value

        if record.exc_info:
            obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(obj, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger with JSON output to stdout.
    Call once at app startup (backend/main.py).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any default handlers (e.g. uvicorn's)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for name in ("googleapiclient.discovery_cache", "urllib3.connectionpool"):
        logging.getLogger(name).setLevel(logging.WARNING)
