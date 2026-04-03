"""OpenClaw storage package.

Exposes the abstract StorageBackend and the in-memory / MongoDB implementations.
"""

from .base import StorageBackend
from .memory import MemoryStorage

__all__ = ["StorageBackend", "MemoryStorage"]

try:
    from .mongo import MongoStorage
    __all__.append("MongoStorage")
except ImportError:
    pass  # pymongo not installed — MongoDB backend unavailable
