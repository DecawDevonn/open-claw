"""In-process, ephemeral storage backend (no external dependencies).

Suitable for tests and single-process development runs.  Data is lost on
process restart; swap for ``MongoStorage`` in production.
"""

from typing import Dict, List, Optional

from .base import StorageBackend


class InMemoryStorage(StorageBackend):
    """Stores all data in plain Python dicts (thread-unsafe by design — use
    a real backend for concurrent production workloads)."""

    def __init__(self) -> None:
        self._users: Dict[str, Dict] = {}
        self._agents: Dict[str, Dict] = {}
        self._tasks: Dict[str, Dict] = {}
        self._revoked: set = set()
        self._leads: Dict[str, Dict] = {}
        self._events: List[Dict] = []
        self._audit: List[Dict] = []

    # --- Users ---

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        for user in self._users.values():
            if user.get("username") == username:
                return user
        return None

    def save_user(self, user: Dict) -> None:
        self._users[user["id"]] = user

    def list_users(self) -> List[Dict]:
        return list(self._users.values())

    # --- Agents ---

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self._agents.get(agent_id)

    def save_agent(self, agent: Dict) -> None:
        self._agents[agent["id"]] = agent

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def list_agents(self) -> List[Dict]:
        return list(self._agents.values())

    # --- Tasks ---

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self._tasks.get(task_id)

    def save_task(self, task: Dict) -> None:
        self._tasks[task["id"]] = task

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def list_tasks(self) -> List[Dict]:
        return list(self._tasks.values())

    # --- Token revocation ---

    def revoke_token(self, jti: str) -> None:
        self._revoked.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        return jti in self._revoked

    # --- Leads ---

    def get_lead(self, lead_id: str) -> Optional[Dict]:
        return self._leads.get(lead_id)

    def save_lead(self, lead: Dict) -> None:
        self._leads[lead["id"]] = lead

    def delete_lead(self, lead_id: str) -> bool:
        if lead_id in self._leads:
            del self._leads[lead_id]
            return True
        return False

    def list_leads(self) -> List[Dict]:
        return list(self._leads.values())

    # --- Analytics events ---

    def save_event(self, event: Dict) -> None:
        self._events.append(event)

    def list_events(self) -> List[Dict]:
        return list(self._events)

    # --- Audit log ---

    def save_audit_entry(self, entry: Dict) -> None:
        self._audit.append(entry)

    def list_audit_entries(self, limit: int = 200) -> List[Dict]:
        return list(self._audit[-limit:])
