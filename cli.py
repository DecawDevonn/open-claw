"""
cli.py - Main CLI entry point for OpenClaw using Click.

Commands:
  openclaw config   - Show current configuration
  openclaw status   - Check API status
  openclaw agents   - List / manage agents
  openclaw tasks    - List / manage tasks
  openclaw execute  - Execute a command on an agent
  openclaw facts    - Query the Fortress fact graph
  openclaw logs     - View agent logs (stub)
  openclaw deploy   - Deploy a workflow (stub)
"""
import json
import sys

import click

from config import get_config
from formatters import (
    bold, cyan, green, print_json, print_section, print_status, print_yaml,
    format_agent_table, format_task_table, red, yellow,
)
from openclaw_client import OpenClawClient, OpenClawError


def _make_client(ctx: click.Context) -> OpenClawClient:
    profile = ctx.obj.get('profile')
    verbose = ctx.obj.get('verbose', False)
    return OpenClawClient(profile=profile, log_requests=verbose)


# ---- Root command group ----

@click.group()
@click.option('--profile', '-p', default=None, help='Config profile (dev/staging/prod)')
@click.option('--output', '-o', default='table', type=click.Choice(['table', 'json', 'yaml']), help='Output format')
@click.option('--verbose', '-v', is_flag=True, default=False, help='Enable verbose logging')
@click.pass_context
def main(ctx: click.Context, profile: str, output: str, verbose: bool) -> None:
    """OpenClaw CLI - Agent orchestration and task management."""
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    ctx.obj['output'] = output
    ctx.obj['verbose'] = verbose


# ---- config command ----

@main.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration."""
    cfg = get_config(ctx.obj.get('profile'))
    print_section("Current Configuration")
    fmt = ctx.obj.get('output', 'table')
    data = cfg.as_dict()
    if fmt == 'json':
        print_json(data)
    elif fmt == 'yaml':
        print_yaml(data)
    else:
        for k, v in data.items():
            print(f"  {cyan(k):<25} {v}")


# ---- status command ----

@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check API status and health."""
    client = _make_client(ctx)
    print_section("API Status")
    try:
        health = client.get_health()
        sys_status = client.get_status()
        print_status(f"API healthy  [{health.get('timestamp', '')}]")
        fmt = ctx.obj.get('output', 'table')
        if fmt == 'json':
            print_json(sys_status)
        else:
            print_yaml(sys_status)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- agents command group ----

@main.group()
def agents() -> None:
    """List and manage agents."""


@agents.command('list')
@click.pass_context
def agents_list(ctx: click.Context) -> None:
    """List all agents."""
    client = _make_client(ctx)
    try:
        data = client.list_agents()
        fmt = ctx.obj.get('output', 'table')
        if fmt == 'json':
            print_json(data)
        elif fmt == 'yaml':
            print_yaml(data)
        else:
            print_section(f"Agents  ({len(data)} total)")
            format_agent_table(data)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


@agents.command('create')
@click.argument('name')
@click.option('--type', 'agent_type', default='generic', help='Agent type')
@click.option('--capabilities', '-c', multiple=True, help='Agent capabilities (repeatable)')
@click.pass_context
def agents_create(ctx: click.Context, name: str, agent_type: str, capabilities: tuple) -> None:
    """Create a new agent."""
    client = _make_client(ctx)
    try:
        agent = client.create_agent(name, agent_type=agent_type, capabilities=list(capabilities))
        print_status(f"Created agent {green(agent['id'])}  ({name})")
        if ctx.obj.get('output') == 'json':
            print_json(agent)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


@agents.command('delete')
@click.argument('agent_id')
@click.pass_context
def agents_delete(ctx: click.Context, agent_id: str) -> None:
    """Delete an agent by ID."""
    client = _make_client(ctx)
    try:
        client.delete_agent(agent_id)
        print_status(f"Deleted agent {agent_id}")
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- tasks command group ----

@main.group()
def tasks() -> None:
    """List and manage tasks."""


