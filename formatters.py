"""
formatters.py - Output formatting helpers for the OpenClaw CLI.

Provides pretty-printed tables, JSON, YAML, and colored output.
"""
import json
import sys
from typing import Any, Dict, List, Optional

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLOR_AVAILABLE = True
except ImportError:
    COLOR_AVAILABLE = False


# ---- Color helpers ----

def _color(text: str, color_code: str) -> str:
    if COLOR_AVAILABLE:
        return f"{color_code}{text}{Style.RESET_ALL}"
    return text


def green(text: str) -> str:
    return _color(text, Fore.GREEN) if COLOR_AVAILABLE else text


def red(text: str) -> str:
    return _color(text, Fore.RED) if COLOR_AVAILABLE else text


def yellow(text: str) -> str:
    return _color(text, Fore.YELLOW) if COLOR_AVAILABLE else text


def cyan(text: str) -> str:
    return _color(text, Fore.CYAN) if COLOR_AVAILABLE else text


def bold(text: str) -> str:
    if COLOR_AVAILABLE:
        return f"{Style.BRIGHT}{text}{Style.RESET_ALL}"
    return text


# ---- Output formatters ----

def print_json(data: Any) -> None:
    """Pretty-print data as JSON."""
    print(json.dumps(data, indent=2, default=str))


def print_table(rows: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
    """Print a list of dicts as a formatted table."""
    if not rows:
        print(yellow("No results."))
        return

    if columns is None:
        columns = list(rows[0].keys())

    headers = [bold(c.upper().replace('_', ' ')) for c in columns]
    table_data = [[row.get(c, '') for c in columns] for row in rows]

    if TABULATE_AVAILABLE:
        print(tabulate(table_data, headers=headers, tablefmt='rounded_outline'))
    else:
        # Fallback: simple fixed-width table
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in table_data), default=0))
                      for i, h in enumerate(headers)]
        sep = '+-' + '-+-'.join('-' * w for w in col_widths) + '-+'
        row_fmt = '| ' + ' | '.join('{:<' + str(w) + '}' for w in col_widths) + ' |'
        print(sep)
        print(row_fmt.format(*headers))
        print(sep)
        for row in table_data:
            print(row_fmt.format(*[str(v) for v in row]))
        print(sep)


def print_yaml(data: Any, indent: int = 0) -> None:
    """Simple recursive YAML-style output (no external dependency)."""
    prefix = '  ' * indent
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{cyan(str(key))}:")
                print_yaml(value, indent + 1)
            else:
                print(f"{prefix}{cyan(str(key))}: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                print(f"{prefix}-")
                print_yaml(item, indent + 1)
            else:
                print(f"{prefix}- {item}")
    else:
        print(f"{prefix}{data}")


def print_status(message: str, ok: bool = True) -> None:
    """Print a status message with a colored indicator."""
    icon = green('✓') if ok else red('✗')
    print(f"{icon}  {message}")


def print_section(title: str) -> None:
    """Print a bold section header."""
    width = max(len(title) + 4, 40)
    border = '─' * width
    print(f"\n{cyan(border)}")
    print(f"  {bold(title)}")
    print(f"{cyan(border)}")


def format_agent_table(agents: List[Dict[str, Any]]) -> None:
    columns = ['id', 'name', 'type', 'status', 'tasks_completed']
    print_table(agents, columns)


def format_task_table(tasks: List[Dict[str, Any]]) -> None:
    columns = ['id', 'name', 'status', 'priority', 'agent_id']
    print_table(tasks, columns)
