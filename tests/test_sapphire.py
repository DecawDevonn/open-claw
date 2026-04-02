"""Tests for the Sapphire Cognitive Memory system.

Covers:
- SapphireMemory service (save, search, inject, reflect, delete, list, count)
- save_to_memory tool registration
- AIService.chat() Cognitive Wrapper
- /api/ai/chat, /api/memory/* HTTP endpoints
"""

from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from openclaw.services.sapphire import SapphireMemory
from openclaw.services.ai import AIService
from openclaw.framework.tools import get_default_registry


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
    resp = client.post('/api/auth/register', json={'username': 'sapphire_test'})
    assert resp.status_code == 201
    return resp.get_json()['token']


@pytest.fixture
def auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def memory():
    """A fresh SapphireMemory using the in-process fallback (no ChromaDB required)."""
    with patch('openclaw.services.sapphire._CHROMA_AVAILABLE', False):
        return SapphireMemory(ai_service=None, reflection_interval=0)


# ── SapphireMemory unit tests ──────────────────────────────────────────────────

class TestSapphireMemory:

    def test_save_returns_id(self, memory):
        mid = memory.save("Wesley prefers concise, structured responses.")
        assert isinstance(mid, str)
        assert len(mid) > 0

    def test_save_and_list(self, memory):
        memory.save("First memory")
        memory.save("Second memory")
        entries = memory.list()
        assert len(entries) == 2

    def test_count(self, memory):
        assert memory.count() == 0
        memory.save("alpha")
        memory.save("beta")
        assert memory.count() == 2

    def test_search_returns_list(self, memory):
        memory.save("DEVONN.AI is an autonomous orchestration platform.")
        memory.save("Wesley Little is the Root Operator.")
        results = memory.search("Who is the root operator?")
        assert isinstance(results, list)

    def test_inject_empty_when_no_memories(self, memory):
        block = memory.inject("anything")
        assert block == ""

    def test_inject_nonempty_with_memories(self, memory):
        memory.save("OpenClaw handles agent orchestration.")
        block = memory.inject("What does OpenClaw do?")
        assert "[SAPPHIRE MEMORY" in block

    def test_delete_existing(self, memory):
        mid = memory.save("Temporary memory")
        assert memory.delete(mid) is True
        assert memory.count() == 0

    def test_delete_nonexistent(self, memory):
        assert memory.delete("does-not-exist") is False

    def test_save_with_metadata(self, memory):
        mid = memory.save(
            "Deployment target is edge cluster.",
            weight=1.5,
            tags=["infrastructure"],
            associations=["some-id"],
            memory_type="fact",
        )
        entries = memory.list()
        assert any(e["id"] == mid for e in entries)

    def test_reflect_no_ai_service(self, memory):
        memory.save("memory one")
        memory.save("memory two")
        result = memory.reflect()
        assert result is None  # no AI service

    def test_reflect_with_ai_service(self):
        mock_ai = MagicMock()
        mock_ai.embed.return_value = [0.0] * 128
        mock_ai.complete.return_value = "Summary of memories."
        with patch('openclaw.services.sapphire._CHROMA_AVAILABLE', False):
            mem = SapphireMemory(ai_service=mock_ai, reflection_interval=0)
        mem.save("fact one")
        mem.save("fact two")
        mid = mem.reflect(n=2)
        assert mid is not None
        mock_ai.complete.assert_called_once()

    def test_auto_reflect_triggered(self):
        mock_ai = MagicMock()
        mock_ai.embed.return_value = [0.0] * 128
        mock_ai.complete.return_value = "Auto summary."
        with patch('openclaw.services.sapphire._CHROMA_AVAILABLE', False):
            mem = SapphireMemory(ai_service=mock_ai, reflection_interval=3)
        for i in range(3):
            mem.save(f"memory {i}")
        # After 3 saves the reflection should have been triggered
        mock_ai.complete.assert_called()

    def test_list_limit(self, memory):
        for i in range(10):
            memory.save(f"entry {i}")
        assert len(memory.list(limit=4)) == 4


# ── save_to_memory tool ────────────────────────────────────────────────────────

class TestSaveToMemoryTool:

    def test_tool_registered(self):
        registry = get_default_registry()
        # The tool is registered when create_app() wires the SapphireMemory.
        # create_app() is called in the app fixture above, so it will be present.
        create_app()  # ensure wired
        assert registry.get("save_to_memory") is not None

    def test_tool_invoke(self):
        mock_mem = MagicMock()
        mock_mem.save.return_value = "abc-123"
        from openclaw.framework.tools import ToolRegistry, _SAVE_TO_MEMORY_PARAMS
        reg = ToolRegistry()
        reg.register(
            name="save_to_memory",
            fn=lambda content, weight=1.0, tags=None, **kw: mock_mem.save(content=content),
            description="test",
            parameters=_SAVE_TO_MEMORY_PARAMS,
        )
        result = reg.invoke("save_to_memory", content="test fact")
        mock_mem.save.assert_called_once_with(content="test fact")


