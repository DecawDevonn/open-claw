import json
import unittest
from app import create_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # --- Health endpoints ---

    def test_health(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')

    def test_health_v1(self):
        response = self.client.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('fortress', data)

    def test_status(self):
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'running')

    # --- Agent endpoints ---

    def test_create_agent(self):
        response = self.client.post('/api/agents',
            data=json.dumps({'name': 'Test Agent', 'type': 'worker'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], 'Test Agent')
        self.assertIn('id', data)

    def test_list_agents_empty(self):
        response = self.client.get('/api/agents')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_get_agent_not_found(self):
        response = self.client.get('/api/agents/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_agent_lifecycle(self):
        # Create
        resp = self.client.post('/api/agents',
            data=json.dumps({'name': 'Lifecycle Agent'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        agent_id = resp.get_json()['id']

        # Get
        resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 200)

        # Update
        resp = self.client.put(f'/api/agents/{agent_id}',
            data=json.dumps({'status': 'busy'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'busy')

        # Delete
        resp = self.client.delete(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 200)

        # Confirm gone
        resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 404)

    # --- Task endpoints ---

    def test_create_task(self):
        response = self.client.post('/api/tasks',
            data=json.dumps({'name': 'Test Task', 'description': 'A test'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['name'], 'Test Task')
        self.assertEqual(data['status'], 'pending')

    def test_list_tasks_empty(self):
        response = self.client.get('/api/tasks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_task_lifecycle(self):
        # Create
        resp = self.client.post('/api/tasks',
            data=json.dumps({'name': 'Lifecycle Task'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        task_id = resp.get_json()['id']

        # Get
        resp = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(resp.status_code, 200)

        # Update to running
        resp = self.client.put(f'/api/tasks/{task_id}',
            data=json.dumps({'status': 'running'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.get_json()['started_at'])

        # Update to completed with result
        resp = self.client.put(f'/api/tasks/{task_id}',
            data=json.dumps({'status': 'completed', 'result': 'done'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['result'], 'done')
        self.assertIsNotNone(data['completed_at'])

        # Delete
        resp = self.client.delete(f'/api/tasks/{task_id}')
        self.assertEqual(resp.status_code, 200)

    def test_task_filter_by_status(self):
        self.client.post('/api/tasks',
            data=json.dumps({'name': 'Pending Task'}),
            content_type='application/json')
        resp = self.client.get('/api/tasks?status=pending')
        self.assertEqual(resp.status_code, 200)
        tasks = resp.get_json()
        self.assertTrue(all(t['status'] == 'pending' for t in tasks))

    # --- Workforce endpoints ---

    def test_workforce_summary(self):
        response = self.client.get('/api/workforce/summary')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('agents_count', data)
        self.assertIn('tasks_count', data)

    def test_assign_task_to_agent(self):
        # Create agent and task
        agent_resp = self.client.post('/api/agents',
            data=json.dumps({'name': 'Worker'}),
            content_type='application/json')
        agent_id = agent_resp.get_json()['id']

        task_resp = self.client.post('/api/tasks',
            data=json.dumps({'name': 'Work Item'}),
            content_type='application/json')
        task_id = task_resp.get_json()['id']

        # Assign
        resp = self.client.post('/api/workforce/assign',
            data=json.dumps({'task_id': task_id, 'agent_id': agent_id}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['task']['status'], 'assigned')
        self.assertEqual(data['agent']['status'], 'busy')

    # --- 404 handler ---

    def test_404(self):
        response = self.client.get('/api/nonexistent-endpoint')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
