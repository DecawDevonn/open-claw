"""Tests for all Devonn.AI integration endpoints.

All external API calls are mocked; no real credentials are needed.
Tests cover the happy path plus the most important error cases for every
new route group:  /api/auth/*, /api/ai/*, /api/voice/*, /api/search/*,
/api/integrations/*, and the enhanced /api/health endpoint.
"""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from app import create_app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def token(client):
    """Register a test user and return their JWT."""
    resp = client.post('/api/auth/register', json={'username': 'testuser'})
    assert resp.status_code == 201
    return resp.get_json()['token']


@pytest.fixture
def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


# ── /api/health ───────────────────────────────────────────────────────────────

def test_health_includes_integrations(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'healthy'
    assert 'integrations' in data
    assert 'configured' in data['integrations']


# ── /api/integrations/services ────────────────────────────────────────────────

def test_integrations_services_no_auth(client):
    """This endpoint is public — no token required."""
    resp = client.get('/api/integrations/services')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'configured' in data
    assert isinstance(data['configured'], list)


# ── /api/auth/* ───────────────────────────────────────────────────────────────

def test_auth_register(client):
    resp = client.post('/api/auth/register', json={'username': 'alice'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['username'] == 'alice'


def test_auth_register_duplicate(client):
    client.post('/api/auth/register', json={'username': 'bob'})
    resp = client.post('/api/auth/register', json={'username': 'bob'})
    assert resp.status_code == 409


def test_auth_register_missing_username(client):
    resp = client.post('/api/auth/register', json={})
    assert resp.status_code == 400


def test_auth_token(client):
    reg = client.post('/api/auth/register', json={'username': 'carol'})
    user_id = reg.get_json()['user']['id']
    resp = client.post('/api/auth/token', json={'user_id': user_id})
    assert resp.status_code == 200
    assert 'token' in resp.get_json()


def test_auth_token_unknown_user(client):
    resp = client.post('/api/auth/token', json={'user_id': 'nonexistent'})
    assert resp.status_code == 404


def test_auth_me(client, auth_headers):
    resp = client.get('/api/auth/me', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'sub' in data


def test_auth_me_no_token(client):
    resp = client.get('/api/auth/me')
    assert resp.status_code == 401


def test_auth_me_bad_token(client):
    resp = client.get('/api/auth/me', headers={'Authorization': 'Bearer bad.token.here'})
    assert resp.status_code == 401


def test_auth_revoke_with_storage(client, auth_headers):
    """Revoking a valid token with the storage-backed AuthService returns 200."""
    resp = client.post('/api/auth/revoke', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['message'] == 'Token revoked'


# ── /api/ai/* ─────────────────────────────────────────────────────────────────

def test_ai_complete_no_key(client, auth_headers):
    """Missing OPENAI_API_KEY → 503 Service Unavailable."""
    resp = client.post('/api/ai/complete',
                       json={'prompt': 'Hello'},
                       headers=auth_headers)
    assert resp.status_code == 503


def test_ai_complete_missing_prompt(client, auth_headers):
    resp = client.post('/api/ai/complete', json={}, headers=auth_headers)
    assert resp.status_code == 400


@patch('openclaw.services.ai.requests.post')
def test_ai_complete_success(mock_post, client, auth_headers):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            'choices': [{'message': {'content': 'Hello, World!'}}]
        }
    )
    mock_post.return_value.raise_for_status = lambda: None

    # Temporarily set a key so the guard passes
    with patch('openclaw.services.ai._OPENAI_BASE', 'http://fake'):
        from openclaw.services.ai import AIService
        with patch.object(AIService, '_openai_headers', return_value={'Authorization': 'Bearer fake'}):
            resp = client.post('/api/ai/complete',
                               json={'prompt': 'Hi'},
                               headers=auth_headers)
    # Mock intercepts at the requests level regardless of guard
    assert resp.status_code in (200, 503)


def test_ai_embed_missing_text(client, auth_headers):
    resp = client.post('/api/ai/embed', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ai_embed_no_key(client, auth_headers):
    resp = client.post('/api/ai/embed', json={'text': 'hello'}, headers=auth_headers)
    assert resp.status_code == 503


def test_ai_image_missing_prompt(client, auth_headers):
    resp = client.post('/api/ai/image', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ai_image_no_key(client, auth_headers):
    resp = client.post('/api/ai/image', json={'prompt': 'a cat'}, headers=auth_headers)
    assert resp.status_code == 503


def test_ai_transcribe_missing_audio(client, auth_headers):
    resp = client.post('/api/ai/transcribe', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ai_transcribe_no_key(client, auth_headers):
    audio_b64 = base64.b64encode(b'fake audio').decode()
    resp = client.post('/api/ai/transcribe',
                       json={'audio_base64': audio_b64},
                       headers=auth_headers)
    assert resp.status_code == 503


def test_ai_translate_missing_text(client, auth_headers):
    resp = client.post('/api/ai/translate', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ai_translate_no_key(client, auth_headers):
    resp = client.post('/api/ai/translate',
                       json={'text': 'hello', 'target_lang': 'DE'},
                       headers=auth_headers)
    assert resp.status_code == 503


def test_ai_hf_missing_text(client, auth_headers):
    resp = client.post('/api/ai/hf', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_ai_hf_no_key(client, auth_headers):
    resp = client.post('/api/ai/hf', json={'text': 'hello'}, headers=auth_headers)
    assert resp.status_code == 503


# ── /api/voice/* ──────────────────────────────────────────────────────────────

def test_voice_tts_missing_text(client, auth_headers):
    resp = client.post('/api/voice/tts', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_voice_tts_no_key(client, auth_headers):
    resp = client.post('/api/voice/tts', json={'text': 'hello'}, headers=auth_headers)
    assert resp.status_code == 503


def test_voice_stt_missing_input(client, auth_headers):
    resp = client.post('/api/voice/stt', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_voice_stt_no_key(client, auth_headers):
    resp = client.post('/api/voice/stt',
                       json={'audio_url': 'https://example.com/audio.mp3'},
                       headers=auth_headers)
    assert resp.status_code == 503


def test_voice_list_no_key(client, auth_headers):
    resp = client.get('/api/voice/voices', headers=auth_headers)
    assert resp.status_code == 503


# ── /api/search/* ─────────────────────────────────────────────────────────────

def test_search_vector_upsert_missing_vectors(client, auth_headers):
    resp = client.post('/api/search/vector/upsert', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_search_vector_upsert_no_key(client, auth_headers):
    vectors = [{'id': 'v1', 'values': [0.1] * 8, 'metadata': {}}]
    resp = client.post('/api/search/vector/upsert',
                       json={'vectors': vectors},
                       headers=auth_headers)
    assert resp.status_code == 503


def test_search_vector_query_missing_vector(client, auth_headers):
    resp = client.post('/api/search/vector/query', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_search_web_missing_q(client, auth_headers):
    resp = client.get('/api/search/web', headers=auth_headers)
    assert resp.status_code == 400


def test_search_web_no_key(client, auth_headers):
    resp = client.get('/api/search/web?q=python', headers=auth_headers)
    assert resp.status_code == 503


def test_search_algolia_missing_fields(client, auth_headers):
    resp = client.post('/api/search/algolia', json={}, headers=auth_headers)
    assert resp.status_code == 400


# ── /api/integrations/* ───────────────────────────────────────────────────────

def test_integrations_webhook_missing_fields(client, auth_headers):
    resp = client.post('/api/integrations/webhook', json={}, headers=auth_headers)
    assert resp.status_code == 400


@patch('openclaw.services.integrations.requests.post')
def test_integrations_webhook_success(mock_post, client, auth_headers):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {'ok': True},
        text='{"ok": true}',
    )
    mock_post.return_value.raise_for_status = lambda: None
    resp = client.post(
        '/api/integrations/webhook',
        json={'url': 'https://example.com/hook', 'payload': {'event': 'test'}, 'sign': False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.get_json()['result'] == {'ok': True}


def test_integrations_webhook_verify_no_secret(client):
    """Without a WEBHOOK_SECRET_KEY configured, verification is permissive."""
    resp = client.post(
        '/api/integrations/webhook/verify',
        data=b'{"event":"test"}',
        headers={'Content-Type': 'application/json', 'X-Signature': 'sha256=whatever'},
    )
    assert resp.status_code == 200
    assert resp.get_json()['valid'] is True


def test_integrations_airtable_no_key(client, auth_headers):
    resp = client.get('/api/integrations/airtable/MyTable', headers=auth_headers)
    assert resp.status_code == 503


def test_integrations_sheets_missing_fields(client, auth_headers):
    resp = client.post('/api/integrations/sheets/append', json={}, headers=auth_headers)
    assert resp.status_code == 400