@tasks.command('list')
@click.option('--status', 'status_filter', default=None, help='Filter by status')
@click.option('--agent', 'agent_id', default=None, help='Filter by agent ID')
@click.pass_context
def tasks_list(ctx: click.Context, status_filter: str, agent_id: str) -> None:
    """List all tasks."""
    client = _make_client(ctx)
    try:
        data = client.get_tasks(status=status_filter, agent_id=agent_id)
        fmt = ctx.obj.get('output', 'table')
        if fmt == 'json':
            print_json(data)
        elif fmt == 'yaml':
            print_yaml(data)
        else:
            print_section(f"Tasks  ({len(data)} total)")
            format_task_table(data)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


@tasks.command('create')
@click.argument('name')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--agent', 'agent_id', default=None, help='Assign to agent ID')
@click.option('--priority', default='normal', type=click.Choice(['low', 'normal', 'high']), help='Task priority')
@click.pass_context
def tasks_create(ctx: click.Context, name: str, description: str, agent_id: str, priority: str) -> None:
    """Create a new task."""
    client = _make_client(ctx)
    try:
        task = client.create_task(name, description=description, agent_id=agent_id, priority=priority)
        print_status(f"Created task {green(task['id'])}  ({name})")
        if ctx.obj.get('output') == 'json':
            print_json(task)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- execute command ----

@main.command()
@click.argument('agent_id')
@click.argument('command')
@click.option('--no-approve', is_flag=True, default=False, help='Require manual approval')
@click.pass_context
def execute(ctx: click.Context, agent_id: str, command: str, no_approve: bool) -> None:
    """Execute a command on an agent."""
    client = _make_client(ctx)
    print_section(f"Executing on agent {agent_id}")
    print(f"  Command: {cyan(command)}")
    try:
        result = client.execute_command(agent_id, command, auto_approve=not no_approve)
        print_status("Execution complete")
        fmt = ctx.obj.get('output', 'table')
        if fmt == 'json':
            print_json(result)
        else:
            print_yaml(result)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- facts command ----

@main.command()
@click.option('--agent', default=None, help='Filter by agent')
@click.option('--tag', default=None, help='Filter by tag')
@click.pass_context
def facts(ctx: click.Context, agent: str, tag: str) -> None:
    """Query the Fortress fact graph."""
    client = _make_client(ctx)
    try:
        data = client.query_facts(agent=agent, tag=tag)
        fmt = ctx.obj.get('output', 'table')
        if fmt == 'json':
            print_json(data)
        elif fmt == 'yaml':
            print_yaml(data)
        else:
            print_section(f"Facts  ({len(data)} results)")
            from formatters import print_table
            print_table(data)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- logs command ----

@main.command()
@click.argument('agent_id', required=False)
@click.option('--tail', '-n', default=50, help='Number of lines to show')
@click.pass_context
def logs(ctx: click.Context, agent_id: str, tail: int) -> None:
    """View agent logs (requires logging endpoint)."""
    client = _make_client(ctx)
    print_section("Agent Logs")
    print(yellow("Note: Log streaming requires the /api/v1/logs endpoint."))
    try:
        status_data = client.get_status()
        print_yaml(status_data)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


# ---- deploy command ----

@main.command()
@click.argument('workflow', required=False)
@click.option('--dry-run', is_flag=True, default=False, help='Simulate deployment only')
@click.pass_context
def deploy(ctx: click.Context, workflow: str, dry_run: bool) -> None:
    """Deploy a workflow or configuration."""
    client = _make_client(ctx)
    label = workflow or 'default'
    print_section(f"Deploying workflow: {label}")
    if dry_run:
        print(yellow("Dry-run mode: no changes will be made."))
    try:
        health = client.get_health()
        print_status(f"API reachable  ({health.get('status', 'unknown')})")
        print_status("Deploy hook not yet configured – extend this command for your workflow", ok=False)
    except OpenClawError as exc:
        print_status(str(exc), ok=False)
        sys.exit(1)


if __name__ == '__main__':
    main()
