"""Pytest fixtures for open-claw test suite."""

import pytest
from app import create_app


@pytest.fixture
def app():
    """Create a fresh application instance for each test."""
    application = create_app({
        'TESTING': True,
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'SECRET_KEY': 'test-secret',
    })
    yield application


@pytest.fixture
def client(app):
    """Return a test client for the application."""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Register a standard user and return Authorization headers."""
    client.post('/api/v1/auth/register', json={
        'username': 'testuser',
        'password': 'testpass123',
    })
    resp = client.post('/api/v1/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123',
    })
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_headers(client):
    """Register an admin user and return Authorization headers."""
    client.post('/api/v1/auth/register', json={
        'username': 'adminuser',
        'password': 'adminpass123',
        'role': 'admin',
    })
    resp = client.post('/api/v1/auth/login', json={
        'username': 'adminuser',
        'password': 'adminpass123',
    })
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_agent(client, auth_headers):
    """Create and return a sample agent."""
    resp = client.post('/api/v1/agents', json={
        'name': 'SampleAgent',
        'type': 'worker',
        'capabilities': ['compute', 'storage'],
    }, headers=auth_headers)
    return resp.get_json()


@pytest.fixture
def sample_task(client, auth_headers):
    """Create and return a sample task."""
    resp = client.post('/api/v1/tasks', json={
        'name': 'SampleTask',
        'description': 'A sample task for testing',
        'priority': 'normal',
    }, headers=auth_headers)
    return resp.get_json()
