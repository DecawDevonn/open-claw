import json
import unittest
from app import create_app


class TestFortressEngine(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.engine = self.app.extensions.get('fortress_engine')

    def tearDown(self):
        self.ctx.pop()

    def test_engine_initialized(self):
        self.assertIsNotNone(self.engine)

    def test_add_and_get_fact(self):
        fid = self.engine.add_fact('agent1', 'test fact', tags=['test'])
        self.assertTrue(fid.startswith('f'))
        fact = self.engine.get_fact(fid)
        self.assertIsNotNone(fact)
        self.assertEqual(fact['fact'], 'test fact')
        self.assertEqual(fact['agent'], 'agent1')

    def test_list_facts(self):
        self.engine.add_fact('agentA', 'fact one')
        self.engine.add_fact('agentB', 'fact two')
        facts = self.engine.list_facts()
        agents = {f['agent'] for f in facts}
        self.assertIn('agentA', agents)
        self.assertIn('agentB', agents)

    def test_list_facts_filter_by_agent(self):
        self.engine.add_fact('agentX', 'x fact')
        self.engine.add_fact('agentY', 'y fact')
        facts = self.engine.list_facts(agent='agentX')
        self.assertTrue(all(f['agent'] == 'agentX' for f in facts))

    def test_mailbox_write_read_clear(self):
        self.engine.write_mailbox('bot1', {'command': 'ls', 'result': 'file.txt'})
        msgs = self.engine.read_mailbox('bot1')
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['command'], 'ls')

        cleared = self.engine.clear_mailbox('bot1')
        self.assertEqual(cleared, 1)
        self.assertEqual(self.engine.read_mailbox('bot1'), [])

    def test_execute_command_allowed(self):
        result = self.engine.execute_command('echo hello', 'agent1', auto_approve=True)
        self.assertTrue(result['allowed'])
        self.assertIn('hello', result['result'])
        self.assertIn('fact_id', result)

    def test_execute_command_blocked(self):
        result = self.engine.execute_command('rm -rf /', 'agent1', auto_approve=False)
        self.assertFalse(result['allowed'])
        self.assertIn('Blocked', result['result'])

    def test_get_stats(self):
        stats = self.engine.get_stats()
        self.assertIn('fact_count', stats)
        self.assertIn('context_window_size', stats)
        self.assertIn('total_agents', stats)
        self.assertIn('mailbox_count', stats)
        self.assertIn('worktree_count', stats)

    def test_context_summary(self):
        self.engine.add_fact('agent1', 'context fact')
        summary = self.engine.get_context_summary()
        self.assertIn('context_window_size', summary)
        self.assertGreater(summary['context_window_size'], 0)

    def test_compact_context(self):
        for i in range(15):
            self.engine.add_fact('agent1', f'fact {i}')
        removed = self.engine.compact_context(keep_last=5)
        self.assertGreaterEqual(removed, 0)


class TestFortressAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_execute_command(self):
        resp = self.client.post('/api/v1/fortress/agents/agent1/execute',
            data=json.dumps({'command': 'echo test', 'auto_approve': True}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['agent_id'], 'agent1')
        self.assertTrue(data['allowed'])

    def test_execute_command_missing(self):
        resp = self.client.post('/api/v1/fortress/agents/agent1/execute',
            data=json.dumps({}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_execute_command_blocked(self):
        resp = self.client.post('/api/v1/fortress/agents/agent1/execute',
            data=json.dumps({'command': 'rm -rf /'}),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['allowed'])

    def test_list_facts(self):
        resp = self.client.get('/api/v1/fortress/facts')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('facts', data)
        self.assertIn('count', data)

    def test_get_fact_not_found(self):
        resp = self.client.get('/api/v1/fortress/facts/nonexistent')
        self.assertEqual(resp.status_code, 404)

    def test_get_fact_found(self):
        # Execute a command to create a fact
        self.client.post('/api/v1/fortress/agents/factbot/execute',
            data=json.dumps({'command': 'echo facttest', 'auto_approve': True}),
            content_type='application/json')
        # Get facts list
        resp = self.client.get('/api/v1/fortress/facts')
        facts = resp.get_json()['facts']
        if facts:
            fid = facts[0]['id']
            resp2 = self.client.get(f'/api/v1/fortress/facts/{fid}')
            self.assertEqual(resp2.status_code, 200)

    def test_read_mailbox(self):
        resp = self.client.get('/api/v1/fortress/mailbox/agent99')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['agent_id'], 'agent99')
        self.assertIn('messages', data)

    def test_clear_mailbox(self):
        resp = self.client.delete('/api/v1/fortress/mailbox/agent99')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('cleared', data)

    def test_context(self):
        resp = self.client.get('/api/v1/fortress/context')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('context_window_size', data)

    def test_stats(self):
        resp = self.client.get('/api/v1/fortress/stats')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('fact_count', data)


if __name__ == '__main__':
    unittest.main()
