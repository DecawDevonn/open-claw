"""Storage package."""

from storage.base import StorageBackend
from storage.mongo import MongoStorage

__all__ = ["StorageBackend", "MongoStorage"]
