import json
import unittest
from app import create_app


class TestAPI(unittest.TestCase):
    def setUp(self):
        """Create a fresh app instance for each test."""
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # ---- Health & Status ----

    def test_health(self):
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')

    def test_status(self):
        resp = self.client.get('/api/status')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('agents', data)
        self.assertIn('tasks', data)

    # ---- Agents ----

    def test_list_agents_empty(self):
        resp = self.client.get('/api/agents')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    def test_create_agent(self):
        resp = self.client.post('/api/agents',
                                data=json.dumps({'name': 'TestAgent', 'type': 'compute'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['name'], 'TestAgent')
        self.assertEqual(data['status'], 'idle')
        self.assertIn('id', data)

    def test_get_agent(self):
        # Create first
        create = self.client.post('/api/agents',
                                  data=json.dumps({'name': 'A1'}),
                                  content_type='application/json')
        agent_id = create.get_json()['id']

        resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['id'], agent_id)

    def test_get_agent_not_found(self):
        resp = self.client.get('/api/agents/nonexistent')
        self.assertEqual(resp.status_code, 404)

    def test_update_agent(self):
        create = self.client.post('/api/agents',
                                  data=json.dumps({'name': 'A2'}),
                                  content_type='application/json')
        agent_id = create.get_json()['id']

        resp = self.client.put(f'/api/agents/{agent_id}',
                               data=json.dumps({'status': 'busy'}),
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'busy')

    def test_delete_agent(self):
        create = self.client.post('/api/agents',
                                  data=json.dumps({'name': 'A3'}),
                                  content_type='application/json')
        agent_id = create.get_json()['id']

        resp = self.client.delete(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 200)

        # Verify gone
        resp = self.client.get(f'/api/agents/{agent_id}')
        self.assertEqual(resp.status_code, 404)

    # ---- Tasks ----

    def test_list_tasks_empty(self):
        resp = self.client.get('/api/tasks')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    def test_create_task(self):
        resp = self.client.post('/api/tasks',
                                data=json.dumps({'name': 'T1', 'priority': 'high'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data['name'], 'T1')
        self.assertEqual(data['status'], 'pending')

    def test_get_task(self):
        create = self.client.post('/api/tasks',
                                  data=json.dumps({'name': 'T2'}),
                                  content_type='application/json')
        task_id = create.get_json()['id']

        resp = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['id'], task_id)

    def test_update_task_status(self):
        create = self.client.post('/api/tasks',
                                  data=json.dumps({'name': 'T3'}),
                                  content_type='application/json')
        task_id = create.get_json()['id']

        resp = self.client.put(f'/api/tasks/{task_id}',
                               data=json.dumps({'status': 'running'}),
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'running')
        self.assertIsNotNone(data['started_at'])

    def test_delete_task(self):
        create = self.client.post('/api/tasks',
                                  data=json.dumps({'name': 'T4'}),
                                  content_type='application/json')
        task_id = create.get_json()['id']

        resp = self.client.delete(f'/api/tasks/{task_id}')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(f'/api/tasks/{task_id}')
        self.assertEqual(resp.status_code, 404)

    # ---- Workforce ----

    def test_workforce_summary(self):
        resp = self.client.get('/api/workforce/summary')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('agents_count', data)
        self.assertIn('tasks_count', data)

    def test_assign_task(self):
        agent = self.client.post('/api/agents',
                                 data=json.dumps({'name': 'WA'}),
                                 content_type='application/json').get_json()
        task = self.client.post('/api/tasks',
                                data=json.dumps({'name': 'WT'}),
                                content_type='application/json').get_json()

        resp = self.client.post('/api/workforce/assign',
                                data=json.dumps({'task_id': task['id'], 'agent_id': agent['id']}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['task']['status'], 'assigned')
        self.assertEqual(data['agent']['status'], 'busy')

    # ---- Error handlers ----

    def test_404(self):
        resp = self.client.get('/api/nonexistent')
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
