import json
import unittest
from app import create_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        """Create a new app instance for each test case."""
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret'})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Destroy the app context after each test case."""
        self.app_context.pop()

    # ------------------------------------------------------------------
    # Example / Health
    # ------------------------------------------------------------------

    def test_endpoint(self):
        """Test the example API endpoint."""
        response = self.client.get('/api/example')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'key': 'value'})

    def test_health(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)

    def test_status(self):
        """Test the system status endpoint."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data['status'], 'running')
        self.assertIn('agents', data)
        self.assertIn('tasks', data)

    # ------------------------------------------------------------------
    # Agent CRUD
    # ------------------------------------------------------------------

    def test_create_agent(self):
        """Test creating a new agent."""
        payload = {'name': 'TestAgent', 'type': 'worker', 'capabilities': ['nlp']}
        response = self.client.post('/api/agents',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json
        self.assertEqual(data['name'], 'TestAgent')
        self.assertEqual(data['status'], 'idle')
        self.assertIn('id', data)
        return data['id']

    def test_list_agents(self):
        """Test listing all agents."""
        response = self.client.get('/api/agents')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)

    def test_get_agent_not_found(self):
        """Test fetching a non-existent agent returns 404."""
        response = self.client.get('/api/agents/nonexistent-id')
        self.assertEqual(response.status_code, 404)

    def test_create_and_get_agent(self):
        """Test creating then retrieving an agent."""
        payload = {'name': 'RetrieveMe', 'type': 'analyst'}
        create_resp = self.client.post('/api/agents',
                                       data=json.dumps(payload),
                                       content_type='application/json')
        self.assertEqual(create_resp.status_code, 201)
        agent_id = create_resp.json['id']

        get_resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json['id'], agent_id)

    def test_update_agent(self):
        """Test updating an agent's status."""
        create_resp = self.client.post('/api/agents',
                                       data=json.dumps({'name': 'UpdateMe'}),
                                       content_type='application/json')
        agent_id = create_resp.json['id']

        update_resp = self.client.put(f'/api/agents/{agent_id}',
                                      data=json.dumps({'status': 'busy'}),
                                      content_type='application/json')
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.json['status'], 'busy')

    def test_delete_agent(self):
        """Test deleting an agent."""
        create_resp = self.client.post('/api/agents',
                                       data=json.dumps({'name': 'DeleteMe'}),
                                       content_type='application/json')
        agent_id = create_resp.json['id']

        del_resp = self.client.delete(f'/api/agents/{agent_id}')
        self.assertEqual(del_resp.status_code, 200)

        get_resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(get_resp.status_code, 404)

    # ------------------------------------------------------------------
    # Task CRUD
    # ------------------------------------------------------------------

    def test_create_task(self):
        """Test creating a new task."""
        payload = {'name': 'TestTask', 'description': 'A test task', 'priority': 'high'}
        response = self.client.post('/api/tasks',
                                    data=json.dumps(payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json
        self.assertEqual(data['name'], 'TestTask')
        self.assertEqual(data['status'], 'pending')
        self.assertIn('id', data)

    def test_list_tasks(self):
        """Test listing all tasks."""
        response = self.client.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)

    def test_get_task_not_found(self):
        """Test fetching a non-existent task returns 404."""
        response = self.client.get('/api/tasks/nonexistent-id')
        self.assertEqual(response.status_code, 404)

    def test_update_task_status(self):
        """Test updating a task's status to running."""
        create_resp = self.client.post('/api/tasks',
                                       data=json.dumps({'name': 'RunMe'}),
                                       content_type='application/json')
        task_id = create_resp.json['id']

        update_resp = self.client.put(f'/api/tasks/{task_id}',
                                      data=json.dumps({'status': 'running'}),
                                      content_type='application/json')
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.json['status'], 'running')
        self.assertIsNotNone(update_resp.json['started_at'])

    def test_delete_task(self):
        """Test deleting a task."""
        create_resp = self.client.post('/api/tasks',
                                       data=json.dumps({'name': 'DeleteMe'}),
                                       content_type='application/json')
        task_id = create_resp.json['id']

        del_resp = self.client.delete(f'/api/tasks/{task_id}')
        self.assertEqual(del_resp.status_code, 200)

        get_resp = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(get_resp.status_code, 404)

    # ------------------------------------------------------------------
    # Workforce
    # ------------------------------------------------------------------

    def test_workforce_summary(self):
        """Test the workforce summary endpoint."""
        response = self.client.get('/api/workforce/summary')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertIn('agents_count', data)
        self.assertIn('tasks_count', data)

    def test_assign_task_to_agent(self):
        """Test assigning a task to an agent."""
        agent_resp = self.client.post('/api/agents',
                                      data=json.dumps({'name': 'Worker'}),
                                      content_type='application/json')
        agent_id = agent_resp.json['id']

        task_resp = self.client.post('/api/tasks',
                                     data=json.dumps({'name': 'Job'}),
                                     content_type='application/json')
        task_id = task_resp.json['id']

        assign_resp = self.client.post('/api/workforce/assign',
                                       data=json.dumps({'task_id': task_id, 'agent_id': agent_id}),
                                       content_type='application/json')
        self.assertEqual(assign_resp.status_code, 200)
        self.assertEqual(assign_resp.json['task']['status'], 'assigned')
        self.assertEqual(assign_resp.json['agent']['status'], 'busy')

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_404_handler(self):
        """Test that unknown routes return a JSON 404."""
        response = self.client.get('/api/does-not-exist')
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json)


if __name__ == '__main__':
    unittest.main()
