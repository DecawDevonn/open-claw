"""
fortress_workflow.py - Fortress integration example.

Demonstrates: query fact graph, check Fortress stats, execute via Fortress
endpoint, and monitor execution.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openclaw_client import OpenClawClient, OpenClawError
from formatters import print_section, print_status, print_json, print_yaml, yellow


def run() -> None:
    client = OpenClawClient(profile='dev')

    # 1. Health check
    print_section("1. Health Check")
    try:
        health = client.get_health()
        print_status(f"API healthy: {health.get('status')}")
    except OpenClawError as exc:
        print_status(f"API unreachable: {exc}", ok=False)
        sys.exit(1)

    # 2. Fortress stats
    print_section("2. Fortress Engine Stats")
    try:
        stats = client.get_fortress_stats()
        print_yaml(stats)
    except OpenClawError as exc:
        print(yellow(f"Fortress stats unavailable: {exc}"))

    # 3. Create an agent for Fortress execution
    print_section("3. Create Fortress Agent")
    agent = client.create_agent("fortress-agent", capabilities=["fortress", "sandboxed"])
    agent_id = agent['id']
    print_status(f"Created agent: {agent_id}")

    # 4. Execute via Fortress
    print_section("4. Execute Command via Fortress")
    try:
        result = client.execute_command(agent_id, "echo 'Hello from Fortress'", auto_approve=True)
        print_json(result)
    except OpenClawError as exc:
        print(yellow(f"Fortress execute not available: {exc}"))

    # 5. Query fact graph
    print_section("5. Query Fact Graph")
    try:
        facts = client.query_facts(agent=agent_id)
        print_json(facts)
    except OpenClawError as exc:
        print(yellow(f"Fact graph query not available: {exc}"))

    # 6. Monitor agent status
    print_section("6. Agent Status")
    updated = client.get_agent(agent_id)
    print_yaml(updated)

    # 7. Clean up
    print_section("7. Clean Up")
    client.delete_agent(agent_id)
    print_status("Clean-up done")


if __name__ == '__main__':
    run()
