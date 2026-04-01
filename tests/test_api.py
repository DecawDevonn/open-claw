"""Comprehensive test suite for the open-claw API."""

import json
import pytest
from app import create_app


# ============================================
# Health & Status Endpoints
# ============================================

class TestHealthEndpoints:
    def test_health_check(self, client):
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data

    def test_health_check_v1(self, client):
        resp = client.get('/api/v1/health')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'healthy'

    def test_status(self, client):
        resp = client.get('/api/status')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'running'
        assert 'agents' in data
        assert 'tasks' in data
        assert 'version' in data

    def test_status_v1(self, client):
        resp = client.get('/api/v1/status')
        assert resp.status_code == 200

    def test_health_no_auth_required(self, client):
        """Health endpoints must be publicly accessible."""
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_status_no_auth_required(self, client):
        resp = client.get('/api/status')
        assert resp.status_code == 200


# ============================================
# Authentication Endpoints
# ============================================

class TestAuthentication:
    def test_register_success(self, client):
        resp = client.post('/api/v1/auth/register', json={
            'username': 'newuser',
            'password': 'password123',
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'user_id' in data
        assert data['username'] == 'newuser'
        assert 'message' in data

    def test_register_assigns_default_role(self, client):
        resp = client.post('/api/v1/auth/register', json={
            'username': 'roleuser',
            'password': 'password123',
        })
        assert resp.status_code == 201

    def test_register_duplicate_username(self, client):
        client.post('/api/v1/auth/register', json={'username': 'dupuser', 'password': 'pass1234'})
        resp = client.post('/api/v1/auth/register', json={'username': 'dupuser', 'password': 'pass1234'})
        assert resp.status_code == 409
        assert resp.get_json()['code'] == 'CONFLICT'

    def test_register_missing_username(self, client):
        resp = client.post('/api/v1/auth/register', json={'password': 'pass123456'})
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_register_missing_password(self, client):
        resp = client.post('/api/v1/auth/register', json={'username': 'validuser'})
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_register_short_username(self, client):
        resp = client.post('/api/v1/auth/register', json={'username': 'ab', 'password': 'pass123'})
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_register_short_password(self, client):
        resp = client.post('/api/v1/auth/register', json={'username': 'validuser2', 'password': '12'})
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_register_no_body(self, client):
        resp = client.post('/api/v1/auth/register')
        assert resp.status_code == 400

    def test_login_success(self, client):
        client.post('/api/v1/auth/register', json={'username': 'logintest', 'password': 'testpass123'})
        resp = client.post('/api/v1/auth/login', json={'username': 'logintest', 'password': 'testpass123'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['username'] == 'logintest'

    def test_login_invalid_password(self, client):
        client.post('/api/v1/auth/register', json={'username': 'logintest2', 'password': 'testpass123'})
        resp = client.post('/api/v1/auth/login', json={'username': 'logintest2', 'password': 'wrongpass'})
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 'UNAUTHORIZED'

    def test_login_nonexistent_user(self, client):
        resp = client.post('/api/v1/auth/login', json={'username': 'ghost', 'password': 'pass123'})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post('/api/v1/auth/login', json={'username': 'nopassword'})
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_login_no_body(self, client):
        resp = client.post('/api/v1/auth/login')
        assert resp.status_code == 400

    def test_access_protected_endpoint_without_token(self, client):
        resp = client.get('/api/v1/agents')
        assert resp.status_code == 401

    def test_access_protected_endpoint_with_invalid_token(self, client):
        resp = client.get('/api/v1/agents', headers={'Authorization': 'Bearer invalid.token.here'})
        assert resp.status_code == 422

    def test_token_refresh(self, client):
        client.post('/api/v1/auth/register', json={'username': 'refreshuser', 'password': 'pass123456'})
        resp = client.post('/api/v1/auth/login', json={'username': 'refreshuser', 'password': 'pass123456'})
        refresh_token = resp.get_json()['refresh_token']

        resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {refresh_token}'})
        assert resp.status_code == 200
        assert 'access_token' in resp.get_json()

    def test_refresh_with_access_token_fails(self, client, auth_headers):
        """Using access token on refresh endpoint should fail."""
        access_token = auth_headers['Authorization'].split(' ')[1]
        resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {access_token}'})
        assert resp.status_code == 422


# ============================================
# Agent Management Endpoints
# ============================================

class TestAgents:
    def test_create_agent(self, client, auth_headers):
        resp = client.post('/api/v1/agents', json={
            'name': 'TestAgent',
            'type': 'worker',
            'capabilities': ['compute', 'storage'],
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'TestAgent'
        assert data['type'] == 'worker'
        assert data['status'] == 'idle'
        assert data['tasks_completed'] == 0
        assert 'id' in data
        assert 'created_at' in data

    def test_create_agent_minimal(self, client, auth_headers):
        resp = client.post('/api/v1/agents', json={'name': 'MinAgent'}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['type'] == 'generic'
        assert data['capabilities'] == []

    def test_create_agent_missing_name(self, client, auth_headers):
        resp = client.post('/api/v1/agents', json={'type': 'worker'}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_create_agent_invalid_capabilities(self, client, auth_headers):
        resp = client.post('/api/v1/agents', json={
            'name': 'BadAgent',
            'capabilities': 'not-a-list',
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_create_agent_no_body(self, client, auth_headers):
        resp = client.post('/api/v1/agents', headers=auth_headers)
        assert resp.status_code == 400

    def test_create_agent_requires_auth(self, client):
        resp = client.post('/api/v1/agents', json={'name': 'Agent'})
        assert resp.status_code == 401

    def test_list_agents_empty(self, client, auth_headers):
        resp = client.get('/api/v1/agents', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'] == []
        assert data['total'] == 0

    def test_list_agents_with_data(self, client, auth_headers):
        client.post('/api/v1/agents', json={'name': 'Agent1'}, headers=auth_headers)
        client.post('/api/v1/agents', json={'name': 'Agent2'}, headers=auth_headers)
        resp = client.get('/api/v1/agents', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data
        assert 'pages' in data
        assert data['total'] >= 2

    def test_list_agents_pagination(self, client, auth_headers):
        for i in range(5):
            client.post('/api/v1/agents', json={'name': f'PagAgent{i}'}, headers=auth_headers)
        resp = client.get('/api/v1/agents?page=1&per_page=2', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['items']) <= 2
        assert data['per_page'] == 2

    def test_list_agents_page2(self, client, auth_headers):
        for i in range(5):
            client.post('/api/v1/agents', json={'name': f'PageAgent{i}'}, headers=auth_headers)
        resp = client.get('/api/v1/agents?page=2&per_page=2', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['page'] == 2

    def test_list_agents_filter_by_status(self, client, auth_headers):
        resp = client.get('/api/v1/agents?status=idle', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert all(a['status'] == 'idle' for a in data['items'])

    def test_list_agents_invalid_page(self, client, auth_headers):
        resp = client.get('/api/v1/agents?page=0', headers=auth_headers)
        assert resp.status_code == 400

    def test_get_agent(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.get(f'/api/v1/agents/{agent_id}', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['id'] == agent_id

    def test_get_agent_not_found(self, client, auth_headers):
        resp = client.get('/api/v1/agents/nonexistent-id', headers=auth_headers)
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 'NOT_FOUND'

    def test_update_agent_status(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', json={'status': 'busy'}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'busy'

    def test_update_agent_name(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', json={'name': 'RenamedAgent'}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'RenamedAgent'

    def test_update_agent_capabilities(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', json={'capabilities': ['ml']}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['capabilities'] == ['ml']

    def test_update_agent_invalid_status(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', json={'status': 'invalid'}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_update_agent_invalid_capabilities(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', json={'capabilities': 'bad'}, headers=auth_headers)
        assert resp.status_code == 400

    def test_update_agent_not_found(self, client, auth_headers):
        resp = client.put('/api/v1/agents/nonexistent', json={'status': 'idle'}, headers=auth_headers)
        assert resp.status_code == 404

    def test_update_agent_no_body(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.put(f'/api/v1/agents/{agent_id}', headers=auth_headers)
        assert resp.status_code == 400

    def test_delete_agent(self, client, auth_headers, sample_agent):
        agent_id = sample_agent['id']
        resp = client.delete(f'/api/v1/agents/{agent_id}', headers=auth_headers)
        assert resp.status_code == 200
        # Verify deleted
        resp = client.get(f'/api/v1/agents/{agent_id}', headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_agent_not_found(self, client, auth_headers):
        resp = client.delete('/api/v1/agents/nonexistent-id', headers=auth_headers)
        assert resp.status_code == 404

    def test_all_agent_endpoints_require_auth(self, client, sample_agent):
        agent_id = sample_agent['id']
        assert client.get('/api/v1/agents').status_code == 401
        assert client.post('/api/v1/agents', json={'name': 'x'}).status_code == 401
        assert client.get(f'/api/v1/agents/{agent_id}').status_code == 401
        assert client.put(f'/api/v1/agents/{agent_id}', json={}).status_code == 401
        assert client.delete(f'/api/v1/agents/{agent_id}').status_code == 401


# ============================================
# Task Management Endpoints
# ============================================

class TestTasks:
    def test_create_task(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', json={
            'name': 'TestTask',
            'description': 'A test task',
            'priority': 'high',
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'TestTask'
        assert data['status'] == 'pending'
        assert data['priority'] == 'high'
        assert data['started_at'] is None
        assert data['completed_at'] is None
        assert data['result'] is None
        assert 'id' in data
        assert 'created_at' in data

    def test_create_task_minimal(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', json={'name': 'MinTask'}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['priority'] == 'normal'
        assert data['agent_id'] is None

    def test_create_task_missing_name(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', json={'description': 'No name'}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_create_task_invalid_priority(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', json={'name': 'Task', 'priority': 'ultra'}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_create_task_with_valid_agent(self, client, auth_headers, sample_agent):
        resp = client.post('/api/v1/tasks', json={
            'name': 'AgentTask',
            'agent_id': sample_agent['id'],
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.get_json()['agent_id'] == sample_agent['id']

    def test_create_task_with_nonexistent_agent(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', json={
            'name': 'Task',
            'agent_id': 'nonexistent-agent-id',
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_create_task_all_priorities(self, client, auth_headers):
        for priority in ('low', 'normal', 'high', 'critical'):
            resp = client.post('/api/v1/tasks', json={'name': f'Task-{priority}', 'priority': priority},
                               headers=auth_headers)
            assert resp.status_code == 201

    def test_create_task_no_body(self, client, auth_headers):
        resp = client.post('/api/v1/tasks', headers=auth_headers)
        assert resp.status_code == 400

    def test_list_tasks_empty(self, client, auth_headers):
        resp = client.get('/api/v1/tasks', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['items'] == []
        assert data['total'] == 0

    def test_list_tasks_pagination(self, client, auth_headers):
        for i in range(5):
            client.post('/api/v1/tasks', json={'name': f'Task{i}'}, headers=auth_headers)
        resp = client.get('/api/v1/tasks?page=1&per_page=3', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['items']) <= 3
        assert data['per_page'] == 3

    def test_list_tasks_filter_by_status(self, client, auth_headers):
        client.post('/api/v1/tasks', json={'name': 'PendingTask'}, headers=auth_headers)
        resp = client.get('/api/v1/tasks?status=pending', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert all(t['status'] == 'pending' for t in data['items'])

    def test_list_tasks_filter_by_agent(self, client, auth_headers, sample_agent):
        client.post('/api/v1/tasks', json={
            'name': 'AgentTask',
            'agent_id': sample_agent['id'],
        }, headers=auth_headers)
        resp = client.get(f'/api/v1/tasks?agent_id={sample_agent["id"]}', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert all(t['agent_id'] == sample_agent['id'] for t in data['items'])

    def test_get_task(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.get(f'/api/v1/tasks/{task_id}', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['id'] == task_id

    def test_get_task_not_found(self, client, auth_headers):
        resp = client.get('/api/v1/tasks/nonexistent-id', headers=auth_headers)
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 'NOT_FOUND'

    def test_update_task_to_running(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.put(f'/api/v1/tasks/{task_id}', json={'status': 'running'}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'running'
        assert data['started_at'] is not None

    def test_update_task_to_completed(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.put(f'/api/v1/tasks/{task_id}',
                          json={'status': 'completed', 'result': 'success'},
                          headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'completed'
        assert data['completed_at'] is not None
        assert data['result'] == 'success'

    def test_update_task_to_failed(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.put(f'/api/v1/tasks/{task_id}', json={'status': 'failed'}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'failed'
        assert data['completed_at'] is not None

    def test_update_task_invalid_status(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.put(f'/api/v1/tasks/{task_id}', json={'status': 'invalid'}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'INVALID_INPUT'

    def test_update_task_not_found(self, client, auth_headers):
        resp = client.put('/api/v1/tasks/nonexistent', json={'status': 'running'}, headers=auth_headers)
        assert resp.status_code == 404

    def test_update_task_no_body(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.put(f'/api/v1/tasks/{task_id}', headers=auth_headers)
        assert resp.status_code == 400

    def test_delete_task(self, client, auth_headers, sample_task):
        task_id = sample_task['id']
        resp = client.delete(f'/api/v1/tasks/{task_id}', headers=auth_headers)
        assert resp.status_code == 200
        resp = client.get(f'/api/v1/tasks/{task_id}', headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_task_not_found(self, client, auth_headers):
        resp = client.delete('/api/v1/tasks/nonexistent-id', headers=auth_headers)
        assert resp.status_code == 404

    def test_all_task_endpoints_require_auth(self, client, sample_task):
        task_id = sample_task['id']
        assert client.get('/api/v1/tasks').status_code == 401
        assert client.post('/api/v1/tasks', json={'name': 'x'}).status_code == 401
        assert client.get(f'/api/v1/tasks/{task_id}').status_code == 401
        assert client.put(f'/api/v1/tasks/{task_id}', json={}).status_code == 401
        assert client.delete(f'/api/v1/tasks/{task_id}').status_code == 401


# ============================================
# Workforce Management Endpoints
# ============================================

class TestWorkforce:
    def test_assign_task_to_agent(self, client, auth_headers, sample_agent, sample_task):
        resp = client.post('/api/v1/workforce/assign', json={
            'task_id': sample_task['id'],
            'agent_id': sample_agent['id'],
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['task']['status'] == 'assigned'
        assert data['task']['agent_id'] == sample_agent['id']
        assert data['agent']['status'] == 'busy'

    def test_assign_missing_fields(self, client, auth_headers, sample_agent):
        resp = client.post('/api/v1/workforce/assign', json={
            'agent_id': sample_agent['id'],
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 'MISSING_FIELDS'

    def test_assign_task_not_found(self, client, auth_headers, sample_agent):
        resp = client.post('/api/v1/workforce/assign', json={
            'task_id': 'nonexistent',
            'agent_id': sample_agent['id'],
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_assign_agent_not_found(self, client, auth_headers, sample_task):
        resp = client.post('/api/v1/workforce/assign', json={
            'task_id': sample_task['id'],
            'agent_id': 'nonexistent',
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_assign_no_body(self, client, auth_headers):
        resp = client.post('/api/v1/workforce/assign', headers=auth_headers)
        assert resp.status_code == 400

    def test_workforce_summary_empty(self, client, auth_headers):
        resp = client.get('/api/v1/workforce/summary', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['agents_count'] == 0
        assert data['tasks_count'] == 0
        assert data['capabilities'] == {}

    def test_workforce_summary_with_data(self, client, auth_headers, sample_agent, sample_task):
        resp = client.get('/api/v1/workforce/summary', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['agents_count'] >= 1
        assert data['tasks_count'] >= 1
        assert 'agents' in data
        assert 'tasks' in data

    def test_workforce_summary_capabilities(self, client, auth_headers):
        client.post('/api/v1/agents', json={
            'name': 'CapAgent',
            'capabilities': ['ml', 'compute'],
        }, headers=auth_headers)
        resp = client.get('/api/v1/workforce/summary', headers=auth_headers)
        data = resp.get_json()
        assert 'ml' in data['capabilities']
        assert 'compute' in data['capabilities']

    def test_workforce_summary_requires_auth(self, client):
        resp = client.get('/api/v1/workforce/summary')
        assert resp.status_code == 401

    def test_assign_requires_auth(self, client):
        resp = client.post('/api/v1/workforce/assign', json={})
        assert resp.status_code == 401


# ============================================
# Error Handlers
# ============================================

class TestErrorHandlers:
    def test_404_handler(self, client):
        resp = client.get('/api/v1/nonexistent-endpoint')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data
        assert data['code'] == 'NOT_FOUND'

    def test_404_returns_json(self, client):
        resp = client.get('/completely/unknown/path')
        assert resp.status_code == 404
        assert resp.content_type == 'application/json'


# ============================================
# Application Factory
# ============================================

class TestAppFactory:
    def test_create_app_returns_flask_app(self):
        from flask import Flask
        app = create_app({'TESTING': True})
        assert isinstance(app, Flask)

    def test_create_app_testing_config(self):
        app = create_app({'TESTING': True})
        assert app.config['TESTING'] is True

    def test_create_app_custom_secret(self):
        app = create_app({'TESTING': True, 'SECRET_KEY': 'my-custom-secret'})
        assert app.config['SECRET_KEY'] == 'my-custom-secret'

    def test_create_app_has_storage(self):
        app = create_app({'TESTING': True})
        assert hasattr(app, 'users')
        assert hasattr(app, 'agents')
        assert hasattr(app, 'tasks')
        assert isinstance(app.users, dict)
        assert isinstance(app.agents, dict)
        assert isinstance(app.tasks, dict)

    def test_separate_app_instances_have_independent_storage(self):
        """Each app instance must have isolated storage."""
        app1 = create_app({'TESTING': True})
        app2 = create_app({'TESTING': True})
        with app1.test_client() as c1:
            c1.post('/api/v1/auth/register', json={'username': 'user1', 'password': 'pass123'})
        with app2.test_client() as c2:
            resp = c2.post('/api/v1/auth/login', json={'username': 'user1', 'password': 'pass123'})
            # user1 should not exist in app2
            assert resp.status_code == 401


# ============================================
# Status counter tests
# ============================================

class TestStatusCounts:
    def test_status_reflects_agent_count(self, client, auth_headers):
        client.post('/api/v1/agents', json={'name': 'A1'}, headers=auth_headers)
        client.post('/api/v1/agents', json={'name': 'A2'}, headers=auth_headers)
        resp = client.get('/api/v1/status')
        data = resp.get_json()
        assert data['agents']['total'] >= 2

    def test_status_reflects_task_count(self, client, auth_headers):
        client.post('/api/v1/tasks', json={'name': 'T1'}, headers=auth_headers)
        resp = client.get('/api/v1/status')
        data = resp.get_json()
        assert data['tasks']['total'] >= 1
        assert data['tasks']['pending'] >= 1

    def test_status_running_task_count(self, client, auth_headers):
        task_resp = client.post('/api/v1/tasks', json={'name': 'RunningTask'}, headers=auth_headers)
        task_id = task_resp.get_json()['id']
        client.put(f'/api/v1/tasks/{task_id}', json={'status': 'running'}, headers=auth_headers)
        resp = client.get('/api/v1/status')
        data = resp.get_json()
        assert data['tasks']['running'] >= 1


# ============================================
# Role-based access (admin)
# ============================================

class TestAdminRole:
    def test_register_admin_role(self, client):
        resp = client.post('/api/v1/auth/register', json={
            'username': 'myadmin',
            'password': 'adminpass123',
            'role': 'admin',
        })
        assert resp.status_code == 201

    def test_admin_can_access_all_endpoints(self, client, admin_headers):
        """Admin users can access all protected endpoints."""
        assert client.get('/api/v1/agents', headers=admin_headers).status_code == 200
        assert client.get('/api/v1/tasks', headers=admin_headers).status_code == 200
        assert client.get('/api/v1/workforce/summary', headers=admin_headers).status_code == 200

    def test_admin_login_returns_admin_role(self, client, admin_headers):
        """Admin login response includes correct role."""
        resp = client.post('/api/v1/auth/login', json={
            'username': 'adminuser',
            'password': 'adminpass123',
        })
        assert resp.status_code == 200
        assert resp.get_json()['role'] == 'admin'
