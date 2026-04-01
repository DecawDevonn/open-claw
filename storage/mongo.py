"""MongoDB-backed storage backend."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pymongo
from pymongo.collection import Collection

from .base import StorageBackend


class MongoStorage(StorageBackend):
    """Persists data in MongoDB via pymongo."""

    # explicit attributes help mypy and readers
    _client: pymongo.MongoClient
    _users: Collection
    _agents: Collection
    _tasks: Collection
    _revoked_tokens: Collection

    def __init__(self, uri: str, db_name: str = 'open-claw') -> None:
        # Keep a typed instance attribute for the client so mypy is satisfied
        # and the client is available for future use or debugging.
        self._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = self._client[db_name]
        self._users = db['users']
        self._agents = db['agents']
        self._tasks = db['tasks']
        self._revoked_tokens = db['revoked_tokens']

    # --- Helpers ---

    @staticmethod
    def _to_dict(doc: Any) -> Optional[Dict]:
        if doc is None:
            return None
        result = {}
        for key, value in doc.items():
            if key == '_id':
                continue
            # Convert ObjectId (and any other BSON types with __str__) to plain strings
            try:
                from bson import ObjectId
                if isinstance(value, ObjectId):
                    value = str(value)
            except ImportError:
                pass
            result[key] = value
        return result

    # --- Users ---

    def get_user(self, user_id: str) -> Optional[Dict]:
        return self._to_dict(self._users.find_one({'id': user_id}))

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        return self._to_dict(self._users.find_one({'username': username}))

    def save_user(self, user: Dict) -> None:
        self._users.replace_one({'id': user['id']}, user, upsert=True)

    def list_users(self) -> List[Dict]:
        return [self._to_dict(d) for d in self._users.find()]

    # --- Agents ---

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self._to_dict(self._agents.find_one({'id': agent_id}))

    def save_agent(self, agent: Dict) -> None:
        self._agents.replace_one({'id': agent['id']}, agent, upsert=True)

    def delete_agent(self, agent_id: str) -> bool:
        result = self._agents.delete_one({'id': agent_id})
        return result.deleted_count > 0

    def list_agents(self) -> List[Dict]:
        return [self._to_dict(d) for d in self._agents.find()]

    # --- Tasks ---

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self._to_dict(self._tasks.find_one({'id': task_id}))

    def save_task(self, task: Dict) -> None:
        self._tasks.replace_one({'id': task['id']}, task, upsert=True)

    def delete_task(self, task_id: str) -> bool:
        result = self._tasks.delete_one({'id': task_id})
        return result.deleted_count > 0

    def list_tasks(self) -> List[Dict]:
        return [self._to_dict(d) for d in self._tasks.find()]

    # --- Token revocation ---

    def revoke_token(self, jti: str) -> None:
        self._revoked_tokens.update_one(
            {'jti': jti},
            {'$setOnInsert': {'jti': jti, 'created_at': datetime.utcnow()}},
            upsert=True,
        )

    def is_token_revoked(self, jti: str) -> bool:
        return self._revoked_tokens.find_one({'jti': jti}) is not None
