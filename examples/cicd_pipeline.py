"""
cicd_pipeline.py - CI/CD pipeline simulation example.

Demonstrates: deploy multiple services with health checks,
rollback capability, and logging & monitoring.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from openclaw_client import OpenClawClient, OpenClawError
from formatters import print_section, print_status, print_json, yellow, green, red

SERVICES = ['auth-service', 'api-gateway', 'worker-service']


def deploy_service(client: OpenClawClient, service_name: str) -> dict:
    """Simulate deploying a single service."""
    agent = client.create_agent(f"deploy-{service_name}", capabilities=["deploy"])
    task = client.create_task(
        f"Deploy {service_name}",
        description=f"CI/CD deployment of {service_name}",
        agent_id=agent['id'],
        priority='high',
    )
    client.update_task(task['id'], status='running')
    time.sleep(0.1)  # Simulate deploy time
    client.update_task(task['id'], status='completed', result={"service": service_name, "deployed": True})
    return {"agent_id": agent['id'], "task_id": task['id'], "service": service_name}


def health_check(client: OpenClawClient) -> bool:
    """Check that the API is still healthy."""
    try:
        health = client.get_health()
        return health.get('status') == 'healthy'
    except OpenClawError:
        return False


def rollback(client: OpenClawClient, deployments: list) -> None:
    """Simulate rolling back all deployments."""
    print_section("Rolling Back Deployments")
    for dep in reversed(deployments):
        task = client.create_task(
            f"Rollback {dep['service']}",
            description=f"Rollback for {dep['service']}",
            agent_id=dep['agent_id'],
            priority='high',
        )
        client.update_task(task['id'], status='running')
        client.update_task(task['id'], status='completed', result={"rolled_back": True})
        print_status(f"Rolled back {dep['service']}")
        client.delete_task(task['id'])


def run() -> None:
    client = OpenClawClient(profile='dev')
    deployments = []

    # 1. Pre-flight health check
    print_section("CI/CD Pipeline: Pre-Flight Check")
    if not health_check(client):
        print_status("API not reachable – aborting pipeline", ok=False)
        sys.exit(1)
    print_status("API healthy – starting deployment pipeline")

    # 2. Deploy services sequentially
    print_section("Deploying Services")
    pipeline_ok = True
    for service in SERVICES:
        try:
            dep = deploy_service(client, service)
            deployments.append(dep)
            print_status(f"Deployed {green(service)}")

            # Health check after each service
            if not health_check(client):
                print_status(f"Health check failed after {service}", ok=False)
                pipeline_ok = False
                break
        except OpenClawError as exc:
            print_status(f"Failed to deploy {service}: {exc}", ok=False)
            pipeline_ok = False
            break

    # 3. Rollback if needed
    if not pipeline_ok:
        rollback(client, deployments)
        print_status("Pipeline aborted and rolled back", ok=False)
    else:
        print_section("Pipeline Complete")
        print_status(f"All {len(SERVICES)} services deployed successfully")
        print_json([{"service": d["service"], "task_id": d["task_id"]} for d in deployments])

    # 4. Final system status
    print_section("System Status")
    try:
        status = client.get_status()
        print_json(status)
    except OpenClawError as exc:
        print(yellow(f"Status unavailable: {exc}"))

    # 5. Clean up
    print_section("Clean Up")
    for dep in deployments:
        try:
            client.delete_task(dep['task_id'])
            client.delete_agent(dep['agent_id'])
        except OpenClawError:
            pass
    print_status("Pipeline resources cleaned up")


if __name__ == '__main__':
    run()
