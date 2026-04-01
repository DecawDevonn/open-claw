import json
import unittest
from app import create_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        """Create a new app instance for each test case."""
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Destroy the app context after each test case."""
        self.app_context.pop()

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')

    def test_status_endpoint(self):
        """Test the system status endpoint."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'running')
        self.assertIn('agents', data)
        self.assertIn('tasks', data)

    def test_create_agent(self):
        """Test creating a new agent."""
        payload = {'name': 'TestAgent', 'type': 'worker', 'capabilities': ['process']}
        response = self.client.post(
            '/api/agents',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], 'TestAgent')
        self.assertIn('id', data)

    def test_list_agents(self):
        """Test listing all agents."""
        response = self.client.get('/api/agents')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_create_task(self):
        """Test creating a new task."""
        payload = {'name': 'TestTask', 'description': 'A test task', 'priority': 'high'}
        response = self.client.post(
            '/api/tasks',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], 'TestTask')
        self.assertEqual(data['status'], 'pending')

    def test_list_tasks(self):
        """Test listing all tasks."""
        response = self.client.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_agent_not_found(self):
        """Test 404 for missing agent."""
        response = self.client.get('/api/agents/nonexistent-id')
        self.assertEqual(response.status_code, 404)

    def test_task_not_found(self):
        """Test 404 for missing task."""
        response = self.client.get('/api/tasks/nonexistent-id')
        self.assertEqual(response.status_code, 404)

    def test_workforce_summary(self):
        """Test the workforce summary endpoint."""
        response = self.client.get('/api/workforce/summary')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('agents_count', data)
        self.assertIn('tasks_count', data)


if __name__ == '__main__':
    unittest.main()