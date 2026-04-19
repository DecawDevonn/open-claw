"""Open Claw - Agent Management System.

Production-ready Flask API with JWT authentication, input validation,
structured logging, pagination, rate limiting, CORS, and API versioning.
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

from apscheduler.schedulers.background import BackgroundScheduler

from storage import get_storage


# Module-level limiter — decorators reference this before init_app is called.
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "100 per minute"])


# ============================================
# Application Factory
# ============================================

def create_app(config: Optional[Dict] = None) -> Flask:
    """Application factory function."""
    app = Flask(__name__)

    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        'JWT_SECRET_KEY': os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production'),
        'JWT_ACCESS_TOKEN_EXPIRES': timedelta(hours=1),
        'JWT_REFRESH_TOKEN_EXPIRES': timedelta(days=30),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'INFO'),
        'DEBUG': os.environ.get('FLASK_DEBUG', 'false').lower() == 'true',
        'TESTING': False,
        'MONGODB_URI': os.environ.get('MONGODB_URI', ''),
        'REDIS_URL': os.environ.get('REDIS_URL', 'memory://'),
        'CORS_ORIGINS': os.environ.get('CORS_ORIGINS', '*'),
        'AGENT_HEARTBEAT_TIMEOUT': int(os.environ.get('AGENT_HEARTBEAT_TIMEOUT', 60)),
        'RATELIMIT_ENABLED': True,
    })

    if config:
        app.config.update(config)

    # Disable rate limiting in test mode
    if app.config.get('TESTING'):
        app.config['RATELIMIT_ENABLED'] = False

    # CORS
    CORS(app, origins=app.config['CORS_ORIGINS'].split(','))

    # Rate limiter
    limiter.init_app(app)

    # Initialize JWT
    jwt = JWTManager(app)

    # Configure structured logging
    _setup_logging(app)

    # Storage backend (in-memory for dev/test, MongoDB for production)
    app.storage = get_storage(app.config.get('MONGODB_URI') or None)

    # Register all routes and error handlers
    _register_routes(app, jwt, limiter)

    # Heartbeat scheduler (skip in tests to avoid background threads)
    if not app.config.get('TESTING'):
        _start_heartbeat_scheduler(app)

    return app


def _start_heartbeat_scheduler(app: Flask) -> BackgroundScheduler:
    """Start a background scheduler that marks stale agents as offline."""
    timeout = int(app.config.get('AGENT_HEARTBEAT_TIMEOUT', 60))
    scheduler = BackgroundScheduler(daemon=True)

    def _check_heartbeats() -> None:
        cutoff = datetime.utcnow() - timedelta(seconds=timeout)
        for agent in app.storage.list_agents():
            last_seen = agent.get('last_seen_at')
            if last_seen:
                last_seen_dt = datetime.fromisoformat(last_seen.rstrip('Z'))
                if last_seen_dt < cutoff and agent['status'] != 'offline':
                    agent['status'] = 'offline'
                    app.storage.save_agent(agent)

    scheduler.add_job(_check_heartbeats, 'interval', seconds=30)
    scheduler.start()
    return scheduler


def _setup_logging(app: Flask) -> None:
    """Configure structured JSON logging."""
    log_level = app.config.get('LOG_LEVEL', 'INFO')

    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': record.levelname,
                'message': record.getMessage(),
                'module': record.module,
            }
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            return json.dumps(log_data)

    if not app.config.get('TESTING'):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        app.logger.handlers = [handler]
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))


def _paginate(items: List, page: int, per_page: int) -> Dict:
    """Return a paginated slice of a list with metadata."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
    }


def _validate_required(data: Dict, fields: List[str]) -> List[str]:
    """Return list of missing required field names."""
    return [f for f in fields if f not in data or data[f] is None]


def _parse_pagination(args: Any) -> Tuple[int, int]:
    """Parse and validate page/per_page query parameters."""
    page = int(args.get('page', 1))
    per_page = min(int(args.get('per_page', 20)), 100)
    if page < 1:
        raise ValueError('page must be >= 1')
    if per_page < 1:
        raise ValueError('per_page must be >= 1')
    return page, per_page


