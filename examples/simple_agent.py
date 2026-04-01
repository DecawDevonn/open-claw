"""
simple_agent.py - Basic single-agent example.

Demonstrates: connect → create agent → create & assign task → clean up.
Run with the API server running on http://localhost:8080.
"""
import sys
import os

# Allow running from the examples/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openclaw_client import OpenClawClient, OpenClawError
from formatters import print_section, print_status, print_json


def run() -> None:
    client = OpenClawClient(profile='dev')

    # 1. Health check
    print_section("1. Health Check")
    try:
        health = client.get_health()
        print_status(f"API healthy: {health}")
    except OpenClawError as exc:
        print_status(f"Cannot reach API: {exc}", ok=False)
        sys.exit(1)

    # 2. Create agent
    print_section("2. Create Agent")
    agent = client.create_agent("example-agent", capabilities=["compute", "storage"])
    agent_id = agent['id']
    print_status(f"Created agent: {agent_id}")

    # 3. Create task
    print_section("3. Create Task")
    task = client.create_task(
        "Example Task",
        description="Run a simple compute workload",
        agent_id=agent_id,
        priority='normal',
    )
    task_id = task['id']
    print_status(f"Created task: {task_id}")

    # 4. Mark task running then completed
    print_section("4. Update Task Status")
    client.update_task(task_id, status='running')
    print_status("Task running")
    client.update_task(task_id, status='completed', result={"output": "Hello from OpenClaw!"})
    print_status("Task completed")

    # 5. Query results
    print_section("5. Query Results")
    result = client.get_task(task_id)
    print_json(result)

    # 6. Clean up
    print_section("6. Clean Up")
    client.delete_task(task_id)
    client.delete_agent(agent_id)
    print_status("Clean-up done")


if __name__ == '__main__':
    run()
