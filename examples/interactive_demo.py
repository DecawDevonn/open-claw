"""
interactive_demo.py - Step-by-step interactive tutorial for OpenClaw.

Walks through creating agents, submitting tasks, and querying results
with educational output and user prompts at each stage.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openclaw_client import OpenClawClient, OpenClawError
from formatters import print_section, print_status, print_json, yellow, cyan, bold


def pause(message: str = "Press Enter to continue...") -> None:
    try:
        input(f"\n  {yellow('▶')}  {message}")
    except (EOFError, KeyboardInterrupt):
        print("\nExiting demo.")
        sys.exit(0)


def run() -> None:
    print_section("🎓  Welcome to the OpenClaw Interactive Demo")
    print("""
  This demo will walk you through the core features of OpenClaw:
    1. Connecting to the API
    2. Creating an agent
    3. Submitting a task
    4. Updating task status
    5. Querying results
    6. Cleaning up
  """)
    pause("Ready to start? Press Enter...")

    client = OpenClawClient(profile='dev')

    # Step 1 — Connection
    print_section("Step 1: Connect to the API")
    print(f"  Connecting to: {cyan(client._config.base_url)}")
    try:
        health = client.get_health()
        print_status(f"Connected!  Status: {health.get('status')}")
    except OpenClawError as exc:
        print_status(f"Connection failed: {exc}", ok=False)
        print(yellow("\n  Make sure the API server is running:"))
        print("    python app.py")
        sys.exit(1)

    pause()

    # Step 2 — Create agent
    print_section("Step 2: Create an Agent")
    print("  Agents represent workers that can execute tasks.")
    agent = client.create_agent("demo-agent", agent_type='generic', capabilities=['demo', 'tutorial'])
    agent_id = agent['id']
    print_status(f"Agent created: {agent_id}")
    print_json(agent)

    pause()

    # Step 3 — Submit task
    print_section("Step 3: Submit a Task")
    print("  Tasks are units of work assigned to agents.")
    task = client.create_task(
        "Hello World Task",
        description="A simple demonstration task",
        agent_id=agent_id,
        priority='normal',
    )
    task_id = task['id']
    print_status(f"Task created: {task_id}")
    print_json(task)

    pause()

    # Step 4 — Update status
    print_section("Step 4: Update Task Status")
    print("  Move the task through its lifecycle: pending → running → completed.")
    client.update_task(task_id, status='running')
    print_status("Task is now RUNNING")

    pause()

    client.update_task(task_id, status='completed', result={"message": "Hello from OpenClaw! 🎉"})
    print_status("Task is now COMPLETED")

    pause()

    # Step 5 — Query results
    print_section("Step 5: Query Results")
    print("  Retrieve the completed task and inspect its result.")
    result = client.get_task(task_id)
    print_json(result)

    pause()

    # Step 6 — System status
    print_section("Step 6: System Status")
    status = client.get_status()
    print_json(status)

    pause()

    # Step 7 — Clean up
    print_section("Step 7: Clean Up")
    print("  Remove the task and agent we created during this demo.")
    client.delete_task(task_id)
    print_status(f"Deleted task {task_id}")
    client.delete_agent(agent_id)
    print_status(f"Deleted agent {agent_id}")

    print_section("🎉  Demo Complete!")
    print("""
  You've learned how to:
    ✓ Connect to the OpenClaw API
    ✓ Create and manage agents
    ✓ Submit, track, and complete tasks
    ✓ Query results and system status
    ✓ Clean up resources

  Next steps:
    • Explore the CLI:       python cli.py --help
    • Run more examples:     ls examples/
    • Read the docs:         cat docs/QUICKSTART.md
  """)


if __name__ == '__main__':
    run()
