from flask import Flask, jsonify, request, g
from datetime import datetime, timezone
import uuid
import logging
import base64

from openclaw.config import settings
from openclaw.services.ai import AIService
from openclaw.services.auth import AuthService, require_auth
from openclaw.services.voice import VoiceService
from openclaw.services.search import SearchService
from openclaw.services.integrations import IntegrationsService
from openclaw.services.leads import LeadsService
from openclaw.services.comms import CommsService
from openclaw.services.analytics import AnalyticsService
from openclaw.services.monitoring import init_monitoring, health_payload
from openclaw.services.sapphire import SapphireMemory
from openclaw.framework.tools import register_save_to_memory
from storage import get_storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings.warn_insecure_defaults()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)

    # Storage backend — MongoStorage when MONGO_URL is set, else InMemoryStorage
    _store = get_storage(mongo_url=settings.mongo_url)

    # ── Initialise integrations ───────────────────────────────────────────────
    init_monitoring(settings.sentry_dsn)

    _ai = AIService(
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        openai_embedding_model=settings.openai_embedding_model,
        hf_api_token=settings.hf_api_token,
        hf_model=settings.hf_model,
        stability_api_key=settings.stability_api_key,
        deepl_api_key=settings.deepl_api_key,
    )
    _auth = AuthService(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expiry_hours=settings.jwt_expiry_hours,
        storage=_store,
    )
    _voice = VoiceService(
        elevenlabs_api_key=settings.elevenlabs_api_key,
        elevenlabs_voice_id=settings.elevenlabs_voice_id,
        assemblyai_api_key=settings.assemblyai_api_key,
    )
    _search = SearchService(
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_environment=settings.pinecone_environment,
        pinecone_index=settings.pinecone_index,
        serpapi_key=settings.serpapi_key,
        algolia_api_key=settings.algolia_api_key,
        algolia_app_id=settings.algolia_app_id,
    )
    _integrations = IntegrationsService(
        webhook_secret_key=settings.webhook_secret_key,
        pabbly_api_key=settings.pabbly_api_key,
        airtable_api_key=settings.airtable_api_key,
        airtable_base_id=settings.airtable_base_id,
        google_sheets_api_key=settings.google_sheets_api_key,
    )
    _leads = LeadsService(storage=_store, ai_service=_ai)
    _comms = CommsService(
        twilio_account_sid=settings.twilio_account_sid,
        twilio_auth_token=settings.twilio_auth_token,
        twilio_from_number=settings.twilio_from_number,
        twilio_whatsapp_from=settings.twilio_whatsapp_from,
        sendgrid_api_key=settings.sendgrid_api_key,
        sendgrid_from_email=settings.sendgrid_from_email,
    )
    _analytics = AnalyticsService(storage=_store)

    # ── Sapphire Cognitive Memory ─────────────────────────────────────────────
    _memory = SapphireMemory(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
        ai_service=_ai,
        top_k=settings.sapphire_memory_top_k,
        reflection_interval=settings.sapphire_reflection_interval,
    )
    register_save_to_memory(_memory)

    # Register AuthService on the app so require_auth can reach it
    app.extensions["auth_service"] = _auth

    # ── Audit-log middleware ──────────────────────────────────────────────────

    @app.after_request
    def _audit_log(response):
        """Record every non-static request to the audit log."""
        try:
            actor = getattr(g, "current_user", {})
            actor_id = actor.get("id") if isinstance(actor, dict) else None
            entry = {
                "id": str(uuid.uuid4()),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "actor_id": actor_id,
                "remote_addr": request.remote_addr,
                "timestamp": _now(),
            }
            _store.save_audit_entry(entry)
        except Exception:
            pass  # never let audit logging break a response
        return response

    # ============================================
    # Agent Management Endpoints
    # ============================================

    @app.route('/api/agents', methods=['POST'])
    def create_agent():
        """Create a new agent"""
        try:
            data = request.json
            agent_id = str(uuid.uuid4())

            agent = {
                'id': agent_id,
                'name': data.get('name', 'Agent'),
                'type': data.get('type', 'generic'),
                'status': 'idle',
                'created_at': _now(),
                'capabilities': data.get('capabilities', []),
                'tasks_completed': 0
            }

            _store.save_agent(agent)
            logger.info(f"Created agent: {agent_id}")
            return jsonify(agent), 201
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/agents', methods=['GET'])
    def list_agents():
        """List all agents"""
        return jsonify(_store.list_agents()), 200

    @app.route('/api/agents/<agent_id>', methods=['GET'])
    def get_agent(agent_id):
        """Get details of a specific agent"""
        agent = _store.get_agent(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        return jsonify(agent), 200

    @app.route('/api/agents/<agent_id>', methods=['PUT'])
    def update_agent(agent_id):
        """Update agent status or properties"""
        try:
            agent = _store.get_agent(agent_id)
            if not agent:
                return jsonify({'error': 'Agent not found'}), 404

            data = request.json

            if 'status' in data:
                agent['status'] = data['status']
            if 'capabilities' in data:
                agent['capabilities'] = data['capabilities']

            _store.save_agent(agent)
            logger.info(f"Updated agent: {agent_id}")
            return jsonify(agent), 200
        except Exception as e:
            logger.error(f"Error updating agent: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/agents/<agent_id>', methods=['DELETE'])
    def delete_agent(agent_id):
        """Delete an agent"""
        if not _store.delete_agent(agent_id):
            return jsonify({'error': 'Agent not found'}), 404

        logger.info(f"Deleted agent: {agent_id}")
        return jsonify({'message': 'Agent deleted'}), 200

    # ============================================
    # Task Management Endpoints
    # ============================================

    @app.route('/api/tasks', methods=['POST'])
    def submit_task():
        """Submit a new task"""
        try:
            data = request.json
            task_id = str(uuid.uuid4())

            task = {
                'id': task_id,
                'name': data.get('name', 'Unnamed Task'),
                'description': data.get('description', ''),
                'agent_id': data.get('agent_id'),
                'status': 'pending',
                'priority': data.get('priority', 'normal'),
                'created_at': _now(),
                'started_at': None,
                'completed_at': None,
                'result': None
            }

            _store.save_task(task)
            logger.info(f"Created task: {task_id}")
            return jsonify(task), 201
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/tasks', methods=['GET'])
    def list_tasks():
        """List all tasks with optional filtering"""
        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent_id')

        filtered_tasks = _store.list_tasks()

        if status_filter:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == status_filter]
        if agent_filter:
            filtered_tasks = [t for t in filtered_tasks if t['agent_id'] == agent_filter]

        return jsonify(filtered_tasks), 200

    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """Get details of a specific task"""
        task = _store.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task), 200

    @app.route('/api/tasks/<task_id>', methods=['PUT'])
    def update_task(task_id):
        """Update task status or result"""
        try:
            task = _store.get_task(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404

            data = request.json

            if 'status' in data:
                task['status'] = data['status']
                if data['status'] == 'running':
                    task['started_at'] = _now()
                elif data['status'] == 'completed':
                    task['completed_at'] = _now()

            if 'result' in data:
                task['result'] = data['result']

            _store.save_task(task)
            logger.info(f"Updated task: {task_id}")
            return jsonify(task), 200
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """Delete a task"""
        if not _store.delete_task(task_id):
            return jsonify({'error': 'Task not found'}), 404

        logger.info(f"Deleted task: {task_id}")
        return jsonify({'message': 'Task deleted'}), 200

    # ============================================
    # Status & Health Endpoints
    # ============================================

    @app.route('/api/status', methods=['GET'])
    def status():
        """Get system status"""
        all_tasks = _store.list_tasks()
        all_agents = _store.list_agents()
        running_tasks = sum(1 for t in all_tasks if t['status'] == 'running')
        completed_tasks = sum(1 for t in all_tasks if t['status'] == 'completed')
        idle_agents = sum(1 for a in all_agents if a['status'] == 'idle')

        return jsonify({
            'status': 'running',
            'timestamp': _now(),
            'agents': {
                'total': len(all_agents),
                'idle': idle_agents,
                'active': len(all_agents) - idle_agents
            },
            'tasks': {
                'total': len(all_tasks),
                'running': running_tasks,
                'completed': completed_tasks,
                'pending': len(all_tasks) - running_tasks - completed_tasks
            }
        }), 200

    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        payload = health_payload(settings.configured_services())
        payload['timestamp'] = _now()
        payload['uptime'] = 'running'
        return jsonify(payload), 200

    # ============================================
    # Workforce Management Endpoints
    # ============================================

    @app.route('/api/workforce/assign', methods=['POST'])
    def assign_task_to_agent():
        """Assign a task to an agent"""
        try:
            data = request.json
            task_id = data.get('task_id')
            agent_id = data.get('agent_id')

            task = _store.get_task(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404
            agent = _store.get_agent(agent_id)
            if not agent:
                return jsonify({'error': 'Agent not found'}), 404

            task['agent_id'] = agent_id
            task['status'] = 'assigned'
            agent['status'] = 'busy'

            _store.save_task(task)
            _store.save_agent(agent)
            logger.info(f"Assigned task {task_id} to agent {agent_id}")
            return jsonify({'task': task, 'agent': agent}), 200
        except Exception as e:
            logger.error(f"Error assigning task: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/workforce/summary', methods=['GET'])
    def workforce_summary():
        """Get workforce summary and statistics"""
        all_agents = _store.list_agents()
        all_tasks = _store.list_tasks()
        agent_capabilities = {}
        for agent in all_agents:
            for cap in agent.get('capabilities', []):
                if cap not in agent_capabilities:
                    agent_capabilities[cap] = 0
                agent_capabilities[cap] += 1

        return jsonify({
            'agents_count': len(all_agents),
            'tasks_count': len(all_tasks),
            'capabilities': agent_capabilities,
            'agents': all_agents,
            'tasks': all_tasks
        }), 200

    # ============================================
    # Auth Endpoints
    # ============================================

    @app.route('/api/auth/register', methods=['POST'])
    def auth_register():
        """Register a new user and return a JWT."""
        try:
            data = request.json or {}
            username = data.get('username', '').strip()
            if not username:
                return jsonify({'error': 'username is required'}), 400
            if _store.get_user_by_username(username):
                return jsonify({'error': 'Username already exists'}), 409
            user_id = str(uuid.uuid4())
            user = {'id': user_id, 'username': username, 'created_at': _now()}
            _store.save_user(user)
            token = _auth.issue_token(user_id, {'username': username})
            logger.info(f"Registered user: {user_id}")
            return jsonify({'token': token, 'user': user}), 201
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return jsonify({'error': str(e)}), 400

    @app.route('/api/auth/token', methods=['POST'])
    def auth_token():
        """Issue a JWT for an existing user (by user_id)."""
        try:
            data = request.json or {}
            user_id = data.get('user_id', '').strip()
            if not _store.get_user(user_id):
                return jsonify({'error': 'User not found'}), 404
            token = _auth.issue_token(user_id)
            return jsonify({'token': token}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/auth/me', methods=['GET'])
    @require_auth
    def auth_me():
        """Return the claims for the authenticated token."""
        return jsonify(g.user), 200

    @app.route('/api/auth/revoke', methods=['POST'])
    @require_auth
    def auth_revoke():
        """Revoke the current Bearer token."""
        try:
            token = request.headers['Authorization'][len("Bearer "):]
            _auth.revoke_token(token)
            return jsonify({'message': 'Token revoked'}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 501
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    # ============================================
    # AI / NLP Endpoints
    # ============================================

    @app.route('/api/ai/complete', methods=['POST'])
    @require_auth
    def ai_complete():
        """Chat completion via OpenAI."""
        try:
            data = request.json or {}
            prompt = data.get('prompt', '')
            if not prompt:
                return jsonify({'error': 'prompt is required'}), 400
            result = _ai.complete(
                prompt=prompt,
                system=data.get('system', 'You are a helpful AI assistant.'),
                max_tokens=int(data.get('max_tokens', 1024)),
                temperature=float(data.get('temperature', 0.7)),
                model=data.get('model'),
            )
            return jsonify({'result': result}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI complete error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/embed', methods=['POST'])
    @require_auth
    def ai_embed():
        """Generate an embedding vector via OpenAI."""
        try:
            data = request.json or {}
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'text is required'}), 400
            vector = _ai.embed(text=text, model=data.get('model'))
            return jsonify({'embedding': vector, 'dimensions': len(vector)}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI embed error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/image', methods=['POST'])
    @require_auth
    def ai_image():
        """Generate images via DALL·E or StabilityAI."""
        try:
            data = request.json or {}
            prompt = data.get('prompt', '')
            if not prompt:
                return jsonify({'error': 'prompt is required'}), 400
            provider = data.get('provider', 'openai').lower()
            if provider == 'stability':
                images = _ai.stability_generate(
                    prompt=prompt,
                    engine=data.get('engine', 'stable-diffusion-xl-1024-v1-0'),
                )
                return jsonify({'provider': 'stability', 'images_base64': images}), 200
            urls = _ai.generate_image(
                prompt=prompt,
                size=data.get('size', '1024x1024'),
                n=int(data.get('n', 1)),
            )
            return jsonify({'provider': 'openai', 'urls': urls}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI image error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/transcribe', methods=['POST'])
    @require_auth
    def ai_transcribe():
        """Transcribe audio via Whisper (file upload as base64 or JSON field)."""
        try:
            data = request.json or {}
            audio_b64 = data.get('audio_base64', '')
            if not audio_b64:
                return jsonify({'error': 'audio_base64 is required'}), 400
            audio_bytes = base64.b64decode(audio_b64)
            text = _ai.transcribe(audio_bytes, filename=data.get('filename', 'audio.mp3'))
            return jsonify({'transcript': text}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI transcribe error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/translate', methods=['POST'])
    @require_auth
    def ai_translate():
        """Translate text via DeepL."""
        try:
            data = request.json or {}
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'text is required'}), 400
            translated = _ai.translate(
                text=text,
                target_lang=data.get('target_lang', 'EN-US'),
                source_lang=data.get('source_lang'),
            )
            return jsonify({'translated': translated}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI translate error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/hf', methods=['POST'])
    @require_auth
    def ai_hf():
        """Run HuggingFace inference."""
        try:
            data = request.json or {}
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'text is required'}), 400
            result = _ai.hf_infer(text=text, model=data.get('model'))
            return jsonify({'result': result}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"HuggingFace infer error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/chat', methods=['POST'])
    @require_auth
    def ai_chat():
        """Sapphire Cognitive Wrapper — memory-augmented chat completion.

        Retrieves relevant memories, injects them into the system prompt,
        calls the LLM, and saves the response back to memory.
        """
        try:
            data = request.json or {}
            prompt = data.get('prompt', '')
            if not prompt:
                return jsonify({'error': 'prompt is required'}), 400
            result = _ai.chat(
                prompt=prompt,
                system=data.get('system', 'You are DEVONN.AI, a helpful autonomous AI assistant.'),
                max_tokens=int(data.get('max_tokens', 1024)),
                temperature=float(data.get('temperature', 0.7)),
                model=data.get('model'),
                memory_service=_memory,
                save_response=bool(data.get('save_response', True)),
                memory_format=data.get('memory_format'),
            )
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    # ============================================
    # Sapphire Memory Endpoints
    # ============================================

    @app.route('/api/memory/save', methods=['POST'])
    @require_auth
    def memory_save():
        """Save a memory entry to the Sapphire vector store."""
        try:
            data = request.json or {}
            content = data.get('content', '')
            if not content:
                return jsonify({'error': 'content is required'}), 400
            mid = _memory.save(
                content=content,
                weight=float(data.get('weight', 1.0)),
                tags=data.get('tags', []),
                associations=data.get('associations', []),
                memory_type=data.get('type', 'memory'),
            )
            return jsonify({'id': mid, 'status': 'saved'}), 201
        except Exception as e:
            logger.error(f"Memory save error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    @app.route('/api/memory/search', methods=['POST'])
    @require_auth
    def memory_search():
        """Semantic search over stored memories."""
        try:
            data = request.json or {}
            query = data.get('query', '')
            if not query:
                return jsonify({'error': 'query is required'}), 400
            results = _memory.search(query, n=int(data.get('n', settings.sapphire_memory_top_k)))
            return jsonify({'results': results, 'count': len(results)}), 200
        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    @app.route('/api/memory/list', methods=['GET'])
    @require_auth
    def memory_list():
        """Return the most-recent memories."""
        try:
            limit = int(request.args.get('limit', 50))
            memories = _memory.list(limit=limit)
            return jsonify({'memories': memories, 'count': len(memories), 'total': _memory.count()}), 200
        except Exception as e:
            logger.error(f"Memory list error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    @app.route('/api/memory/reflect', methods=['POST'])
    @require_auth
    def memory_reflect():
        """Trigger a Sapphire reflection — summarise recent memories."""
        try:
            data = request.json or {}
            n = int(data.get('n', 5))
            mid = _memory.reflect(n=n)
            if mid is None:
                return jsonify({'status': 'skipped', 'reason': 'insufficient memories or no AI service'}), 200
            return jsonify({'status': 'reflected', 'memory_id': mid}), 201
        except Exception as e:
            logger.error(f"Memory reflect error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    @app.route('/api/memory/<memory_id>', methods=['DELETE'])
    @require_auth
    def memory_delete(memory_id):
        """Delete a memory entry by id."""
        try:
            deleted = _memory.delete(memory_id)
            if not deleted:
                return jsonify({'error': 'memory not found'}), 404
            return jsonify({'status': 'deleted', 'id': memory_id}), 200
        except Exception as e:
            logger.error(f"Memory delete error: {e}")
            return jsonify({'error': 'An internal error occurred.'}), 500

    # ============================================
    # Voice Endpoints
    # ============================================

    @app.route('/api/voice/tts', methods=['POST'])
    @require_auth
    def voice_tts():
        """Convert text to speech via ElevenLabs. Returns base64-encoded MP3."""
        try:
            data = request.json or {}
            text = data.get('text', '')
            if not text:
                return jsonify({'error': 'text is required'}), 400
            audio_bytes = _voice.text_to_speech(
                text=text,
                voice_id=data.get('voice_id'),
                model_id=data.get('model_id', 'eleven_multilingual_v2'),
                stability=float(data.get('stability', 0.5)),
                similarity_boost=float(data.get('similarity_boost', 0.75)),
            )
            return jsonify({
                'audio_base64': base64.b64encode(audio_bytes).decode(),
                'content_type': 'audio/mpeg',
            }), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/voice/voices', methods=['GET'])
    @require_auth
    def voice_list():
        """List available ElevenLabs voices."""
        try:
            return jsonify({'voices': _voice.list_voices()}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/voice/stt', methods=['POST'])
    @require_auth
    def voice_stt():
        """Transcribe audio via AssemblyAI (accepts audio_url or audio_base64)."""
        try:
            data = request.json or {}
            if 'audio_url' in data:
                result = _voice.transcribe_url(
                    audio_url=data['audio_url'],
                    speaker_labels=bool(data.get('speaker_labels', False)),
                    sentiment_analysis=bool(data.get('sentiment_analysis', False)),
                    auto_chapters=bool(data.get('auto_chapters', False)),
                )
            elif 'audio_base64' in data:
                audio_bytes = base64.b64decode(data['audio_base64'])
                result = _voice.transcribe_bytes(audio_bytes)
            else:
                return jsonify({'error': 'audio_url or audio_base64 is required'}), 400
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"STT error: {e}")
            return jsonify({'error': str(e)}), 500

    # ============================================
    # Search Endpoints
    # ============================================

    @app.route('/api/search/vector/upsert', methods=['POST'])
    @require_auth
    def search_vector_upsert():
        """Upsert vectors into Pinecone."""
        try:
            data = request.json or {}
            vectors = data.get('vectors')
            if not vectors:
                return jsonify({'error': 'vectors is required'}), 400
            result = _search.vector_upsert(vectors, namespace=data.get('namespace', ''))
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Vector upsert error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/search/vector/query', methods=['POST'])
    @require_auth
    def search_vector_query():
        """Query Pinecone for nearest-neighbour vectors."""
        try:
            data = request.json or {}
            vector = data.get('vector')
            if not vector:
                return jsonify({'error': 'vector is required'}), 400
            result = _search.vector_query(
                vector=vector,
                top_k=int(data.get('top_k', 5)),
                namespace=data.get('namespace', ''),
                include_metadata=bool(data.get('include_metadata', True)),
                filter=data.get('filter'),
            )
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Vector query error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/search/web', methods=['GET'])
    @require_auth
    def search_web():
        """Perform a web search via SerpAPI."""
        try:
            query = request.args.get('q', '').strip()
            if not query:
                return jsonify({'error': 'q query parameter is required'}), 400
            result = _search.web_search(
                query=query,
                num=int(request.args.get('num', 10)),
                engine=request.args.get('engine', 'google'),
            )
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/search/algolia', methods=['POST'])
    @require_auth
    def search_algolia():
        """Search an Algolia index."""
        try:
            data = request.json or {}
            index = data.get('index', '').strip()
            query = data.get('query', '').strip()
            if not index or not query:
                return jsonify({'error': 'index and query are required'}), 400
            result = _search.algolia_search(
                index=index,
                query=query,
                hits_per_page=int(data.get('hits_per_page', 20)),
            )
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Algolia search error: {e}")
            return jsonify({'error': str(e)}), 500

    # ============================================
    # Integration Endpoints
    # ============================================

    @app.route('/api/integrations/webhook', methods=['POST'])
    @require_auth
    def integrations_webhook():
        """Relay a JSON payload to an external webhook URL."""
        try:
            data = request.json or {}
            url = data.get('url', '').strip()
            payload = data.get('payload')
            if not url or payload is None:
                return jsonify({'error': 'url and payload are required'}), 400
            result = _integrations.send_webhook(
                url=url, payload=payload, sign=bool(data.get('sign', True))
            )
            return jsonify({'result': result}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Webhook relay error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/integrations/webhook/verify', methods=['POST'])
    def integrations_webhook_verify():
        """Verify an inbound webhook HMAC-SHA256 signature."""
        sig = request.headers.get('X-Signature', '')
        valid = _integrations.verify_webhook_signature(request.data, sig)
        return jsonify({'valid': valid}), 200

    @app.route('/api/integrations/airtable/<table>', methods=['GET'])
    @require_auth
    def integrations_airtable_list(table):
        """List records from an Airtable table."""
        try:
            records = _integrations.airtable_list(
                table=table, max_records=int(request.args.get('max_records', 100))
            )
            return jsonify({'records': records}), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Airtable list error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/integrations/airtable/<table>', methods=['POST'])
    @require_auth
    def integrations_airtable_create(table):
        """Create a record in an Airtable table."""
        try:
            data = request.json or {}
            fields = data.get('fields')
            if not fields:
                return jsonify({'error': 'fields is required'}), 400
            record = _integrations.airtable_create(table=table, fields=fields)
            return jsonify(record), 201
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Airtable create error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/integrations/sheets/append', methods=['POST'])
    @require_auth
    def integrations_sheets_append():
        """Append rows to a Google Sheet."""
        try:
            data = request.json or {}
            spreadsheet_id = data.get('spreadsheet_id', '').strip()
            range_ = data.get('range', '').strip()
            values = data.get('values')
            if not spreadsheet_id or not range_ or values is None:
                return jsonify({'error': 'spreadsheet_id, range, and values are required'}), 400
            result = _integrations.sheets_append(
                spreadsheet_id=spreadsheet_id, range_=range_, values=values
            )
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Sheets append error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/integrations/services', methods=['GET'])
    def integrations_services():
        """List which external service integrations are currently configured."""
        return jsonify({'configured': settings.configured_services()}), 200

    # ============================================
    # Lead Management Endpoints
    # ============================================

    @app.route('/api/leads', methods=['POST'])
    def leads_capture():
        """Capture a new inbound lead."""
        try:
            data = request.json or {}
            if not data.get('name') and not data.get('email'):
                return jsonify({'error': 'name or email is required'}), 400
            lead = _leads.capture(data)
            _analytics.track_event('lead_captured', {'lead_id': lead['id'], 'source': lead['source']})
            return jsonify(lead), 201
        except Exception as e:
            logger.error(f"Lead capture error: {e}")
            return jsonify({'error': 'Lead capture failed'}), 400

    @app.route('/api/leads', methods=['GET'])
    @require_auth
    def leads_list():
        """List leads with optional status/source filters."""
        status = request.args.get('status')
        source = request.args.get('source')
        return jsonify(_leads.list(status=status, source=source)), 200

    @app.route('/api/leads/<lead_id>', methods=['GET'])
    @require_auth
    def leads_get(lead_id):
        """Get a specific lead by ID."""
        lead = _leads.get(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        return jsonify(lead), 200

    @app.route('/api/leads/<lead_id>', methods=['PUT'])
    @require_auth
    def leads_update(lead_id):
        """Update lead fields."""
        try:
            data = request.json or {}
            lead = _leads.update(lead_id, data)
            if not lead:
                return jsonify({'error': 'Lead not found'}), 404
            return jsonify(lead), 200
        except Exception as e:
            logger.error(f"Lead update error: {e}")
            return jsonify({'error': 'Lead update failed'}), 400

    @app.route('/api/leads/<lead_id>/score', methods=['POST'])
    @require_auth
    def leads_score(lead_id):
        """AI-score a lead for quality and purchase intent."""
        try:
            lead = _leads.score(lead_id)
            _analytics.track_event(
                'lead_scored',
                {'lead_id': lead_id, 'score': lead['score'], 'intent': lead['intent']},
            )
            return jsonify(lead), 200
        except KeyError:
            return jsonify({'error': 'Lead not found'}), 404
        except Exception as e:
            logger.error(f"Lead scoring error: {e}")
            return jsonify({'error': 'Lead scoring failed'}), 500

    @app.route('/api/leads/<lead_id>/route', methods=['POST'])
    @require_auth
    def leads_route(lead_id):
        """Route a lead to the best available agent."""
        try:
            lead = _leads.route(lead_id)
            _analytics.track_event('lead_routed', {'lead_id': lead_id, 'agent_id': lead.get('assigned_agent')})
            return jsonify(lead), 200
        except KeyError:
            return jsonify({'error': 'Lead not found'}), 404
        except Exception as e:
            logger.error(f"Lead routing error: {e}")
            return jsonify({'error': 'Lead routing failed'}), 500

    @app.route('/api/leads/<lead_id>/follow-up', methods=['POST'])
    @require_auth
    def leads_follow_up(lead_id):
        """Record a follow-up interaction for a lead."""
        lead = _leads.record_follow_up(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        _analytics.track_event('follow_up_sent', {'lead_id': lead_id})
        return jsonify(lead), 200

    @app.route('/api/leads/<lead_id>', methods=['DELETE'])
    @require_auth
    def leads_delete(lead_id):
        """Delete a lead."""
        if not _leads.delete(lead_id):
            return jsonify({'error': 'Lead not found'}), 404
        return jsonify({'message': 'Lead deleted'}), 200

    # ============================================
    # Communications Endpoints
    # ============================================

    @app.route('/api/comms/sms', methods=['POST'])
    @require_auth
    def comms_sms():
        """Send an SMS via Twilio."""
        try:
            data = request.json or {}
            to = data.get('to', '').strip()
            body = data.get('body', '').strip()
            if not to or not body:
                return jsonify({'error': 'to and body are required'}), 400
            result = _comms.send_sms(to=to, body=body)
            _analytics.track_event('sms_sent', {'to': to})
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return jsonify({'error': 'SMS delivery failed'}), 500

    @app.route('/api/comms/whatsapp', methods=['POST'])
    @require_auth
    def comms_whatsapp():
        """Send a WhatsApp message via Twilio."""
        try:
            data = request.json or {}
            to = data.get('to', '').strip()
            body = data.get('body', '').strip()
            if not to or not body:
                return jsonify({'error': 'to and body are required'}), 400
            result = _comms.send_whatsapp(to=to, body=body)
            _analytics.track_event('whatsapp_sent', {'to': to})
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"WhatsApp error: {e}")
            return jsonify({'error': 'WhatsApp delivery failed'}), 500

    @app.route('/api/comms/call', methods=['POST'])
    @require_auth
    def comms_call():
        """Initiate an outbound voice call via Twilio."""
        try:
            data = request.json or {}
            to = data.get('to', '').strip()
            twiml_url = data.get('twiml_url', '').strip()
            if not to or not twiml_url:
                return jsonify({'error': 'to and twiml_url are required'}), 400
            result = _comms.make_call(to=to, twiml_url=twiml_url)
            _analytics.track_event('call_initiated', {'to': to})
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Call error: {e}")
            return jsonify({'error': 'Call initiation failed'}), 500

    @app.route('/api/comms/email', methods=['POST'])
    @require_auth
    def comms_email():
        """Send a transactional email via SendGrid."""
        try:
            data = request.json or {}
            to = data.get('to', '').strip()
            subject = data.get('subject', '').strip()
            html_body = data.get('html_body', '').strip()
            if not to or not subject or not html_body:
                return jsonify({'error': 'to, subject, and html_body are required'}), 400
            result = _comms.send_email(
                to=to,
                subject=subject,
                html_body=html_body,
                text_body=data.get('text_body'),
                from_email=data.get('from_email'),
                from_name=data.get('from_name'),
            )
            _analytics.track_event('email_sent', {'to': to, 'subject': subject})
            return jsonify(result), 200
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 503
        except Exception as e:
            logger.error(f"Email error: {e}")
            return jsonify({'error': 'Email delivery failed'}), 500

    # ============================================
    # Analytics & Optimization Endpoints
    # ============================================

    @app.route('/api/analytics/events', methods=['POST'])
    @require_auth
    def analytics_track():
        """Track an analytics event."""
        try:
            data = request.json or {}
            event_type = data.get('event_type', '').strip()
            if not event_type:
                return jsonify({'error': 'event_type is required'}), 400
            actor = getattr(g, 'current_user', {})
            actor_id = actor.get('id') if isinstance(actor, dict) else None
            event = _analytics.track_event(
                event_type=event_type,
                data=data.get('data'),
                actor_id=actor_id,
            )
            return jsonify(event), 201
        except Exception as e:
            logger.error(f"Analytics track error: {e}")
            return jsonify({'error': 'Event tracking failed'}), 400

    @app.route('/api/analytics/metrics', methods=['GET'])
    @require_auth
    def analytics_metrics():
        """Return aggregated performance metrics."""
        since = request.args.get('since')
        return jsonify(_analytics.get_metrics(since=since)), 200

    @app.route('/api/analytics/feedback', methods=['POST'])
    @require_auth
    def analytics_feedback_log():
        """Log an AI feedback signal for reinforcement learning."""
        try:
            data = request.json or {}
            agent_id = data.get('agent_id', '').strip()
            task_id = data.get('task_id', '').strip()
            outcome = data.get('outcome', '').strip()
            score = data.get('score')
            if not agent_id or not task_id or not outcome or score is None:
                return jsonify({'error': 'agent_id, task_id, outcome, and score are required'}), 400
            feedback = _analytics.log_feedback(
                agent_id=agent_id,
                task_id=task_id,
                outcome=outcome,
                score=score,
                notes=data.get('notes'),
            )
            return jsonify(feedback), 201
        except Exception as e:
            logger.error(f"Feedback log error: {e}")
            return jsonify({'error': 'Feedback logging failed'}), 400

    @app.route('/api/analytics/feedback', methods=['GET'])
    @require_auth
    def analytics_feedback_summary():
        """Return feedback summary, optionally filtered by agent."""
        agent_id = request.args.get('agent_id')
        return jsonify(_analytics.get_feedback_summary(agent_id=agent_id)), 200

    # ============================================
    # Audit Log Endpoints
    # ============================================

    @app.route('/api/audit', methods=['GET'])
    @require_auth
    def audit_list():
        """Return recent audit log entries (most-recent first, up to 200)."""
        limit = min(int(request.args.get('limit', 200)), 200)
        entries = _store.list_audit_entries(limit=limit)
        return jsonify(list(reversed(entries))), 200

    # ============================================
    # OpenClaw Agent Framework Endpoints
    # ============================================

    from openclaw.framework import AgentConfig, TaskExecutor

    _executor = TaskExecutor(ai_service=_ai)

    @app.route('/api/framework/agents/spawn', methods=['POST'])
    @require_auth
    def framework_spawn():
        """Spawn a new framework agent.

        Body (JSON):
          name (str, required) — agent name
          role (str) — executor | researcher | analyzer | validator
          capabilities (list[str])
          tools (list[str])
          model (str)
          max_steps (int)
          temperature (float)
          system_prompt (str)
          metadata (dict)
        """
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name is required'}), 400
        config = AgentConfig.from_dict({**data, 'name': name})
        agent = _executor.spawn(config)
        return jsonify(agent.to_dict()), 201

    @app.route('/api/framework/agents', methods=['GET'])
    @require_auth
    def framework_list_agents():
        """Return all active framework agent instances."""
        return jsonify(_executor.list_agents()), 200

    @app.route('/api/framework/agents/<agent_id>', methods=['GET'])
    @require_auth
    def framework_get_agent(agent_id):
        """Return a specific framework agent by id."""
        agent = _executor.get_agent(agent_id)
        if agent is None:
            return jsonify({'error': 'Agent not found'}), 404
        return jsonify(agent.to_dict()), 200

    @app.route('/api/framework/run', methods=['POST'])
    @require_auth
    def framework_run():
        """Execute a goal through the OpenClaw agent framework.

        Body (JSON):
          goal (str, required) — natural-language objective
          strategy (str) — 'sequential' (default) or 'parallel'
          agent (dict) — optional AgentConfig fields
          context (dict) — extra context passed to the planner
        """
        data = request.json or {}
        goal = (data.get('goal') or '').strip()
        if not goal:
            return jsonify({'error': 'goal is required'}), 400

        strategy = data.get('strategy', 'sequential')
        agent_data = data.get('agent') or {}
        if agent_data and not agent_data.get('name'):
            agent_data['name'] = 'openclaw-default'
        agent_config = AgentConfig.from_dict(agent_data) if agent_data else None
        context = data.get('context')

        result = _executor.run(
            goal=goal,
            agent_config=agent_config,
            strategy=strategy,
            context=context,
        )
        status_code = 200 if result.status == 'done' else 500
        return jsonify(result.to_dict()), status_code

    @app.route('/api/framework/status', methods=['GET'])
    @require_auth
    def framework_status():
        """Return the OpenClaw framework operational status."""
        agents = _executor.list_agents()
        return jsonify({
            'status': 'operational',
            'active_agents': len(agents),
            'tools': _executor._registry.names(),
        }), 200

    # ============================================
    # Error Handlers
    # ============================================

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    logger.info("Starting open-claw API server...")
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
