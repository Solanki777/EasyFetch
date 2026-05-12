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
    Configure the root logger with JSON output to stderr.
    Call once at app startup (backend/main.py).
    """
    # Use stderr as it's often less buffered than stdout on Windows
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)

    # Instead of clearing all handlers (which might break uvicorn's own logging),
    # we just ensure our handler is present.
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stderr for h in root.handlers):
        root.addHandler(handler)

    # Silence noisy third-party loggers
    for name in ("googleapiclient.discovery_cache", "urllib3.connectionpool", "openai", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)
