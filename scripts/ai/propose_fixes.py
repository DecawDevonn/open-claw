#!/usr/bin/env python3
"""
AI-assisted static analysis and fix proposal script.

This script:
1. Runs static checks (mypy, flake8/ruff/black, pytest) on the repository.
2. Identifies low-risk, safe-to-fix issues (e.g. mypy var-annotated warnings).
3. Queries the OpenAI API with the relevant code context to generate a unified diff.
4. Applies the patch locally and reruns checks to confirm the fix is safe.
5. If checks pass, commits the fix to a branch named ai/proposed-fixes/<timestamp>
   and opens a draft pull request via the GitHub API.
6. Appends a summary entry to scripts/ai/run_log.json.
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_LOG_PATH = Path(__file__).resolve().parent / "run_log.json"
BRANCH_PREFIX = "ai/proposed-fixes"

# Low-risk mypy error codes that are safe to auto-fix.
LOW_RISK_MYPY_CODES = {"var-annotated"}

# ---------------------------------------------------------------------------
# Helper: run a subprocess and capture output
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run *cmd* in *cwd* and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Step 1 – Run static checks and collect findings
# ---------------------------------------------------------------------------

LOW_RISK_PATTERN = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+)(?::\d+)?: error: .+  \[(?P<code>[^\]]+)\]$"
)


def run_mypy() -> list[dict]:
    """Run mypy and return a list of low-risk finding dicts."""
    rc, stdout, stderr = _run(
        [sys.executable, "-m", "mypy", "--ignore-missing-imports", "."],
    )
    findings: list[dict] = []
    for line in stdout.splitlines():
        m = LOW_RISK_PATTERN.match(line)
        if m and m.group("code") in LOW_RISK_MYPY_CODES:
            findings.append(
                {
                    "tool": "mypy",
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "code": m.group("code"),
                    "message": line,
                }
            )
    log.info("mypy returned %d low-risk finding(s).", len(findings))
    return findings


def run_flake8() -> list[dict]:
    """Run flake8 (if available) and return findings for safe codes."""
    rc, stdout, _ = _run([sys.executable, "-m", "flake8", "--max-line-length=120", "."])
    if rc == 5:  # flake8 not found / no files checked
        return []
    findings: list[dict] = []
    # Only target missing whitespace around operators (E225) — low risk
    safe_codes = {"E225", "W291", "W293", "W292"}
    pattern = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\d+: (?P<code>[A-Z]\d+) ")
    for line in stdout.splitlines():
        m = pattern.match(line)
        if m and m.group("code") in safe_codes:
            findings.append(
                {
                    "tool": "flake8",
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "code": m.group("code"),
                    "message": line,
                }
            )
    log.info("flake8 returned %d low-risk finding(s).", len(findings))
    return findings


def run_pytest() -> tuple[bool, str]:
    """Run pytest and return (passed, summary_line)."""
    rc, stdout, stderr = _run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"])
    passed = rc == 0
    # Extract summary line (last non-empty line)
    lines = [l for l in stdout.splitlines() if l.strip()]
    summary = lines[-1] if lines else "(no output)"
    log.info("pytest %s – %s", "PASSED" if passed else "FAILED", summary)
    return passed, summary


# ---------------------------------------------------------------------------
# Step 2 – Query OpenAI for a unified diff fix
# ---------------------------------------------------------------------------


def _read_file_around(filepath: str, line: int, context: int = 10) -> str:
    """Return lines around *line* in *filepath* with line numbers."""
    path = REPO_ROOT / filepath
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    start = max(0, line - context - 1)
    end = min(len(lines), line + context)
    numbered = [f"{i + 1}: {lines[i]}" for i in range(start, end)]
    return "\n".join(numbered)


def query_openai_for_fix(finding: dict) -> Optional[str]:
    """
    Ask OpenAI to produce a minimal unified diff that fixes *finding*.
    Returns the diff string, or None if the API call fails or no key is set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        log.warning("OPENAI_API_KEY not set – skipping OpenAI query.")
        return None

    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:
        log.warning("openai package not installed – skipping OpenAI query.")
        return None

    snippet = _read_file_around(finding["file"], finding["line"])
    prompt = (
        "You are a Python static-analysis assistant. "
        "Produce ONLY a minimal unified diff (no explanations) that fixes the "
        f"following {finding['tool']} issue:\n\n"
        f"Issue: {finding['message']}\n\n"
        f"File: {finding['file']} (relevant lines shown below)\n"
        f"```\n{snippet}\n```\n\n"
        "Rules:\n"
        "- The fix must be safe and low-risk (e.g. adding a type annotation).\n"
        "- Do NOT refactor logic.\n"
        "- Output ONLY the unified diff starting with '--- a/' and '+++ b/'."
    )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        diff = response.choices[0].message.content or ""
        return diff.strip() if diff.strip().startswith("---") else None
    except Exception as exc:
        import openai as _openai

        if isinstance(exc, (_openai.OpenAIError, _openai.APIConnectionError)):
            log.error("OpenAI API error: %s", exc)
        else:
            log.error("Unexpected error while querying OpenAI: %s", exc)
            raise
        return None


# ---------------------------------------------------------------------------
# Step 3 – Apply patch and verify
# ---------------------------------------------------------------------------


