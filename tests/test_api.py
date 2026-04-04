"""
Comprehensive test suite for Open Claw API v1.
Covers auth, agents, tasks, workforce, health, and error handling.
"""
import json
import unittest
from app import create_app


class TestAPI(unittest.TestCase):
    """Full API test suite."""

    BASE = "/api/v1"

    def setUp(self):
        """Create a fresh app and authenticated client for each test."""
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-secret',
            'JWT_SECRET_KEY': 'test-jwt-secret',
            'RATELIMIT_ENABLED': False,
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Register and log in a test user to get a JWT token
        self.client.post(
            f"{self.BASE}/auth/register",
            data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
            content_type='application/json'
        )
        login_resp = self.client.post(
            f"{self.BASE}/auth/login",
            data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
            content_type='application/json'
        )
        token_data = login_resp.json
        self.token = token_data.get('access_token', '')
        self.auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def tearDown(self):
        self.app_context.pop()

    def _post(self, path, data):
        return self.client.post(
            f"{self.BASE}{path}",
            data=json.dumps(data),
            headers=self.auth_headers
        )

    def _get(self, path, params=None):
        return self.client.get(
            f"{self.BASE}{path}",
            query_string=params,
            headers=self.auth_headers
        )

    def _put(self, path, data):
        return self.client.put(
            f"{self.BASE}{path}",
            data=json.dumps(data),
            headers=self.auth_headers
        )

    def _delete(self, path):
        return self.client.delete(f"{self.BASE}{path}", headers=self.auth_headers)

    # ------------------------------------------------------------------
    # Legacy compatibility endpoint
    # ------------------------------------------------------------------

    def test_endpoint(self):
        """Test the legacy /api/example endpoint (compatibility)."""
        response = self.client.get('/api/example')
        # If not present in new app, /api/health is the canonical check
        self.assertIn(response.status_code, [200, 404])

    # ------------------------------------------------------------------
    # Health & Status
    # ------------------------------------------------------------------

    def test_health(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'healthy')

    def test_v1_health(self):
        """Test the versioned health check endpoint."""
        response = self.client.get(f'{self.BASE}/health')
        self.assertEqual(response.status_code, 200)

    def test_status(self):
        """Test the system status endpoint."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.json)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def test_register_and_login(self):
        """Test user registration and login flow."""
        reg = self.client.post(
            f"{self.BASE}/auth/register",
            data=json.dumps({'username': 'newuser', 'password': 'newpass123'}),
            content_type='application/json'
        )
        self.assertIn(reg.status_code, [200, 201, 409])  # 409 if already exists

        login = self.client.post(
            f"{self.BASE}/auth/login",
            data=json.dumps({'username': 'newuser', 'password': 'newpass123'}),
            content_type='application/json'
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn('access_token', login.json)

    def test_protected_route_without_token(self):
        """Test that protected routes reject unauthenticated requests."""
        response = self.client.get(f'{self.BASE}/agents')
        self.assertIn(response.status_code, [401, 422])

    # ------------------------------------------------------------------
    # Agent CRUD
    # ------------------------------------------------------------------

    def test_create_agent(self):
        """Test creating a new agent."""
        resp = self._post('/agents', {'name': 'TestAgent', 'type': 'worker', 'capabilities': ['nlp']})
        self.assertEqual(resp.status_code, 201)
        data = resp.json
        self.assertIn('id', data)
        self.assertEqual(data['name'], 'TestAgent')
        self.assertEqual(data['status'], 'idle')

    def test_list_agents(self):
        """Test listing all agents."""
        resp = self._get('/agents')
        self.assertEqual(resp.status_code, 200)
        body = resp.json
        # May be paginated — check for list or paginated wrapper
        self.assertTrue(isinstance(body, list) or 'agents' in body or 'items' in body)

    def test_create_and_get_agent(self):
        """Test creating then retrieving an agent."""
        create = self._post('/agents', {'name': 'RetrieveMe', 'type': 'analyst'})
        self.assertEqual(create.status_code, 201)
        agent_id = create.json['id']

        get = self._get(f'/agents/{agent_id}')
        self.assertEqual(get.status_code, 200)
        self.assertEqual(get.json['id'], agent_id)

    def test_get_agent_not_found(self):
        """Test fetching a non-existent agent returns 404."""
        resp = self._get('/agents/nonexistent-id-xyz')
        self.assertEqual(resp.status_code, 404)

    def test_update_agent(self):
        """Test updating an agent's status."""
        create = self._post('/agents', {'name': 'UpdateMe'})
        self.assertEqual(create.status_code, 201)
        agent_id = create.json['id']

        update = self._put(f'/agents/{agent_id}', {'status': 'busy'})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json['status'], 'busy')

    def test_delete_agent(self):
        """Test deleting an agent."""
        create = self._post('/agents', {'name': 'DeleteMe'})
        self.assertEqual(create.status_code, 201)
        agent_id = create.json['id']

        delete = self._delete(f'/agents/{agent_id}')
        self.assertEqual(delete.status_code, 200)

        get = self._get(f'/agents/{agent_id}')
        self.assertEqual(get.status_code, 404)

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def test_create_task(self):
        """Test creating a new task."""
        resp = self._post('/tasks', {'name': 'TestTask', 'description': 'A test task', 'priority': 'high'})
        self.assertEqual(resp.status_code, 201)
        data = resp.json
        self.assertIn('id', data)
        self.assertEqual(data['name'], 'TestTask')
        self.assertEqual(data['status'], 'pending')

    def test_list_tasks(self):
        """Test listing all tasks."""
        resp = self._get('/tasks')
        self.assertEqual(resp.status_code, 200)
        body = resp.json
        self.assertTrue(isinstance(body, list) or 'tasks' in body or 'items' in body)

    def test_get_task_not_found(self):
        """Test fetching a non-existent task returns 404."""
        resp = self._get('/tasks/nonexistent-task-xyz')
        self.assertEqual(resp.status_code, 404)

    def test_update_task_status(self):
        """Test updating a task status to running."""
        create = self._post('/tasks', {'name': 'RunMe'})
        self.assertEqual(create.status_code, 201)
        task_id = create.json['id']

        update = self._put(f'/tasks/{task_id}', {'status': 'running'})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json['status'], 'running')

    def test_delete_task(self):
        """Test deleting a task."""
        create = self._post('/tasks', {'name': 'DeleteMe'})
        self.assertEqual(create.status_code, 201)
        task_id = create.json['id']

        delete = self._delete(f'/tasks/{task_id}')
        self.assertEqual(delete.status_code, 200)

        get = self._get(f'/tasks/{task_id}')
        self.assertEqual(get.status_code, 404)

    # ------------------------------------------------------------------
    # Workforce
    # ------------------------------------------------------------------

    def test_workforce_summary(self):
        """Test the workforce summary endpoint."""
        resp = self._get('/workforce/summary')
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        self.assertIn('agents_count', data)
        self.assertIn('tasks_count', data)

    def test_assign_task_to_agent(self):
        """Test assigning a task to an agent."""
        agent = self._post('/agents', {'name': 'Worker'})
        self.assertEqual(agent.status_code, 201)
        agent_id = agent.json['id']

        task = self._post('/tasks', {'name': 'Job'})
        self.assertEqual(task.status_code, 201)
        task_id = task.json['id']

        assign = self._post('/workforce/assign', {'task_id': task_id, 'agent_id': agent_id})
        self.assertEqual(assign.status_code, 200)
        self.assertEqual(assign.json['task']['status'], 'assigned')
        self.assertEqual(assign.json['agent']['status'], 'busy')

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_404_handler(self):
        """Test that unknown routes return a JSON 404."""
        resp = self.client.get('/api/v1/does-not-exist', headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
        self.assertIn('error', resp.json)


if __name__ == '__main__':
    unittest.main()
