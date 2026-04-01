from flask import Flask, jsonify, request
from datetime import datetime
import uuid
import logging


def create_app():
    """Application factory for creating Flask app instances."""
    flask_app = Flask(__name__)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app_logger = logging.getLogger(__name__)

    # In-memory storage (replace with database in production)
    store = {
        'agents': {},
        'tasks': {},
    }

    # ============================================
    # Agent Management Endpoints
    # ============================================

    @flask_app.route('/api/agents', methods=['POST'])
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

            store['agents'][agent_id] = agent
            app_logger.info(f"Created agent: {agent_id}")
            return jsonify(agent), 201
        except Exception as e:
            app_logger.error(f"Error creating agent: {str(e)}")
            return jsonify({'error': 'Request processing failed'}), 400

    @flask_app.route('/api/agents', methods=['GET'])
    def list_agents():
        """List all agents"""
        return jsonify(list(store['agents'].values())), 200

    @flask_app.route('/api/agents/<agent_id>', methods=['GET'])
    def get_agent(agent_id):
        """Get details of a specific agent"""
        agent = store['agents'].get(agent_id)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        return jsonify(agent), 200

    @flask_app.route('/api/agents/<agent_id>', methods=['PUT'])
    def update_agent(agent_id):
        """Update agent status or properties"""
        try:
            if agent_id not in store['agents']:
                return jsonify({'error': 'Agent not found'}), 404

            data = request.json
            agent = store['agents'][agent_id]

            if 'status' in data:
                agent['status'] = data['status']
            if 'capabilities' in data:
                agent['capabilities'] = data['capabilities']

            app_logger.info(f"Updated agent: {agent_id}")
            return jsonify(agent), 200
        except Exception as e:
            app_logger.error(f"Error updating agent: {str(e)}")
            return jsonify({'error': 'Request processing failed'}), 400

    @flask_app.route('/api/agents/<agent_id>', methods=['DELETE'])
    def delete_agent(agent_id):
        """Delete an agent"""
        if agent_id not in store['agents']:
            return jsonify({'error': 'Agent not found'}), 404

        del store['agents'][agent_id]
        app_logger.info(f"Deleted agent: {agent_id}")
        return jsonify({'message': 'Agent deleted'}), 200

    # ============================================
    # Task Management Endpoints
    # ============================================

    @flask_app.route('/api/tasks', methods=['POST'])
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

            store['tasks'][task_id] = task
            app_logger.info(f"Created task: {task_id}")
            return jsonify(task), 201
        except Exception as e:
            app_logger.error(f"Error creating task: {str(e)}")
            return jsonify({'error': 'Request processing failed'}), 400

    @flask_app.route('/api/tasks', methods=['GET'])
    def list_tasks():
        """List all tasks with optional filtering"""
        status_filter = request.args.get('status')
        agent_filter = request.args.get('agent_id')

        filtered_tasks = list(store['tasks'].values())

        if status_filter:
            filtered_tasks = [t for t in filtered_tasks if t['status'] == status_filter]
        if agent_filter:
            filtered_tasks = [t for t in filtered_tasks if t['agent_id'] == agent_filter]

        return jsonify(filtered_tasks), 200

    @flask_app.route('/api/tasks/<task_id>', methods=['GET'])
    def get_task(task_id):
        """Get details of a specific task"""
        task = store['tasks'].get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(task), 200

    @flask_app.route('/api/tasks/<task_id>', methods=['PUT'])
    def update_task(task_id):
        """Update task status or result"""
        try:
            if task_id not in store['tasks']:
                return jsonify({'error': 'Task not found'}), 404

            data = request.json
            task = store['tasks'][task_id]

            if 'status' in data:
                task['status'] = data['status']
                if data['status'] == 'running':
                    task['started_at'] = datetime.utcnow().isoformat()
                elif data['status'] == 'completed':
                    task['completed_at'] = datetime.utcnow().isoformat()

            if 'result' in data:
                task['result'] = data['result']

            app_logger.info(f"Updated task: {task_id}")
            return jsonify(task), 200
        except Exception as e:
            app_logger.error(f"Error updating task: {str(e)}")
            return jsonify({'error': 'Request processing failed'}), 400

    @flask_app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def delete_task(task_id):
        """Delete a task"""
        if task_id not in store['tasks']:
            return jsonify({'error': 'Task not found'}), 404

        del store['tasks'][task_id]
        app_logger.info(f"Deleted task: {task_id}")
        return jsonify({'message': 'Task deleted'}), 200

    # ============================================
    # Status & Health Endpoints
    # ============================================

    @flask_app.route('/api/status', methods=['GET'])
    def status():
        """Get system status"""
        agents = store['agents']
        tasks = store['tasks']
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

    @flask_app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running'
        }), 200

    # ============================================
    # Workforce Management Endpoints
    # ============================================

    @flask_app.route('/api/workforce/assign', methods=['POST'])
    def assign_task_to_agent():
        """Assign a task to an agent"""
        try:
            data = request.json
            task_id = data.get('task_id')
            agent_id = data.get('agent_id')

            if task_id not in store['tasks']:
                return jsonify({'error': 'Task not found'}), 404
            if agent_id not in store['agents']:
                return jsonify({'error': 'Agent not found'}), 404

            task = store['tasks'][task_id]
            agent = store['agents'][agent_id]

            task['agent_id'] = agent_id
            task['status'] = 'assigned'
            agent['status'] = 'busy'

            app_logger.info(f"Assigned task {task_id} to agent {agent_id}")
            return jsonify({'task': task, 'agent': agent}), 200
        except Exception as e:
            app_logger.error(f"Error assigning task: {str(e)}")
            return jsonify({'error': 'Request processing failed'}), 400

    @flask_app.route('/api/workforce/summary', methods=['GET'])
    def workforce_summary():
        """Get workforce summary and statistics"""
        agents = store['agents']
        tasks = store['tasks']
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

    @flask_app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({'error': 'Resource not found'}), 404

    @flask_app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        app_logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500

    return flask_app


# Module-level app for direct execution
app = create_app()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    logger.info("Starting open-claw API server...")
    app.run(host='0.0.0.0', port=8080, debug=False)
