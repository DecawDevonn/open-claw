import json
import pytest
from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_status_endpoint(client):
    """Test system status endpoint."""
    response = client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'running'
    assert 'agents' in data
    assert 'tasks' in data


def test_create_agent(client):
    """Test creating a new agent."""
    payload = {'name': 'TestAgent', 'type': 'worker', 'capabilities': ['compute']}
    response = client.post('/api/agents', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'TestAgent'
    assert data['type'] == 'worker'
    assert 'id' in data


def test_list_agents(client):
    """Test listing agents."""
    client.post('/api/agents', json={'name': 'Agent1'})
    response = client.get('/api/agents')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_get_agent_not_found(client):
    """Test getting a non-existent agent."""
    response = client.get('/api/agents/nonexistent-id')
    assert response.status_code == 404


def test_create_task(client):
    """Test creating a new task."""
    payload = {'name': 'TestTask', 'description': 'A test task'}
    response = client.post('/api/tasks', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'TestTask'
    assert data['status'] == 'pending'
    assert 'id' in data


def test_list_tasks(client):
    """Test listing tasks."""
    client.post('/api/tasks', json={'name': 'Task1'})
    response = client.get('/api/tasks')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_get_task_not_found(client):
    """Test getting a non-existent task."""
    response = client.get('/api/tasks/nonexistent-id')
    assert response.status_code == 404


def test_workforce_summary(client):
    """Test workforce summary endpoint."""
    response = client.get('/api/workforce/summary')
    assert response.status_code == 200
    data = response.get_json()
    assert 'agents_count' in data
    assert 'tasks_count' in data
