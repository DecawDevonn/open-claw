"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class StorageBackend(ABC):
    """Abstract interface for all storage backends."""

    # --- Users ---

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def save_user(self, user: Dict) -> None:
        ...

    @abstractmethod
    def list_users(self) -> List[Dict]:
        ...

    # --- Agents ---

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def save_agent(self, agent: Dict) -> None:
        ...

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        ...

    @abstractmethod
    def list_agents(self) -> List[Dict]:
        ...

    # --- Tasks ---

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict]:
        ...

    @abstractmethod
    def save_task(self, task: Dict) -> None:
        ...

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        ...

    @abstractmethod
    def list_tasks(self) -> List[Dict]:
        ...

    # --- Token revocation ---

    @abstractmethod
    def revoke_token(self, jti: str) -> None:
        ...

    @abstractmethod
    def is_token_revoked(self, jti: str) -> bool:
        ...
