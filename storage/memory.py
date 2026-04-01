"""In-memory storage backend (development / testing)."""

from typing import Dict, List, Optional
from .base import StorageBackend


class MemoryStorage(StorageBackend):
    """Dict-backed, in-process storage. Not suitable for multi-process deployments."""

    def __init__(self) -> None:
        self._users: Dict[str, Dict] = {}
        self._agents: Dict[str, Dict] = {}
        self._tasks: Dict[str, Dict] = {}
        self._revoked_tokens: set = set()

    # --- Users ---

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        for user in self._users.values():
            if user['username'] == username:
                return user
        return None

    def save_user(self, user: Dict) -> None:
        self._users[user['id']] = user

    def list_users(self) -> List[Dict]:
        return list(self._users.values())

    # --- Agents ---

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self._agents.get(agent_id)

    def save_agent(self, agent: Dict) -> None:
        self._agents[agent['id']] = agent

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
        self._tasks[task['id']] = task

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def list_tasks(self) -> List[Dict]:
        return list(self._tasks.values())

    # --- Token revocation ---

    def revoke_token(self, jti: str) -> None:
        self._revoked_tokens.add(jti)

    def is_token_revoked(self, jti: str) -> bool:
        return jti in self._revoked_tokens
