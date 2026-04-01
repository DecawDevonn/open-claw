"""
multi_agent_workflow.py - Multi-agent parallel task execution example.

Demonstrates: create multiple agents, submit parallel tasks, coordinate
results, handle errors, and clean up.
"""
import sys
import os
import concurrent.futures

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openclaw_client import OpenClawClient, OpenClawError
from formatters import print_section, print_status, print_json, yellow

NUM_AGENTS = 3
TASKS_PER_AGENT = 2


def process_agent(client: OpenClawClient, index: int):
    """Create an agent, run tasks, return summary."""
    agent = client.create_agent(f"worker-{index}", capabilities=["compute"])
    agent_id = agent['id']
    results = []
    for t in range(TASKS_PER_AGENT):
        task = client.create_task(
            f"task-{index}-{t}",
            description=f"Worker {index}, task {t}",
            agent_id=agent_id,
            priority='normal',
        )
        client.update_task(task['id'], status='running')
        client.update_task(task['id'], status='completed', result={"worker": index, "task": t})
        results.append(task['id'])
    return {"agent_id": agent_id, "tasks": results}


def run() -> None:
    client = OpenClawClient(profile='dev')

    print_section("Multi-Agent Workflow")

    # 1. Health check
    try:
        client.get_health()
        print_status("API reachable")
    except OpenClawError as exc:
        print_status(f"API unreachable: {exc}", ok=False)
        sys.exit(1)

    # 2. Launch agents in parallel
    print_section("Launching agents in parallel")
    summaries = []
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_AGENTS) as pool:
        futures = {pool.submit(process_agent, client, i): i for i in range(NUM_AGENTS)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                summary = future.result()
                summaries.append(summary)
                print_status(f"Agent {idx} completed {len(summary['tasks'])} tasks")
            except OpenClawError as exc:
                errors.append(str(exc))
                print_status(f"Agent {idx} failed: {exc}", ok=False)

    # 3. Summarize
    print_section("Workflow Summary")
    print_json({"completed": summaries, "errors": errors})

    # 4. Clean up
    print_section("Clean Up")
    for summary in summaries:
        for task_id in summary['tasks']:
            try:
                client.delete_task(task_id)
            except OpenClawError:
                pass
        try:
            client.delete_agent(summary['agent_id'])
        except OpenClawError:
            pass
    print_status(f"Cleaned up {len(summaries)} agents")
    if errors:
        print(yellow(f"  {len(errors)} error(s) encountered during workflow"))


if __name__ == '__main__':
    run()
