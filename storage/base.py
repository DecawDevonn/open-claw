"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class StorageBackend(ABC):
    """Abstract storage interface for users, agents, tasks, and token revocation."""

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Return user dict by ID, or None."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Return user dict by username, or None."""

    @abstractmethod
    def save_user(self, user: Dict) -> None:
        """Insert or update a user record."""

    @abstractmethod
    def list_users(self) -> List[Dict]:
        """Return all users."""

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Return agent dict by ID, or None."""

    @abstractmethod
    def save_agent(self, agent: Dict) -> None:
        """Insert or update an agent record."""

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent by ID. Returns True if deleted, False if not found."""

    @abstractmethod
    def list_agents(self) -> List[Dict]:
        """Return all agents."""

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Return task dict by ID, or None."""

    @abstractmethod
    def save_task(self, task: Dict) -> None:
        """Insert or update a task record."""

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""

    @abstractmethod
    def list_tasks(self) -> List[Dict]:
        """Return all tasks."""

    @abstractmethod
    def revoke_token(self, jti: str) -> None:
        """Mark a JWT (by jti) as revoked."""

    @abstractmethod
    def is_token_revoked(self, jti: str) -> bool:
        """Return True if the JWT jti has been revoked."""
