"""Abstract base class for OpenClaw storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class StorageBackend(ABC):
    """Interface that every storage backend must implement."""

    # --- Users ---

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Retrieve a user by ID. Returns None if not found."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Retrieve a user by username. Returns None if not found."""

    @abstractmethod
    def save_user(self, user: Dict) -> None:
        """Persist (insert or update) a user document."""

    @abstractmethod
    def list_users(self) -> List[Dict]:
        """Return all users."""

    # --- Agents ---

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Retrieve an agent by ID. Returns None if not found."""

    @abstractmethod
    def save_agent(self, agent: Dict) -> None:
        """Persist (insert or update) an agent document."""

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent. Returns True if deleted, False if not found."""

    @abstractmethod
    def list_agents(self) -> List[Dict]:
        """Return all agents."""

    # --- Tasks ---

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Retrieve a task by ID. Returns None if not found."""

    @abstractmethod
    def save_task(self, task: Dict) -> None:
        """Persist (insert or update) a task document."""

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete a task. Returns True if deleted, False if not found."""

    @abstractmethod
    def list_tasks(self) -> List[Dict]:
        """Return all tasks."""

    # --- Token revocation ---

    @abstractmethod
    def revoke_token(self, jti: str) -> None:
        """Mark a JWT token as revoked."""

    @abstractmethod
    def is_token_revoked(self, jti: str) -> bool:
        """Return True if the given JWT token has been revoked."""
