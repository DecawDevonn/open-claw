import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict
from flask import Flask, request, g


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging(app: Flask, level: str = "INFO") -> None:
    """Configure structured JSON logging for the app."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    app.logger.handlers = [handler]
    app.logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def setup_request_logging(app: Flask) -> None:
    """Set up request/response logging middleware."""

    @app.before_request
    def before_request():
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        duration = time.time() - g.start_time if hasattr(g, 'start_time') else None
        log_entry = {
            "type": "request",
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
        }
        if duration is not None:
            log_entry["duration_ms"] = round(duration * 1000, 2)
        app.logger.info(json.dumps(log_entry))
        return response
