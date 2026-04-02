"""Monitoring / observability helpers.

Initialises Sentry (if configured) and exposes a ``health_payload()`` helper
used by the ``/api/health`` endpoint to include integration status.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def init_monitoring(sentry_dsn: Optional[str] = None) -> bool:
    """Initialise Sentry SDK if a DSN is provided.

    Returns True when Sentry was successfully initialised, False otherwise.
    Safe to call when ``sentry-sdk`` is not installed (import failure is
    caught and logged as a warning).
    """
    if not sentry_dsn:
        logger.debug("SENTRY_DSN not set — Sentry will not be initialised.")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.2,
            send_default_pii=False,
        )
        logger.info("Sentry initialised.")
        return True
    except ImportError:
        logger.warning("sentry-sdk is not installed. Install it with: pip install sentry-sdk")
        return False
    except Exception as exc:
        logger.warning("Failed to initialise Sentry: %s", exc)
        return False


def health_payload(configured_services: List[str]) -> Dict[str, Any]:
    """Return a structured health dict suitable for the /api/health endpoint."""
    return {
        "status": "healthy",
        "integrations": {
            "configured": configured_services,
            "count": len(configured_services),
        },
    }