def _register_routes(app: Flask, jwt: JWTManager, limiter: Limiter) -> None:
    """Register all application routes and error handlers."""

    # --- JWT blocklist ---

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header: Dict, jwt_payload: Dict) -> bool:
        return app.storage.is_token_revoked(jwt_payload['jti'])

    # --- Request/response logging middleware ---

    @app.before_request
    def _before_request() -> None:
        g.start_time = time.monotonic()

    @app.after_request
    def _after_request(response: Any) -> Any:
        latency_ms = round((time.monotonic() - g.start_time) * 1000, 2)
        if not app.config.get('TESTING'):
            app.logger.info(json.dumps({
                'event': 'request',
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'latency_ms': latency_ms,
            }))
        return response

    def admin_required(fn: Any) -> Any:
        """Decorator: require admin role."""
        @wraps(fn)
        @jwt_required()
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            identity = get_jwt_identity()
            user = app.storage.get_user(identity)
            if not user or user.get('role') != 'admin':
                return jsonify({'error': 'Admin access required', 'code': 'FORBIDDEN'}), 403
            return fn(*args, **kwargs)
        return wrapper

    # ============================================
    # Authentication Endpoints
    # ============================================

    @app.route('/api/v1/auth/register', methods=['POST'])
    @limiter.limit('10 per minute')
    def register() -> Tuple[Any, int]:
        """Register a new user."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            missing = _validate_required(data, ['username', 'password'])
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}',
                    'code': 'MISSING_FIELDS',
                }), 400

            username = str(data['username']).strip()
            password = str(data['password'])

            if len(username) < 3:
                return jsonify({
                    'error': 'Username must be at least 3 characters',
                    'code': 'INVALID_INPUT',
                }), 400
            if len(password) < 6:
                return jsonify({
                    'error': 'Password must be at least 6 characters',
                    'code': 'INVALID_INPUT',
                }), 400

            if app.storage.get_user_by_username(username):
                return jsonify({'error': 'Username already exists', 'code': 'CONFLICT'}), 409

            user_id = str(uuid.uuid4())
            user = {
                'id': user_id,
                'username': username,
                'password_hash': generate_password_hash(password),
                'role': data.get('role', 'user'),
                'created_at': datetime.utcnow().isoformat() + 'Z',
            }
            app.storage.save_user(user)
            app.logger.info(json.dumps({'event': 'user_registered', 'user_id': user_id}))
            return jsonify({
                'message': 'User registered successfully',
                'user_id': user_id,
                'username': username,
            }), 201
        except Exception as e:
            app.logger.error(f'Error registering user: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/auth/login', methods=['POST'])
    @limiter.limit('10 per minute')
    def login() -> Tuple[Any, int]:
        """Authenticate user and return JWT tokens."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            missing = _validate_required(data, ['username', 'password'])
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}',
                    'code': 'MISSING_FIELDS',
                }), 400

            username = data['username']
            password = data['password']

            user = app.storage.get_user_by_username(username)

            if not user or not check_password_hash(user['password_hash'], password):
                return jsonify({'error': 'Invalid credentials', 'code': 'UNAUTHORIZED'}), 401

            access_token = create_access_token(
                identity=user['id'],
                additional_claims={'role': user['role'], 'username': user['username']},
            )
            refresh_token = create_refresh_token(identity=user['id'])

            app.logger.info(json.dumps({'event': 'user_login', 'user_id': user['id']}))
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': user['id'],
                'username': user['username'],
                'role': user['role'],
            }), 200
        except Exception as e:
            app.logger.error(f'Error during login: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/auth/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh_token() -> Tuple[Any, int]:
        """Refresh access token using a refresh token."""
        identity = get_jwt_identity()
        user = app.storage.get_user(identity)
        if not user:
            return jsonify({'error': 'User not found', 'code': 'NOT_FOUND'}), 404
        access_token = create_access_token(
            identity=identity,
            additional_claims={'role': user['role'], 'username': user['username']},
        )
        return jsonify({'access_token': access_token}), 200

    @app.route('/api/v1/auth/logout', methods=['POST'])
    @jwt_required()
    @limiter.limit('30 per minute')
    def logout() -> Tuple[Any, int]:
        """Revoke the current access token."""
        jti = get_jwt()['jti']
        app.storage.revoke_token(jti)
        return jsonify({'message': 'Successfully logged out'}), 200

    # ============================================
    # Agent Management Endpoints
    # ============================================

    @app.route('/api/v1/agents', methods=['POST'])
    @jwt_required()
    def create_agent() -> Tuple[Any, int]:
        """Create a new agent."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            missing = _validate_required(data, ['name'])
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}',
                    'code': 'MISSING_FIELDS',
                }), 400

            capabilities = data.get('capabilities', [])
            if not isinstance(capabilities, list):
                return jsonify({'error': 'capabilities must be a list', 'code': 'INVALID_INPUT'}), 400

            agent_id = str(uuid.uuid4())
            agent = {
                'id': agent_id,
                'name': str(data['name']).strip(),
                'type': str(data.get('type', 'generic')).strip(),
                'status': 'idle',
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'capabilities': capabilities,
                'tasks_completed': 0,
                'last_seen_at': None,
            }
            app.storage.save_agent(agent)
            app.logger.info(json.dumps({'event': 'agent_created', 'agent_id': agent_id}))
            return jsonify(agent), 201
        except Exception as e:
            app.logger.error(f'Error creating agent: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/agents', methods=['GET'])
    @jwt_required()
    def list_agents() -> Tuple[Any, int]:
        """List all agents with pagination, filtering, and sorting."""
        try:
            page, per_page = _parse_pagination(request.args)
        except ValueError:
            return jsonify({'error': 'Invalid pagination parameters', 'code': 'INVALID_INPUT'}), 400

        status_filter = request.args.get('status')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        agent_list = app.storage.list_agents()
        if status_filter:
            agent_list = [a for a in agent_list if a['status'] == status_filter]

        if sort_by in ('created_at', 'name', 'status', 'tasks_completed'):
            agent_list.sort(
                key=lambda x: x.get(sort_by, ''),
                reverse=(sort_order.lower() == 'desc'),
            )

        return jsonify(_paginate(agent_list, page, per_page)), 200

    @app.route('/api/v1/agents/<agent_id>', methods=['GET'])
    @jwt_required()
    def get_agent(agent_id: str) -> Tuple[Any, int]:
        """Get details of a specific agent."""
        agent = app.storage.get_agent(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404
        return jsonify(agent), 200

    @app.route('/api/v1/agents/<agent_id>', methods=['PUT'])
    @jwt_required()
    def update_agent(agent_id: str) -> Tuple[Any, int]:
        """Update agent status or properties."""
        try:
            agent = app.storage.get_agent(agent_id)
            if not agent:
                return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404

            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            valid_statuses = ('idle', 'busy', 'offline', 'error')

            if 'status' in data:
                if data['status'] not in valid_statuses:
                    return jsonify({
                        'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
                        'code': 'INVALID_INPUT',
                    }), 400
                agent['status'] = data['status']

            if 'capabilities' in data:
                if not isinstance(data['capabilities'], list):
                    return jsonify({'error': 'capabilities must be a list', 'code': 'INVALID_INPUT'}), 400
                agent['capabilities'] = data['capabilities']

            if 'name' in data:
                agent['name'] = str(data['name']).strip()

            app.storage.save_agent(agent)
            app.logger.info(json.dumps({'event': 'agent_updated', 'agent_id': agent_id}))
            return jsonify(agent), 200
        except Exception as e:
            app.logger.error(f'Error updating agent: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/agents/<agent_id>', methods=['DELETE'])
    @jwt_required()
    def delete_agent(agent_id: str) -> Tuple[Any, int]:
        """Delete an agent."""
        if not app.storage.delete_agent(agent_id):
            return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404
        app.logger.info(json.dumps({'event': 'agent_deleted', 'agent_id': agent_id}))
        return jsonify({'message': 'Agent deleted successfully'}), 200

    @app.route('/api/v1/agents/<agent_id>/heartbeat', methods=['POST'])
    @jwt_required()
    def agent_heartbeat(agent_id: str) -> Tuple[Any, int]:
        """Update agent last_seen_at and revive if offline."""
        agent = app.storage.get_agent(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404
        agent['last_seen_at'] = datetime.utcnow().isoformat() + 'Z'
        if agent['status'] == 'offline':
            agent['status'] = 'idle'
        app.storage.save_agent(agent)
        return jsonify(agent), 200

    # ============================================
    # Task Management Endpoints
    # ============================================

    @app.route('/api/v1/tasks', methods=['POST'])
    @jwt_required()
    def submit_task() -> Tuple[Any, int]:
        """Submit a new task."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            missing = _validate_required(data, ['name'])
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}',
                    'code': 'MISSING_FIELDS',
                }), 400

            valid_priorities = ('low', 'normal', 'high', 'critical')
            priority = data.get('priority', 'normal')
            if priority not in valid_priorities:
                return jsonify({
                    'error': f'Invalid priority. Must be one of: {", ".join(valid_priorities)}',
                    'code': 'INVALID_INPUT',
                }), 400

            agent_id = data.get('agent_id')
            if agent_id and not app.storage.get_agent(agent_id):
                return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404

            task_id = str(uuid.uuid4())
            task = {
                'id': task_id,
                'name': str(data['name']).strip(),
                'description': str(data.get('description', '')),
                'agent_id': agent_id,
                'status': 'pending',
                'priority': priority,
                'created_at': datetime.utcnow().isoformat() + 'Z',
                'started_at': None,
                'completed_at': None,
                'result': None,
            }
            app.storage.save_task(task)
            app.logger.info(json.dumps({'event': 'task_created', 'task_id': task_id}))
            return jsonify(task), 201
        except Exception as e:
            app.logger.error(f'Error creating task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/tasks', methods=['GET'])
    @jwt_required()
    def list_tasks() -> Tuple[Any, int]:
        """List all tasks with pagination, filtering, and sorting."""
        try:
            page, per_page = _parse_pagination(request.args)
        except ValueError:
            return jsonify({'error': 'Invalid pagination parameters', 'code': 'INVALID_INPUT'}), 400

        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent_id')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        task_list = app.storage.list_tasks()
        if status_filter:
            task_list = [t for t in task_list if t['status'] == status_filter]
        if agent_filter:
            task_list = [t for t in task_list if t['agent_id'] == agent_filter]

        if sort_by in ('created_at', 'name', 'status', 'priority'):
            task_list.sort(
                key=lambda x: x.get(sort_by, ''),
                reverse=(sort_order.lower() == 'desc'),
            )

        return jsonify(_paginate(task_list, page, per_page)), 200

    @app.route('/api/v1/tasks/<task_id>', methods=['GET'])
    @jwt_required()
    def get_task(task_id: str) -> Tuple[Any, int]:
        """Get details of a specific task."""
        task = app.storage.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
        return jsonify(task), 200

    @app.route('/api/v1/tasks/<task_id>', methods=['PUT'])
    @jwt_required()
    def update_task(task_id: str) -> Tuple[Any, int]:
        """Update task status or result."""
        try:
            task = app.storage.get_task(task_id)
            if not task:
                return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404

            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            valid_statuses = ('pending', 'assigned', 'running', 'completed', 'failed', 'cancelled')

            if 'status' in data:
                if data['status'] not in valid_statuses:
                    return jsonify({
                        'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
                        'code': 'INVALID_INPUT',
                    }), 400
                task['status'] = data['status']
                if data['status'] == 'running' and not task['started_at']:
                    task['started_at'] = datetime.utcnow().isoformat() + 'Z'
                elif data['status'] in ('completed', 'failed', 'cancelled'):
                    task['completed_at'] = datetime.utcnow().isoformat() + 'Z'

            if 'result' in data:
                task['result'] = data['result']

            app.storage.save_task(task)
            app.logger.info(json.dumps({'event': 'task_updated', 'task_id': task_id}))
            return jsonify(task), 200
        except Exception as e:
            app.logger.error(f'Error updating task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/tasks/<task_id>', methods=['DELETE'])
    @jwt_required()
    def delete_task(task_id: str) -> Tuple[Any, int]:
        """Delete a task."""
        if not app.storage.delete_task(task_id):
            return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
        app.logger.info(json.dumps({'event': 'task_deleted', 'task_id': task_id}))
        return jsonify({'message': 'Task deleted successfully'}), 200

    # ============================================
    # Health & Status Endpoints (no auth required)
    # ============================================

    @app.route('/api/v1/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    def health() -> Tuple[Any, int]:
        """Health check endpoint with dependency checks."""
        checks: Dict[str, str] = {'flask': 'ok'}

        # Check MongoDB / DocumentDB
        mongodb_uri = app.config.get('MONGODB_URI', '')
        if mongodb_uri:
            try:
                import pymongo
                client = pymongo.MongoClient(
                    mongodb_uri,
                    serverSelectionTimeoutMS=2000,
                    tlsCAFile='/global-bundle.pem' if 'docdb' in mongodb_uri else None,
                )
                client.admin.command('ping')
                checks['mongodb'] = 'ok'
                client.close()
            except Exception as exc:
                checks['mongodb'] = f'error: {str(exc)[:80]}'
        else:
            checks['mongodb'] = 'not_configured'

        # Check Redis
        redis_url = app.config.get('REDIS_URL', 'memory://')
        if redis_url and not redis_url.startswith('memory://'):
            try:
                import redis as redis_lib
                r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
                r.ping()
                checks['redis'] = 'ok'
            except Exception as exc:
                checks['redis'] = f'error: {str(exc)[:80]}'
        else:
            checks['redis'] = 'in_memory'

        overall = 'healthy' if all(
            v in ('ok', 'not_configured', 'in_memory') for v in checks.values()
        ) else 'degraded'

        return jsonify({
            'status': overall,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'checks': checks,
        }), 200 if overall == 'healthy' else 207

    @app.route('/api/v1/status', methods=['GET'])
    @app.route('/api/status', methods=['GET'])
    def status() -> Tuple[Any, int]:
        """Get system status."""
        all_tasks = app.storage.list_tasks()
        all_agents = app.storage.list_agents()
        running_tasks = sum(1 for t in all_tasks if t['status'] == 'running')
        completed_tasks = sum(1 for t in all_tasks if t['status'] == 'completed')
        idle_agents = sum(1 for a in all_agents if a['status'] == 'idle')
        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'agents': {
                'total': len(all_agents),
                'idle': idle_agents,
                'active': len(all_agents) - idle_agents,
            },
            'tasks': {
                'total': len(all_tasks),
                'running': running_tasks,
                'completed': completed_tasks,
                'pending': len(all_tasks) - running_tasks - completed_tasks,
            },
        }), 200

    # ============================================
    # MCP (Model Context Protocol) Endpoint
    # ============================================

    @app.route('/api/mcp', methods=['POST', 'OPTIONS'])
    @app.route('/api/v1/mcp', methods=['POST', 'OPTIONS'])
    def mcp_gateway() -> Tuple[Any, int]:
        """JSON-RPC 2.0 endpoint for Model Context Protocol (MCP) tool access.

        Supports methods: initialize, notifications/initialized, tools/list, tools/call
        """
        if request.method == 'OPTIONS':
            from flask import make_response
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, apikey'
            return resp

        try:
            body = request.get_json(silent=True) or {}
            rpc_id = body.get('id')
            method = body.get('method', '')
            params = body.get('params', {})

            app.logger.info(json.dumps({'event': 'mcp_request', 'method': method}))

            # Handle initialize handshake
            if method == 'initialize':
                return jsonify({
                    'jsonrpc': '2.0',
                    'id': rpc_id,
                    'result': {
                        'protocolVersion': '2024-11-05',
                        'capabilities': {
                            'tools': {'listChanged': False},
                        },
                        'serverInfo': {
                            'name': 'devonn-mcp-server',
                            'version': '1.0.0',
                        },
                    },
                }), 200

            # Handle initialized notification (no response needed)
            if method == 'notifications/initialized':
                return jsonify({
                    'jsonrpc': '2.0',
                    'id': rpc_id,
                    'result': {},
                }), 200

            # List available tools
            if method == 'tools/list':
                tools = [
                    {
                        'name': 'health_check',
                        'description': 'Check the health status of the Devonn.AI backend services',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {},
                            'required': [],
                        },
                    },
                    {
                        'name': 'list_agents',
                        'description': 'List all registered AI agents in the system',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'page': {'type': 'integer', 'description': 'Page number (default: 1)'},
                                'per_page': {'type': 'integer', 'description': 'Items per page (default: 20)'},
                            },
                            'required': [],
                        },
                    },
                    {
                        'name': 'list_tasks',
                        'description': 'List all tasks in the system',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'page': {'type': 'integer', 'description': 'Page number (default: 1)'},
                                'per_page': {'type': 'integer', 'description': 'Items per page (default: 20)'},
                            },
                            'required': [],
                        },
                    },
                    {
                        'name': 'get_status',
                        'description': 'Get the current system status including agent and task counts',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {},
                            'required': [],
                        },
                    },
                ]
                return jsonify({
                    'jsonrpc': '2.0',
                    'id': rpc_id,
                    'result': {'tools': tools},
                }), 200

            # Call a tool
            if method == 'tools/call':
                tool_name = params.get('name', '')
                tool_args = params.get('arguments', {})

                if tool_name == 'health_check':
                    checks: Dict[str, str] = {'flask': 'ok'}
                    mongodb_uri = app.config.get('MONGODB_URI', '')
                    if mongodb_uri:
                        try:
                            import pymongo
                            client = pymongo.MongoClient(
                                mongodb_uri,
                                serverSelectionTimeoutMS=2000,
                                tlsCAFile='/global-bundle.pem' if 'docdb' in mongodb_uri else None,
                            )
                            client.admin.command('ping')
                            checks['mongodb'] = 'ok'
                            client.close()
                        except Exception as exc:
                            checks['mongodb'] = f'error: {str(exc)[:80]}'
                    redis_url = app.config.get('REDIS_URL', 'memory://')
                    if redis_url and not redis_url.startswith('memory://'):
                        try:
                            import redis as redis_lib
                            r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
                            r.ping()
                            checks['redis'] = 'ok'
                        except Exception as exc:
                            checks['redis'] = f'error: {str(exc)[:80]}'
                    result_text = json.dumps({'status': 'healthy', 'checks': checks})

                elif tool_name == 'list_agents':
                    agents = app.storage.list_agents()
                    result_text = json.dumps({'agents': agents, 'count': len(agents)})

                elif tool_name == 'list_tasks':
                    tasks = app.storage.list_tasks()
                    result_text = json.dumps({'tasks': tasks, 'count': len(tasks)})

                elif tool_name == 'get_status':
                    all_tasks = app.storage.list_tasks()
                    all_agents = app.storage.list_agents()
                    result_text = json.dumps({
                        'agents': len(all_agents),
                        'tasks': len(all_tasks),
                        'running': sum(1 for t in all_tasks if t['status'] == 'running'),
                    })

                else:
                    return jsonify({
                        'jsonrpc': '2.0',
                        'id': rpc_id,
                        'error': {'code': -32601, 'message': f'Unknown tool: {tool_name}'},
                    }), 200

                return jsonify({
                    'jsonrpc': '2.0',
                    'id': rpc_id,
                    'result': {
                        'content': [{'type': 'text', 'text': result_text}],
                        'isError': False,
                    },
                }), 200

            # Unknown method
            return jsonify({
                'jsonrpc': '2.0',
                'id': rpc_id,
                'error': {'code': -32601, 'message': f'Method not found: {method}'},
            }), 200

        except Exception as e:
            app.logger.error(f'MCP error: {str(e)}')
            return jsonify({
                'jsonrpc': '2.0',
                'id': None,
                'error': {'code': -32603, 'message': 'Internal error'},
            }), 200

    # ============================================
    # Workforce Management Endpoints
    # ============================================

    @app.route('/api/v1/workforce/assign', methods=['POST'])
    @jwt_required()
    def assign_task_to_agent() -> Tuple[Any, int]:
        """Assign a task to an agent."""
        try:
            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            missing = _validate_required(data, ['task_id', 'agent_id'])
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}',
                    'code': 'MISSING_FIELDS',
                }), 400

            task_id = data['task_id']
            agent_id = data['agent_id']

            task = app.storage.get_task(task_id)
            if not task:
                return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
            agent = app.storage.get_agent(agent_id)
            if not agent:
                return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404

            task['agent_id'] = agent_id
            task['status'] = 'assigned'
            agent['status'] = 'busy'
            app.storage.save_task(task)
            app.storage.save_agent(agent)

            app.logger.info(json.dumps({
                'event': 'task_assigned', 'task_id': task_id, 'agent_id': agent_id,
            }))
            return jsonify({'task': task, 'agent': agent}), 200
        except Exception as e:
            app.logger.error(f'Error assigning task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/workforce/summary', methods=['GET'])
    @jwt_required()
    def workforce_summary() -> Tuple[Any, int]:
        """Get workforce summary and statistics."""
        all_agents = app.storage.list_agents()
        all_tasks = app.storage.list_tasks()
        agent_capabilities: Dict[str, int] = {}
        for agent in all_agents:
            for cap in agent.get('capabilities', []):
                agent_capabilities[cap] = agent_capabilities.get(cap, 0) + 1

        return jsonify({
            'agents_count': len(all_agents),
            'tasks_count': len(all_tasks),
            'capabilities': agent_capabilities,
            'agents': all_agents,
            'tasks': all_tasks,
        }), 200

    # ============================================
    # Error Handlers
    # ============================================

    @app.errorhandler(404)
    def not_found(error: Any) -> Tuple[Any, int]:
        return jsonify({'error': 'Resource not found', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error: Any) -> Tuple[Any, int]:
        return jsonify({'error': 'Method not allowed', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(500)
    def internal_error(error: Any) -> Tuple[Any, int]:
        app.logger.error(f'Internal server error: {str(error)}')
        return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @jwt.unauthorized_loader
    def unauthorized_callback(reason: str) -> Tuple[Any, int]:
        return jsonify({'error': 'Authorization required', 'code': 'UNAUTHORIZED', 'reason': reason}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason: str) -> Tuple[Any, int]:
        return jsonify({'error': 'Invalid token', 'code': 'INVALID_TOKEN', 'reason': reason}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header: Dict, jwt_data: Dict) -> Tuple[Any, int]:
        return jsonify({'error': 'Token has expired', 'code': 'TOKEN_EXPIRED'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header: Dict, jwt_data: Dict) -> Tuple[Any, int]:
        return jsonify({'error': 'Token has been revoked', 'code': 'TOKEN_REVOKED'}), 401


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    application = create_app()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    application.logger.info(json.dumps({'event': 'server_start', 'host': host, 'port': port}))
    application.run(host=host, port=port)
else:
    # WSGI entrypoint for gunicorn / production
    application = create_app()
