"""
openclaw_client.py - Reusable API client for the OpenClaw platform.

Provides synchronous methods for all API endpoints with error
handling, retry logic, and optional request/response logging.
"""
import logging
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config, OpenClawConfig

logger = logging.getLogger(__name__)


class OpenClawError(Exception):
    """Raised for API or network errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OpenClawClient:
    """HTTP client for the OpenClaw REST API."""

    def __init__(
        self,
        config: Optional[OpenClawConfig] = None,
        profile: Optional[str] = None,
        log_requests: bool = False,
    ) -> None:
        self._config = config or get_config(profile)
        self._log_requests = log_requests
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        if self._config.api_key:
            session.headers['Authorization'] = f'Bearer {self._config.api_key}'
        session.headers['Content-Type'] = 'application/json'
        session.verify = self._config.verify_ssl
        return session

    def _url(self, path: str) -> str:
        return f"{self._config.base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = self._url(path)
        if self._log_requests:
            logger.debug('%s %s  kwargs=%s', method, url, kwargs)
        start = time.monotonic()
        try:
            response = self._session.request(
                method, url, timeout=self._config.timeout, **kwargs
            )
        except requests.ConnectionError as exc:
            raise OpenClawError(f"Connection failed: {exc}") from exc
        except requests.Timeout as exc:
            raise OpenClawError(f"Request timed out: {exc}") from exc

        elapsed = time.monotonic() - start
        if self._log_requests:
            logger.debug('→ %s  %.2fs', response.status_code, elapsed)

        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise OpenClawError(
                f"API error {response.status_code}: {detail}",
                status_code=response.status_code,
                response=detail,
            )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    # ---- Health ----

    def get_health(self) -> Dict[str, Any]:
        """Check API health."""
        return self._request('GET', '/api/health')

    # ---- Agents ----

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return all agents."""
        return self._request('GET', '/api/agents')  # type: ignore[return-value]

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Return details for a single agent."""
        return self._request('GET', f'/api/agents/{agent_id}')

    def create_agent(
        self,
        name: str,
        agent_type: str = 'generic',
        capabilities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new agent."""
        return self._request('POST', '/api/agents', json={
            'name': name,
            'type': agent_type,
            'capabilities': capabilities or [],
        })

    def update_agent(self, agent_id: str, **fields: Any) -> Dict[str, Any]:
        """Update an agent's fields."""
        return self._request('PUT', f'/api/agents/{agent_id}', json=fields)

    def delete_agent(self, agent_id: str) -> Dict[str, Any]:
        """Delete an agent."""
        return self._request('DELETE', f'/api/agents/{agent_id}')

    def execute_command(self, agent_id: str, command: str, auto_approve: bool = True) -> Dict[str, Any]:
        """Execute a command on a specific agent via the Fortress endpoint."""
        return self._request('POST', f'/api/v1/fortress/agents/{agent_id}/execute', json={
            'command': command,
            'auto_approve': auto_approve,
        })

    # ---- Tasks ----

    def get_tasks(self, status: Optional[str] = None, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return tasks, optionally filtered by status or agent."""
        params: Dict[str, str] = {}
        if status:
            params['status'] = status
        if agent_id:
            params['agent_id'] = agent_id
        return self._request('GET', '/api/tasks', params=params)  # type: ignore[return-value]

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Return a single task."""
        return self._request('GET', f'/api/tasks/{task_id}')

    def create_task(
        self,
        name: str,
        description: str = '',
        agent_id: Optional[str] = None,
        priority: str = 'normal',
    ) -> Dict[str, Any]:
        """Submit a new task."""
        return self._request('POST', '/api/tasks', json={
            'name': name,
            'description': description,
            'agent_id': agent_id,
            'priority': priority,
        })

    def update_task(self, task_id: str, **fields: Any) -> Dict[str, Any]:
        """Update task fields (e.g. status, result)."""
        return self._request('PUT', f'/api/tasks/{task_id}', json=fields)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task."""
        return self._request('DELETE', f'/api/tasks/{task_id}')

    # ---- Fortress / Fact graph ----

    def query_facts(self, agent: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query the Fortress fact graph."""
        params: Dict[str, str] = {}
        if agent:
            params['agent'] = agent
        if tag:
            params['tag'] = tag
        return self._request('GET', '/api/v1/fortress/facts', params=params)  # type: ignore[return-value]

    def get_fortress_stats(self) -> Dict[str, Any]:
        """Return Fortress engine statistics."""
        return self._request('GET', '/api/v1/fortress/stats')

    # ---- Workforce ----

    def assign_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
        """Assign a task to an agent."""
        return self._request('POST', '/api/workforce/assign', json={
            'task_id': task_id,
            'agent_id': agent_id,
        })

    def get_status(self) -> Dict[str, Any]:
        """Return overall system status."""
        return self._request('GET', '/api/status')
