"""Storage backend factory for OpenClaw.

Usage::

    from storage import get_storage

    store = get_storage(mongo_url="mongodb://localhost:27017")  # MongoStorage
    store = get_storage()                                       # InMemoryStorage
"""

import logging
from typing import Optional

from .base import StorageBackend
from .memory import InMemoryStorage

logger = logging.getLogger(__name__)


def get_storage(mongo_url: Optional[str] = None, db_name: str = "openclaw") -> StorageBackend:
    """Return the appropriate storage backend.

    If *mongo_url* is provided the MongoDB-backed ``MongoStorage`` is returned.
    Otherwise an ephemeral ``InMemoryStorage`` is used (suitable for tests and
    single-process development).
    """
    if mongo_url:
        try:
            from .mongo import MongoStorage  # pymongo is an optional dependency
            logger.info("Using MongoStorage backend (url=%s)", mongo_url)
            return MongoStorage(uri=mongo_url, db_name=db_name)
        except ImportError:
            logger.warning(
                "MONGO_URL is set but pymongo is not installed; "
                "falling back to InMemoryStorage."
            )
    logger.info("Using InMemoryStorage backend")
    return InMemoryStorage()


__all__ = ["StorageBackend", "InMemoryStorage", "get_storage"]
