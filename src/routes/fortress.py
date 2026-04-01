from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

fortress_bp = Blueprint('fortress', __name__, url_prefix='/api/v1/fortress')


def get_engine():
    return current_app.extensions.get('fortress_engine')


@fortress_bp.route('/agents/<agent_id>/execute', methods=['POST'])
def execute_command(agent_id):
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    data = request.get_json() or {}
    command = data.get('command', '')
    auto_approve = data.get('auto_approve', False)
    if not command:
        return jsonify({'error': 'command is required'}), 400
    result = engine.execute_command(command, agent_id, auto_approve=auto_approve)
    return jsonify({
        'agent_id': agent_id,
        'command': result['command'],
        'result': result['result'],
        'allowed': result.get('allowed', False),
        'fact_id': result.get('fact_id', ''),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }), 200


@fortress_bp.route('/facts', methods=['GET'])
def list_facts():
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    agent = request.args.get('agent')
    tags = request.args.getlist('tag')
    facts = engine.list_facts(agent=agent, tags=tags if tags else None)
    return jsonify({'facts': facts, 'count': len(facts)}), 200


@fortress_bp.route('/facts/<fact_id>', methods=['GET'])
def get_fact(fact_id):
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    fact = engine.get_fact(fact_id)
    if not fact:
        return jsonify({'error': 'Fact not found'}), 404
    return jsonify(fact), 200


@fortress_bp.route('/agents/<agent_id>/worktree', methods=['POST'])
def create_worktree(agent_id):
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    data = request.get_json() or {}
    branch = data.get('branch', f'agent-{agent_id}')
    project_root = data.get('project_root', '.')
    info = engine.create_worktree(agent_id, branch, project_root)
    return jsonify(info), 201


@fortress_bp.route('/context', methods=['GET'])
def get_context():
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    return jsonify(engine.get_context_summary()), 200


@fortress_bp.route('/mailbox/<agent_id>', methods=['GET'])
def read_mailbox(agent_id):
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    messages = engine.read_mailbox(agent_id)
    return jsonify({'agent_id': agent_id, 'messages': messages, 'count': len(messages)}), 200


@fortress_bp.route('/mailbox/<agent_id>', methods=['DELETE'])
def clear_mailbox(agent_id):
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    count = engine.clear_mailbox(agent_id)
    return jsonify({'agent_id': agent_id, 'cleared': count}), 200


@fortress_bp.route('/stats', methods=['GET'])
def get_stats():
    engine = get_engine()
    if not engine:
        return jsonify({'error': 'Fortress engine not initialized'}), 503
    return jsonify(engine.get_stats()), 200
