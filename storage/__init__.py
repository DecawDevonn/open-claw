"""Storage package — exports the backend abstraction and factory."""

from typing import Optional

from .base import StorageBackend
from .memory import MemoryStorage
from .mongo import MongoStorage

__all__ = ['StorageBackend', 'MemoryStorage', 'MongoStorage', 'get_storage']


def get_storage(uri: Optional[str] = None) -> StorageBackend:
    """Return the appropriate storage backend.

    If *uri* is provided (non-empty), returns a :class:`MongoStorage` instance
    connected to that URI.  Otherwise returns an in-memory :class:`MemoryStorage`.
    """
    if uri:
        return MongoStorage(uri)
    return MemoryStorage()
