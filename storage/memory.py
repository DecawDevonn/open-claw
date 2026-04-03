"""In-memory storage backend for development and testing."""

import copy
from typing import Dict, List, Optional

from .base import StorageBackend


class MemoryStorage(StorageBackend):
    """Stores all data in plain Python dicts.  Not persistent across restarts."""

    def __init__(self) -> None:
        self._users: Dict[str, Dict] = {}
        self._agents: Dict[str, Dict] = {}
        self._tasks: Dict[str, Dict] = {}
        self._revoked_tokens: set = set()

    # --- Users ---

    def get_user(self, user_id: str) -> Optional[Dict]:
        return copy.deepcopy(self._users.get(user_id))

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        for user in self._users.values():
            if user.get("username") == username:
                return copy.deepcopy(user)
        return None

    def save_user(self, user: Dict) -> None:
        self._users[user["id"]] = copy.deepcopy(user)

    def list_users(self) -> List[Dict]:
        return [copy.deepcopy(u) for u in self._users.values()]

    # --- Agents ---

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return copy.deepcopy(self._agents.get(agent_id))

    def save_agent(self, agent: Dict) -> None:
        self._agents[agent["id"]] = copy.deepcopy(agent)

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def list_agents(self) -> List[Dict]:
        return [copy.deepcopy(a) for a in self._agents.values()]

    # --- Tasks ---

    def get_task(self, task_id: str) -> Optional[Dict]:
        return copy.deepcopy(self._tasks.get(task_id))

    def save_task(self, task: Dict) -> None:
        self._tasks[task["id"]] = copy.deepcopy(task)

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def list_tasks(self) -> List[Dict]:
        return [copy.deepcopy(t) for t in self._tasks.values()]

    # --- Token revocation ---

    def revoke_token(self, jti: str) -> None:
        self._revoked_tokens.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        return jti in self._revoked_tokens
