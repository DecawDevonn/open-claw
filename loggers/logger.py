"""Structured logging helpers for OpenClaw.

Wraps the stdlib ``logging`` module to provide a consistent, named-logger
interface used throughout the OpenClaw packages.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

_DEFAULT_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=_DEFAULT_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Return a named stdlib logger, optionally overriding the log level."""
    log = logging.getLogger(name)
    if level:
        log.setLevel(level.upper())
    return log


_root = get_logger("openclaw")


def log_info(message: str, *args, **kwargs) -> None:
    """Log at INFO level on the root ``openclaw`` logger."""
    _root.info(message, *args, **kwargs)


def log_warning(message: str, *args, **kwargs) -> None:
    """Log at WARNING level on the root ``openclaw`` logger."""
    _root.warning(message, *args, **kwargs)


def log_error(message: str, *args, **kwargs) -> None:
    """Log at ERROR level on the root ``openclaw`` logger."""
    _root.error(message, *args, **kwargs)


def log_debug(message: str, *args, **kwargs) -> None:
    """Log at DEBUG level on the root ``openclaw`` logger."""
    _root.debug(message, *args, **kwargs)
