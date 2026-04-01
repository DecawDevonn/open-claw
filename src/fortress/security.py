import re
import shlex
from typing import List, Optional

DEFAULT_ALLOWED_COMMANDS = [
    "ls", "cat", "echo", "pwd", "git", "python", "pip",
    "pytest", "find", "grep", "wc", "head", "tail", "diff"
]

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r">\s*/dev/sd",
    r"mkfs",
    r"dd\s+if=",
    r":(){ :|: & };:",
    r"\bsudo\b",
    r"/etc/passwd",
    r"/etc/shadow",
]


def is_command_allowed(command: str, allowed_commands: Optional[List[str]] = None) -> bool:
    """Check if a command is in the whitelist."""
    if allowed_commands is None:
        allowed_commands = DEFAULT_ALLOWED_COMMANDS
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    base_cmd = parts[0].split("/")[-1]  # handle full paths like /usr/bin/ls
    return base_cmd in allowed_commands


def is_dangerous(command: str) -> bool:
    """Check command for dangerous patterns."""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def validate_command(command: str, allowed_commands: Optional[List[str]] = None) -> tuple:
    """Validate a command. Returns (is_valid, reason)."""
    if is_dangerous(command):
        return False, "Command matches dangerous pattern"
    if not is_command_allowed(command, allowed_commands):
        return False, "Command not in whitelist"
    return True, "OK"
