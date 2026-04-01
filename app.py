from flask import Flask, jsonify, request, current_app
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(__name__)

    # Load config
    from src.config import Config, TestingConfig
    if config == 'testing':
        app.config.from_object(TestingConfig)
    else:
        app.config.from_object(Config)

    # In-memory storage
    app.agents = {}
    app.tasks = {}

    # Initialize Fortress engine
    from src.fortress.engine import FortressV2Production
    fortress_config = app.config.get('FORTRESS')
    try:
        engine = FortressV2Production(
            data_dir=getattr(fortress_config, 'data_dir', '/tmp/fortress'),
            max_workers=getattr(fortress_config, 'max_workers', 4),
            sandbox_timeout=getattr(fortress_config, 'sandbox_timeout', 30),
        )
        app.extensions['fortress_engine'] = engine
        logger.info("Fortress v2 engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Fortress engine: {e}")

    # Register Fortress blueprint
    from src.routes.fortress import fortress_bp
    app.register_blueprint(fortress_bp)

    # Setup request logging
    from src.monitoring.logging_config import setup_request_logging
    setup_request_logging(app)

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
                'created_at': datetime.utcnow().isoformat(),
                'capabilities': data.get('capabilities', []),
                'tasks_completed': 0
            }

            current_app.agents[agent_id] = agent
            logger.info(f"Created agent: {agent_id}")
            return jsonify(agent), 201
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            return jsonify({'error': 'Failed to create agent'}), 400

    @app.route('/api/agents', methods=['GET'])
    def list_agents():
        """List all agents"""
        return jsonify(list(current_app.agents.values())), 200

    @app.route('/api/agents/<agent_id>', methods=['GET'])
    def get_agent(agent_id):
        """Get details of a specific agent"""
        agent = current_app.agents.get(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        return jsonify(agent), 200

    @app.route('/api/agents/<agent_id>', methods=['PUT'])
    def update_agent(agent_id):
        """Update agent status or properties"""
        try:
            if agent_id not in current_app.agents:
                return jsonify({'error': 'Agent not found'}), 404

            data = request.json
            agent = current_app.agents[agent_id]

            if 'status' in data:
                agent['status'] = data['status']
            if 'capabilities' in data:
                agent['capabilities'] = data['capabilities']

            logger.info(f"Updated agent: {agent_id}")
            return jsonify(agent), 200
        except Exception as e:
            logger.error(f"Error updating agent: {str(e)}")
            return jsonify({'error': 'Failed to update agent'}), 400

    @app.route('/api/agents/<agent_id>', methods=['DELETE'])
    def delete_agent(agent_id):
        """Delete an agent"""
        if agent_id not in current_app.agents:
            return jsonify({'error': 'Agent not found'}), 404

        del current_app.agents[agent_id]
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
                'created_at': datetime.utcnow().isoformat(),
                'started_at': None,
                'completed_at': None,
                'result': None
            }

            current_app.tasks[task_id] = task
            logger.info(f"Created task: {task_id}")
            return jsonify(task), 201
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            return jsonify({'error': 'Failed to create task'}), 400

    @app.route('/api/tasks', methods=['GET'])
    def list_tasks():
        """List all tasks with optional filtering"""
        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent_id')

        filtered_tasks = list(current_app.tasks.values())

        if status_filter:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == status_filter]
        if agent_filter:
            filtered_tasks = [t for t in filtered_tasks if t['agent_id'] == agent_filter]

        return jsonify(filtered_tasks), 200

    @app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """Get details of a specific task"""
        task = current_app.tasks.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task), 200

    @app.route('/api/tasks/<task_id>', methods=['PUT'])
    def update_task(task_id):
        """Update task status or result"""
        try:
            if task_id not in current_app.tasks:
                return jsonify({'error': 'Task not found'}), 404

            data = request.json
            task = current_app.tasks[task_id]

            if 'status' in data:
                task['status'] = data['status']
                if data['status'] == 'running':
                    task['started_at'] = datetime.utcnow().isoformat()
                elif data['status'] == 'completed':
                    task['completed_at'] = datetime.utcnow().isoformat()

            if 'result' in data:
                task['result'] = data['result']

            logger.info(f"Updated task: {task_id}")
            return jsonify(task), 200
        except Exception as e:
            logger.error(f"Error updating task: {str(e)}")
            return jsonify({'error': 'Failed to update task'}), 400

    @app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """Delete a task"""
        if task_id not in current_app.tasks:
            return jsonify({'error': 'Task not found'}), 404

        del current_app.tasks[task_id]
        logger.info(f"Deleted task: {task_id}")
        return jsonify({'message': 'Task deleted'}), 200

    # ============================================
    # Status & Health Endpoints
    # ============================================

    @app.route('/api/status', methods=['GET'])
    def status():
        """Get system status"""
        agents = current_app.agents
        tasks = current_app.tasks
        running_tasks = sum(1 for t in tasks.values() if t['status'] == 'running')
        completed_tasks = sum(1 for t in tasks.values() if t['status'] == 'completed')
        idle_agents = sum(1 for a in agents.values() if a['status'] == 'idle')

        return jsonify({
            'status': 'running',
            'timestamp': datetime.utcnow().isoformat(),
            'agents': {
                'total': len(agents),
                'idle': idle_agents,
                'active': len(agents) - idle_agents
            },
            'tasks': {
                'total': len(tasks),
                'running': running_tasks,
                'completed': completed_tasks,
                'pending': len(tasks) - running_tasks - completed_tasks
            }
        }), 200

    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running'
        }), 200

    @app.route('/api/v1/health', methods=['GET'])
    def health_v1():
        """Enhanced health check with Fortress status"""
        engine = current_app.extensions.get('fortress_engine')
        fortress_status = 'unavailable'
        fortress_stats = {}
        if engine:
            try:
                fortress_stats = engine.get_stats()
                fortress_status = 'healthy'
            except Exception:
                fortress_status = 'degraded'

        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running',
            'fortress': {
                'status': fortress_status,
                'stats': fortress_stats,
            }
        }), 200

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

            if task_id not in current_app.tasks:
                return jsonify({'error': 'Task not found'}), 404
            if agent_id not in current_app.agents:
                return jsonify({'error': 'Agent not found'}), 404

            task = current_app.tasks[task_id]
            agent = current_app.agents[agent_id]

            task['agent_id'] = agent_id
            task['status'] = 'assigned'
            agent['status'] = 'busy'

            logger.info(f"Assigned task {task_id} to agent {agent_id}")
            return jsonify({'task': task, 'agent': agent}), 200
        except Exception as e:
            logger.error(f"Error assigning task: {str(e)}")
            return jsonify({'error': 'Failed to assign task'}), 400

    @app.route('/api/workforce/summary', methods=['GET'])
    def workforce_summary():
        """Get workforce summary and statistics"""
        agents = current_app.agents
        tasks = current_app.tasks
        agent_capabilities = {}
        for agent in agents.values():
            for cap in agent.get('capabilities', []):
                if cap not in agent_capabilities:
                    agent_capabilities[cap] = 0
                agent_capabilities[cap] += 1

        return jsonify({
            'agents_count': len(agents),
            'tasks_count': len(tasks),
            'capabilities': agent_capabilities,
            'agents': list(agents.values()),
            'tasks': list(tasks.values())
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
    app.run(host='0.0.0.0', port=8080, debug=False)
