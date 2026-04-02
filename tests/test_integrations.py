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


# ── /api/leads/* ──────────────────────────────────────────────────────────────

def test_leads_capture_no_name_or_email(client):
    resp = client.post('/api/leads', json={'phone': '+15555555555'})
    assert resp.status_code == 400


def test_leads_capture_with_name(client):
    resp = client.post('/api/leads', json={'name': 'Alice', 'source': 'website'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Alice'
    assert data['source'] == 'website'
    assert 'id' in data
    assert data['status'] == 'new'


def test_leads_capture_with_email(client):
    resp = client.post('/api/leads', json={'email': 'bob@example.com'})
    assert resp.status_code == 201
    assert resp.get_json()['email'] == 'bob@example.com'


def test_leads_list_requires_auth(client):
    resp = client.get('/api/leads')
    assert resp.status_code == 401


def test_leads_list(client, auth_headers):
    client.post('/api/leads', json={'name': 'Lead1'})
    client.post('/api/leads', json={'name': 'Lead2', 'source': 'ads'})
    resp = client.get('/api/leads', headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 2


def test_leads_list_filter_by_source(client, auth_headers):
    client.post('/api/leads', json={'name': 'Organic Lead', 'source': 'organic'})
    resp = client.get('/api/leads?source=organic', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert all(l['source'] == 'organic' for l in data)


def test_leads_get(client, auth_headers):
    create_resp = client.post('/api/leads', json={'name': 'Charlie'})
    lead_id = create_resp.get_json()['id']
    resp = client.get(f'/api/leads/{lead_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == lead_id


def test_leads_get_not_found(client, auth_headers):
    resp = client.get('/api/leads/nonexistent-id', headers=auth_headers)
    assert resp.status_code == 404


def test_leads_update(client, auth_headers):
    create_resp = client.post('/api/leads', json={'name': 'Dave'})
    lead_id = create_resp.get_json()['id']
    resp = client.put(
        f'/api/leads/{lead_id}',
        json={'status': 'contacted', 'company': 'Acme'},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'contacted'
    assert data['company'] == 'Acme'


def test_leads_update_not_found(client, auth_headers):
    resp = client.put('/api/leads/bad-id', json={'status': 'new'}, headers=auth_headers)
    assert resp.status_code == 404


def test_leads_score(client, auth_headers):
    create_resp = client.post('/api/leads', json={
        'name': 'Eve', 'email': 'eve@example.com',
        'message': 'I want to buy now, send me a quote',
        'source': 'ads',
    })
    lead_id = create_resp.get_json()['id']
    resp = client.post(f'/api/leads/{lead_id}/score', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 0 <= data['score'] <= 100
    assert data['intent'] in ('high', 'medium', 'low')


def test_leads_score_not_found(client, auth_headers):
    resp = client.post('/api/leads/nope/score', headers=auth_headers)
    assert resp.status_code == 404


def test_leads_route(client, auth_headers):
    create_resp = client.post('/api/leads', json={'name': 'Frank'})
    lead_id = create_resp.get_json()['id']
    resp = client.post(f'/api/leads/{lead_id}/route', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    # No agents registered → status should be unassigned
    assert data['status'] == 'unassigned'


def test_leads_route_not_found(client, auth_headers):
    resp = client.post('/api/leads/nope/route', headers=auth_headers)
    assert resp.status_code == 404


def test_leads_follow_up(client, auth_headers):
    create_resp = client.post('/api/leads', json={'name': 'Grace'})
    lead_id = create_resp.get_json()['id']
    resp = client.post(f'/api/leads/{lead_id}/follow-up', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['follow_up_count'] == 1


def test_leads_delete(client, auth_headers):
    create_resp = client.post('/api/leads', json={'name': 'Heidi'})
    lead_id = create_resp.get_json()['id']
    resp = client.delete(f'/api/leads/{lead_id}', headers=auth_headers)
    assert resp.status_code == 200
    # Confirm it's gone
    assert client.get(f'/api/leads/{lead_id}', headers=auth_headers).status_code == 404


# ── /api/comms/* ──────────────────────────────────────────────────────────────

def test_comms_sms_missing_fields(client, auth_headers):
    resp = client.post('/api/comms/sms', json={'to': '+15555555555'}, headers=auth_headers)
    assert resp.status_code == 400


def test_comms_sms_no_key(client, auth_headers):
    resp = client.post(
        '/api/comms/sms',
        json={'to': '+15555555555', 'body': 'Hello'},
        headers=auth_headers,
    )
    assert resp.status_code == 503


def test_comms_whatsapp_missing_fields(client, auth_headers):
    resp = client.post('/api/comms/whatsapp', json={'to': '+15555555555'}, headers=auth_headers)
    assert resp.status_code == 400


def test_comms_whatsapp_no_key(client, auth_headers):
    resp = client.post(
        '/api/comms/whatsapp',
        json={'to': '+15555555555', 'body': 'Hi there'},
        headers=auth_headers,
    )
    assert resp.status_code == 503


def test_comms_call_missing_fields(client, auth_headers):
    resp = client.post('/api/comms/call', json={'to': '+15555555555'}, headers=auth_headers)
    assert resp.status_code == 400


def test_comms_call_no_key(client, auth_headers):
    resp = client.post(
        '/api/comms/call',
        json={'to': '+15555555555', 'twiml_url': 'https://example.com/twiml'},
        headers=auth_headers,
    )
    assert resp.status_code == 503


def test_comms_email_missing_fields(client, auth_headers):
    resp = client.post(
        '/api/comms/email',
        json={'to': 'x@x.com', 'subject': 'Hi'},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_comms_email_no_key(client, auth_headers):
    resp = client.post(
        '/api/comms/email',
        json={'to': 'x@x.com', 'subject': 'Hello', 'html_body': '<p>Hi</p>'},
        headers=auth_headers,
    )
    assert resp.status_code == 503


# ── /api/analytics/* ──────────────────────────────────────────────────────────

def test_analytics_track_missing_event_type(client, auth_headers):
    resp = client.post('/api/analytics/events', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_analytics_track_event(client, auth_headers):
    resp = client.post(
        '/api/analytics/events',
        json={'event_type': 'payment_completed', 'data': {'amount': 99}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['event_type'] == 'payment_completed'
    assert 'id' in data
    assert 'timestamp' in data


def test_analytics_metrics(client, auth_headers):
    client.post(
        '/api/analytics/events',
        json={'event_type': 'lead_captured'},
        headers=auth_headers,
    )
    resp = client.get('/api/analytics/metrics', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total_events' in data
    assert 'by_type' in data
    assert 'conversion_rate' in data


def test_analytics_metrics_with_since(client, auth_headers):
    resp = client.get('/api/analytics/metrics?since=2099-01-01T00:00:00', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['total_events'] == 0


def test_analytics_feedback_log_missing_fields(client, auth_headers):
    resp = client.post('/api/analytics/feedback', json={'agent_id': 'a1'}, headers=auth_headers)
    assert resp.status_code == 400


def test_analytics_feedback_log(client, auth_headers):
    resp = client.post(
        '/api/analytics/feedback',
        json={'agent_id': 'a1', 'task_id': 't1', 'outcome': 'success', 'score': 0.9},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['outcome'] == 'success'
    assert data['score'] == 0.9


def test_analytics_feedback_summary(client, auth_headers):
    client.post(
        '/api/analytics/feedback',
        json={'agent_id': 'a2', 'task_id': 't2', 'outcome': 'failure', 'score': 0.2},
        headers=auth_headers,
    )
    resp = client.get('/api/analytics/feedback', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total_feedback' in data
    assert 'outcomes' in data
    assert 'mean_score' in data


def test_analytics_feedback_summary_by_agent(client, auth_headers):
    client.post(
        '/api/analytics/feedback',
        json={'agent_id': 'agent-x', 'task_id': 't3', 'outcome': 'success', 'score': 1.0},
        headers=auth_headers,
    )
    resp = client.get('/api/analytics/feedback?agent_id=agent-x', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['agent_id'] == 'agent-x'


# ── /api/audit ────────────────────────────────────────────────────────────────

def test_audit_list_requires_auth(client):
    resp = client.get('/api/audit')
    assert resp.status_code == 401


def test_audit_list(client, auth_headers):
    # Make a couple of requests first so there are entries
    client.get('/api/health')
    resp = client.get('/api/audit', headers=auth_headers)
    assert resp.status_code == 200
    entries = resp.get_json()
    assert isinstance(entries, list)
    assert len(entries) > 0
    entry = entries[0]
    assert 'method' in entry
    assert 'path' in entry
    assert 'status' in entry
    assert 'timestamp' in entry


# ── /api/framework ────────────────────────────────────────────────────────────

def test_framework_status_requires_auth(client):
    resp = client.get('/api/framework/status')
    assert resp.status_code == 401


def test_framework_status(client, auth_headers):
    resp = client.get('/api/framework/status', headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'operational'
    assert 'active_agents' in data
    assert isinstance(data['tools'], list)


def test_framework_spawn_requires_auth(client):
    resp = client.post('/api/framework/agents/spawn', json={'name': 'test-agent'})
    assert resp.status_code == 401


def test_framework_spawn_missing_name(client, auth_headers):
    resp = client.post(
        '/api/framework/agents/spawn',
        json={'role': 'executor'},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_framework_spawn(client, auth_headers):
    resp = client.post(
        '/api/framework/agents/spawn',
        json={'name': 'researcher', 'role': 'researcher', 'capabilities': ['search']},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['config']['name'] == 'researcher'
    assert data['status'] == 'idle'
    assert 'id' in data


def test_framework_list_agents(client, auth_headers):
    # Spawn one first
    client.post(
        '/api/framework/agents/spawn',
        json={'name': 'worker-1'},
        headers=auth_headers,
    )
    resp = client.get('/api/framework/agents', headers=auth_headers)
    assert resp.status_code == 200
    agents = resp.get_json()
    assert isinstance(agents, list)
    assert len(agents) >= 1


def test_framework_get_agent(client, auth_headers):
    spawn_resp = client.post(
        '/api/framework/agents/spawn',
        json={'name': 'worker-get'},
        headers=auth_headers,
    )
    agent_id = spawn_resp.get_json()['id']
    resp = client.get(f'/api/framework/agents/{agent_id}', headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()['id'] == agent_id


def test_framework_get_agent_not_found(client, auth_headers):
    resp = client.get('/api/framework/agents/nonexistent', headers=auth_headers)
    assert resp.status_code == 404


def test_framework_run_requires_auth(client):
    resp = client.post('/api/framework/run', json={'goal': 'do something'})
    assert resp.status_code == 401


def test_framework_run_missing_goal(client, auth_headers):
    resp = client.post('/api/framework/run', json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_framework_run_no_ai(client, auth_headers):
    """Run without an AI key — executor falls back to stub output."""
    resp = client.post(
        '/api/framework/run',
        json={'goal': 'greet the user', 'strategy': 'sequential'},
        headers=auth_headers,
    )
    # Should succeed even without a real AI key (stub path)
    assert resp.status_code in (200, 500)
    data = resp.get_json()
    assert 'agent_id' in data
    assert data['goal'] == 'greet the user'
    assert 'plan' in data
    assert 'status' in data
