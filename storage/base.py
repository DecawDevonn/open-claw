"""Abstract base class for all OpenClaw storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class StorageBackend(ABC):
    """Defines the interface that every storage backend must implement."""

    # --- Users ---

    @abstractmethod
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Return the user dict for *user_id*, or None if not found."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Return the user dict for *username*, or None if not found."""

    @abstractmethod
    def save_user(self, user: Dict) -> None:
        """Persist *user* (insert or replace by ``user['id']``)."""

    @abstractmethod
    def list_users(self) -> List[Dict]:
        """Return all users."""

    # --- Agents ---

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Return the agent dict for *agent_id*, or None if not found."""

    @abstractmethod
    def save_agent(self, agent: Dict) -> None:
        """Persist *agent* (insert or replace by ``agent['id']``)."""

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent by *agent_id*. Returns True if it existed."""

    @abstractmethod
    def list_agents(self) -> List[Dict]:
        """Return all agents."""

    # --- Tasks ---

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Return the task dict for *task_id*, or None if not found."""

    @abstractmethod
    def save_task(self, task: Dict) -> None:
        """Persist *task* (insert or replace by ``task['id']``)."""

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete task by *task_id*. Returns True if it existed."""

    @abstractmethod
    def list_tasks(self) -> List[Dict]:
        """Return all tasks."""

    # --- Token revocation ---

    @abstractmethod
    def revoke_token(self, jti: str) -> None:
        """Mark a JWT JTI as revoked."""

    @abstractmethod
    def is_token_revoked(self, jti: str) -> bool:
        """Return True if the JTI has been revoked."""

    # --- Leads ---

    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[Dict]:
        """Return the lead dict for *lead_id*, or None if not found."""

    @abstractmethod
    def save_lead(self, lead: Dict) -> None:
        """Persist *lead* (insert or replace by ``lead['id']``)."""

    @abstractmethod
    def delete_lead(self, lead_id: str) -> bool:
        """Delete lead by *lead_id*. Returns True if it existed."""

    @abstractmethod
    def list_leads(self) -> List[Dict]:
        """Return all leads."""

    # --- Analytics events ---

    @abstractmethod
    def save_event(self, event: Dict) -> None:
        """Persist an analytics *event* (insert only; events are immutable)."""

    @abstractmethod
    def list_events(self) -> List[Dict]:
        """Return all analytics events."""

    # --- Audit log ---

    @abstractmethod
    def save_audit_entry(self, entry: Dict) -> None:
        """Persist an audit log *entry*."""

    @abstractmethod
    def list_audit_entries(self, limit: int = 200) -> List[Dict]:
        """Return up to *limit* most-recent audit log entries."""