# ── AIService.chat() Cognitive Wrapper ────────────────────────────────────────

class TestAIServiceChat:

    def _make_ai(self):
        ai = AIService(openai_api_key="fake-key")
        return ai

    def test_chat_no_memory_service(self):
        ai = self._make_ai()
        with patch.object(ai, 'complete', return_value="Hello!") as mock_complete:
            result = ai.chat(prompt="Hi", memory_service=None)
        assert result['result'] == "Hello!"
        assert result['memories_used'] == []
        assert result['memory_saved_id'] is None

    def test_chat_injects_memories(self):
        ai = self._make_ai()
        mock_mem = MagicMock()
        mock_mem.search.return_value = [{"id": "m1", "content": "fact"}]
        mock_mem.inject.return_value = "[SAPPHIRE MEMORY]\n- fact\n[END MEMORY]"
        mock_mem.save.return_value = "new-id"
        with patch.object(ai, 'complete', return_value="Response") as mock_complete:
            result = ai.chat(prompt="question", memory_service=mock_mem)
        assert "[SAPPHIRE MEMORY]" in mock_complete.call_args[1]['system']
        assert result['result'] == "Response"
        assert result['memories_used'] == [{"id": "m1", "content": "fact"}]
        assert result['memory_saved_id'] == "new-id"

    def test_chat_save_response_false(self):
        ai = self._make_ai()
        mock_mem = MagicMock()
        mock_mem.search.return_value = []
        mock_mem.inject.return_value = ""
        with patch.object(ai, 'complete', return_value="Response"):
            result = ai.chat(prompt="question", memory_service=mock_mem, save_response=False)
        mock_mem.save.assert_not_called()
        assert result['memory_saved_id'] is None


# ── /api/ai/chat endpoint ─────────────────────────────────────────────────────

class TestAIChatEndpoint:

    def test_chat_missing_prompt(self, client, auth_headers):
        resp = client.post('/api/ai/chat', json={}, headers=auth_headers)
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_chat_no_auth(self, client):
        resp = client.post('/api/ai/chat', json={'prompt': 'hi'})
        assert resp.status_code == 401

    def test_chat_no_key(self, client, auth_headers):
        resp = client.post('/api/ai/chat', json={'prompt': 'Hello'}, headers=auth_headers)
        assert resp.status_code in (503, 500)


# ── /api/memory/* endpoints ───────────────────────────────────────────────────

class TestMemoryEndpoints:

    def test_save_no_auth(self, client):
        resp = client.post('/api/memory/save', json={'content': 'test'})
        assert resp.status_code == 401

    def test_save_missing_content(self, client, auth_headers):
        resp = client.post('/api/memory/save', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_save_success(self, client, auth_headers):
        resp = client.post(
            '/api/memory/save',
            json={'content': 'Wesley prefers Python.', 'tags': ['prefs']},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'id' in data
        assert data['status'] == 'saved'

    def test_list_empty(self, client, auth_headers):
        resp = client.get('/api/memory/list', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'memories' in data
        assert isinstance(data['memories'], list)

    def test_list_after_save(self, client, auth_headers):
        client.post('/api/memory/save', json={'content': 'mem one'}, headers=auth_headers)
        client.post('/api/memory/save', json={'content': 'mem two'}, headers=auth_headers)
        resp = client.get('/api/memory/list', headers=auth_headers)
        data = resp.get_json()
        assert data['count'] >= 2

    def test_search_missing_query(self, client, auth_headers):
        resp = client.post('/api/memory/search', json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_search_returns_results(self, client, auth_headers):
        client.post('/api/memory/save', json={'content': 'Telegram is the command interface.'}, headers=auth_headers)
        resp = client.post(
            '/api/memory/search',
            json={'query': 'command interface'},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'results' in data
        assert isinstance(data['results'], list)

    def test_reflect_skipped_when_no_ai(self, client, auth_headers):
        resp = client.post('/api/memory/reflect', json={}, headers=auth_headers)
        assert resp.status_code in (200, 201)

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete('/api/memory/nonexistent-id', headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_success(self, client, auth_headers):
        save_resp = client.post(
            '/api/memory/save',
            json={'content': 'to be deleted'},
            headers=auth_headers,
        )
        mid = save_resp.get_json()['id']
        del_resp = client.delete(f'/api/memory/{mid}', headers=auth_headers)
        assert del_resp.status_code == 200
        assert del_resp.get_json()['status'] == 'deleted'

    def test_list_no_auth(self, client):
        resp = client.get('/api/memory/list')
        assert resp.status_code == 401
