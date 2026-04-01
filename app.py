"""Open Claw - Agent Management System.

Production-ready Flask API with JWT authentication, input validation,
structured logging, pagination, and API versioning.
"""

from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import uuid
import logging
import os
import json


# ============================================
# Application Factory
# ============================================

def create_app(config=None):
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
    })

    if config:
        app.config.update(config)

    # Initialize JWT
    jwt = JWTManager(app)

    # Configure structured logging
    _setup_logging(app)

    # In-memory storage (swap with DB adapter in production)
    app.users = {}
    app.agents = {}
    app.tasks = {}

    # Register all routes and error handlers
    _register_routes(app, jwt)

    return app


def _setup_logging(app):
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


def _paginate(items, page, per_page):
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


def _validate_required(data, fields):
    """Return list of missing required field names."""
    return [f for f in fields if f not in data or data[f] is None]


def _parse_pagination(args):
    """Parse and validate page/per_page query parameters."""
    page = int(args.get('page', 1))
    per_page = min(int(args.get('per_page', 20)), 100)
    if page < 1:
        raise ValueError('page must be >= 1')
    if per_page < 1:
        raise ValueError('per_page must be >= 1')
    return page, per_page


def _register_routes(app, jwt):
    """Register all application routes and error handlers."""

    def admin_required(fn):
        """Decorator: require admin role."""
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            user = app.users.get(identity)
            if not user or user.get('role') != 'admin':
                return jsonify({'error': 'Admin access required', 'code': 'FORBIDDEN'}), 403
            return fn(*args, **kwargs)
        return wrapper

    # ============================================
    # Authentication Endpoints
    # ============================================

    @app.route('/api/v1/auth/register', methods=['POST'])
    def register():
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

            for user in app.users.values():
                if user['username'] == username:
                    return jsonify({'error': 'Username already exists', 'code': 'CONFLICT'}), 409

            user_id = str(uuid.uuid4())
            user = {
                'id': user_id,
                'username': username,
                'password_hash': generate_password_hash(password),
                'role': data.get('role', 'user'),
                'created_at': datetime.utcnow().isoformat() + 'Z',
            }
            app.users[user_id] = user
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
    def login():
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

            user = None
            for u in app.users.values():
                if u['username'] == username:
                    user = u
                    break

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
    def refresh_token():
        """Refresh access token using a refresh token."""
        identity = get_jwt_identity()
        user = app.users.get(identity)
        if not user:
            return jsonify({'error': 'User not found', 'code': 'NOT_FOUND'}), 404
        access_token = create_access_token(
            identity=identity,
            additional_claims={'role': user['role'], 'username': user['username']},
        )
        return jsonify({'access_token': access_token}), 200

    # ============================================
    # Agent Management Endpoints
    # ============================================

    @app.route('/api/v1/agents', methods=['POST'])
    @jwt_required()
    def create_agent():
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
            }
            app.agents[agent_id] = agent
            app.logger.info(json.dumps({'event': 'agent_created', 'agent_id': agent_id}))
            return jsonify(agent), 201
        except Exception as e:
            app.logger.error(f'Error creating agent: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/agents', methods=['GET'])
    @jwt_required()
    def list_agents():
        """List all agents with pagination, filtering, and sorting."""
        try:
            page, per_page = _parse_pagination(request.args)
        except ValueError as e:
            return jsonify({'error': 'Invalid pagination parameters', 'code': 'INVALID_INPUT'}), 400

        status_filter = request.args.get('status')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        agent_list = list(app.agents.values())
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
    def get_agent(agent_id):
        """Get details of a specific agent."""
        agent = app.agents.get(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404
        return jsonify(agent), 200

    @app.route('/api/v1/agents/<agent_id>', methods=['PUT'])
    @jwt_required()
    def update_agent(agent_id):
        """Update agent status or properties."""
        try:
            if agent_id not in app.agents:
                return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404

            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            agent = app.agents[agent_id]
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

            app.logger.info(json.dumps({'event': 'agent_updated', 'agent_id': agent_id}))
            return jsonify(agent), 200
        except Exception as e:
            app.logger.error(f'Error updating agent: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/agents/<agent_id>', methods=['DELETE'])
    @jwt_required()
    def delete_agent(agent_id):
        """Delete an agent."""
        if agent_id not in app.agents:
            return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404
        del app.agents[agent_id]
        app.logger.info(json.dumps({'event': 'agent_deleted', 'agent_id': agent_id}))
        return jsonify({'message': 'Agent deleted successfully'}), 200

    # ============================================
    # Task Management Endpoints
    # ============================================

    @app.route('/api/v1/tasks', methods=['POST'])
    @jwt_required()
    def submit_task():
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
            if agent_id and agent_id not in app.agents:
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
            app.tasks[task_id] = task
            app.logger.info(json.dumps({'event': 'task_created', 'task_id': task_id}))
            return jsonify(task), 201
        except Exception as e:
            app.logger.error(f'Error creating task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/tasks', methods=['GET'])
    @jwt_required()
    def list_tasks():
        """List all tasks with pagination, filtering, and sorting."""
        try:
            page, per_page = _parse_pagination(request.args)
        except ValueError as e:
            return jsonify({'error': 'Invalid pagination parameters', 'code': 'INVALID_INPUT'}), 400

        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent_id')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')

        task_list = list(app.tasks.values())
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
    def get_task(task_id):
        """Get details of a specific task."""
        task = app.tasks.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
        return jsonify(task), 200

    @app.route('/api/v1/tasks/<task_id>', methods=['PUT'])
    @jwt_required()
    def update_task(task_id):
        """Update task status or result."""
        try:
            if task_id not in app.tasks:
                return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404

            data = request.get_json(silent=True)
            if not data:
                return jsonify({'error': 'Request body required', 'code': 'INVALID_INPUT'}), 400

            task = app.tasks[task_id]
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

            app.logger.info(json.dumps({'event': 'task_updated', 'task_id': task_id}))
            return jsonify(task), 200
        except Exception as e:
            app.logger.error(f'Error updating task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/tasks/<task_id>', methods=['DELETE'])
    @jwt_required()
    def delete_task(task_id):
        """Delete a task."""
        if task_id not in app.tasks:
            return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
        del app.tasks[task_id]
        app.logger.info(json.dumps({'event': 'task_deleted', 'task_id': task_id}))
        return jsonify({'message': 'Task deleted successfully'}), 200

    # ============================================
    # Health & Status Endpoints (no auth required)
    # ============================================

    @app.route('/api/v1/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
        }), 200

    @app.route('/api/v1/status', methods=['GET'])
    @app.route('/api/status', methods=['GET'])
    def status():
        """Get system status."""
        running_tasks = sum(1 for t in app.tasks.values() if t['status'] == 'running')
        completed_tasks = sum(1 for t in app.tasks.values() if t['status'] == 'completed')
        idle_agents = sum(1 for a in app.agents.values() if a['status'] == 'idle')
        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'agents': {
                'total': len(app.agents),
                'idle': idle_agents,
                'active': len(app.agents) - idle_agents,
            },
            'tasks': {
                'total': len(app.tasks),
                'running': running_tasks,
                'completed': completed_tasks,
                'pending': len(app.tasks) - running_tasks - completed_tasks,
            },
        }), 200

    # ============================================
    # Workforce Management Endpoints
    # ============================================

    @app.route('/api/v1/workforce/assign', methods=['POST'])
    @jwt_required()
    def assign_task_to_agent():
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

            if task_id not in app.tasks:
                return jsonify({'error': 'Task not found', 'code': 'NOT_FOUND'}), 404
            if agent_id not in app.agents:
                return jsonify({'error': 'Agent not found', 'code': 'NOT_FOUND'}), 404

            task = app.tasks[task_id]
            agent = app.agents[agent_id]
            task['agent_id'] = agent_id
            task['status'] = 'assigned'
            agent['status'] = 'busy'

            app.logger.info(json.dumps({
                'event': 'task_assigned', 'task_id': task_id, 'agent_id': agent_id,
            }))
            return jsonify({'task': task, 'agent': agent}), 200
        except Exception as e:
            app.logger.error(f'Error assigning task: {str(e)}')
            return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @app.route('/api/v1/workforce/summary', methods=['GET'])
    @jwt_required()
    def workforce_summary():
        """Get workforce summary and statistics."""
        agent_capabilities = {}
        for agent in app.agents.values():
            for cap in agent.get('capabilities', []):
                agent_capabilities[cap] = agent_capabilities.get(cap, 0) + 1

        return jsonify({
            'agents_count': len(app.agents),
            'tasks_count': len(app.tasks),
            'capabilities': agent_capabilities,
            'agents': list(app.agents.values()),
            'tasks': list(app.tasks.values()),
        }), 200

    # ============================================
    # Error Handlers
    # ============================================

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {str(error)}')
        return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        return jsonify({'error': 'Authorization required', 'code': 'UNAUTHORIZED', 'reason': reason}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({'error': 'Invalid token', 'code': 'INVALID_TOKEN', 'reason': reason}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({'error': 'Token has expired', 'code': 'TOKEN_EXPIRED'}), 401


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    application = create_app()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    application.logger.info(json.dumps({'event': 'server_start', 'host': host, 'port': port}))
    application.run(host=host, port=port)