def apply_and_verify(diff: str) -> bool:
    """
    Write *diff* to a temp file, apply it with `patch`, then rerun checks.
    Returns True only if the patch applies cleanly AND pytest still passes.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(diff)
        patch_file = f.name

    try:
        rc, stdout, stderr = _run(
            ["patch", "-p1", "--dry-run", "-i", patch_file],
        )
        if rc != 0:
            log.warning("Patch dry-run failed:\n%s", stderr)
            return False

        rc, stdout, stderr = _run(["patch", "-p1", "-i", patch_file])
        if rc != 0:
            log.warning("Patch apply failed:\n%s", stderr)
            return False

        passed, _ = run_pytest()
        return passed
    finally:
        Path(patch_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Step 4 – Commit to a branch and open a draft PR
# ---------------------------------------------------------------------------


def commit_and_open_pr(finding: dict, diff: str) -> Optional[str]:
    """
    Commit the current working-tree changes to a new branch and open a draft PR.
    Returns the PR URL on success, or None on failure.
    """
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo_name = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_token or not repo_name:
        log.warning("GITHUB_TOKEN / GITHUB_REPOSITORY not set – skipping PR creation.")
        return None

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"{BRANCH_PREFIX}/{timestamp}"

    # Configure git
    _run(["git", "config", "user.email", "ai-bot@users.noreply.github.com"])
    _run(["git", "config", "user.name", "AI Fix Bot"])

    # Create branch, stage and commit
    rc, _, err = _run(["git", "checkout", "-b", branch])
    if rc != 0:
        log.error("Failed to create branch %s: %s", branch, err)
        return None

    _run(["git", "add", "-A"])
    commit_msg = (
        f"fix({finding['tool']}): auto-fix {finding['code']} in {finding['file']} "
        f"line {finding['line']}"
    )
    _run(["git", "commit", "-m", commit_msg])

    # Push
    remote_url = (
        f"https://x-access-token:{github_token}@github.com/{repo_name}.git"
    )
    rc, _, err = _run(["git", "push", remote_url, f"HEAD:{branch}"])
    if rc != 0:
        log.error("Failed to push branch %s: %s", branch, err)
        return None

    # Open draft PR via PyGithub
    try:
        from github import Github  # type: ignore[import]
    except ImportError:
        log.warning("PyGithub not installed – branch pushed but no PR created.")
        return branch

    gh = Github(github_token)
    repo = gh.get_repo(repo_name)

    # Determine default branch
    default_branch = repo.default_branch

    pr_body = (
        "## AI-Proposed Fix\n\n"
        f"**Tool:** {finding['tool']}  \n"
        f"**Code:** {finding['code']}  \n"
        f"**File:** `{finding['file']}` line {finding['line']}  \n\n"
        "### Diff applied\n"
        f"```diff\n{diff}\n```\n\n"
        "> This PR was opened automatically by the `ai-propose-fixes` workflow. "
        "Please review carefully before merging."
    )

    pr = repo.create_pull(
        title=commit_msg,
        body=pr_body,
        head=branch,
        base=default_branch,
        draft=True,
    )
    log.info("Opened draft PR #%d: %s", pr.number, pr.html_url)
    return pr.html_url


# ---------------------------------------------------------------------------
# Step 5 – Append to run log
# ---------------------------------------------------------------------------


def append_run_log(entry: dict) -> None:
    """Append *entry* to scripts/ai/run_log.json."""
    try:
        existing: list = json.loads(RUN_LOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = []

    existing.append(entry)
    RUN_LOG_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    log.info("=== AI Propose Fixes – %s ===", datetime.now(tz=timezone.utc).isoformat())

    # Collect low-risk findings
    findings = run_mypy() + run_flake8()

    if not findings:
        log.info("No low-risk findings – nothing to fix.")
        append_run_log(
            {
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "findings": 0,
                "fixes_attempted": 0,
                "prs_opened": [],
            }
        )
        return

    log.info("Found %d low-risk finding(s) to attempt fixing.", len(findings))

    prs_opened: list[str] = []

    # Record the original branch so we can return to it after each iteration.
    _, original_branch, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    original_branch = original_branch.strip() or "main"

    for finding in findings:
        log.info("Processing: %s", finding["message"])

        diff = query_openai_for_fix(finding)
        if not diff:
            log.info("No diff produced for finding – skipping.")
            continue

        if not apply_and_verify(diff):
            log.info("Patch did not pass verification – skipping.")
            # Log the diff that failed before reverting to aid debugging.
            log.debug("Reverting failed diff:\n%s", diff)
            _run(["git", "checkout", "--", "."])
            continue

        pr_url = commit_and_open_pr(finding, diff)
        if pr_url:
            prs_opened.append(pr_url)

        # Return to the original branch for the next iteration.
        rc, _, err = _run(["git", "checkout", original_branch])
        if rc != 0:
            log.error("Failed to return to branch '%s': %s", original_branch, err)
            break

    log.info("Done. %d draft PR(s) opened.", len(prs_opened))

    append_run_log(
        {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "findings": len(findings),
            "fixes_attempted": len(findings),
            "prs_opened": prs_opened,
        }
    )


if __name__ == "__main__":
    main()
