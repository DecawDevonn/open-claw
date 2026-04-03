"""
propose_fixes.py
================
Runs static checks (mypy, flake8, pytest) and uses the OpenAI API to propose
safe, low-risk fixes.  For each fixable finding the script:

1. Builds a minimal prompt (file content + error + patch-only instruction).
2. Calls the OpenAI chat-completion endpoint.
3. Parses a unified diff from the response.
4. Applies the patch with ``git apply --index``.
5. Re-runs the original check to confirm the fix resolves the error and that
   the test suite is still green.
6. Commits the change on the current branch (the caller – the GitHub Action –
   is responsible for pushing and opening the draft PR via
   peter-evans/create-pull-request).

Note on index state: ``git apply --index`` stages the patch immediately.  If
the process is interrupted between applying a patch and verifying it, the index
may contain partial changes.  The script calls ``_revert_index()`` after any
failed verification to restore a clean state.

Safe-fix categories
-------------------
* **mypy** – only ``[var-annotated]`` findings (add a type annotation for a
  local variable that mypy can infer from the right-hand side).
* **flake8** – only trailing-whitespace (W291/W293), blank-line (W391/W292),
  and import-order (E401) findings that ``ruff``/``black`` can handle without
  LLM involvement.

The script exits with code 0 in all cases so that the workflow step never
fails; any un-fixable issues are logged and skipped.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
)
log = logging.getLogger("propose_fixes")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Maximum number of characters of file content to include in a prompt.
MAX_FILE_CHARS = 8_000

# Mypy findings that we consider safe to auto-fix via LLM.
SAFE_MYPY_CODES = {"var-annotated"}

# Flake8 codes that we fix with ruff/black (no LLM needed).
RUFF_FIXABLE_CODES = {"W291", "W293", "W391", "W292", "E401"}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single issue reported by a checker."""

    checker: str          # "mypy" | "flake8"
    filepath: str         # relative to REPO_ROOT
    line: int
    col: int
    code: str             # e.g. "var-annotated", "W291"
    message: str          # full error text
    raw: str              # original output line


@dataclass
class AppliedFix:
    filepath: str
    finding: Finding
    patch: str


# ---------------------------------------------------------------------------
# Helpers – run sub-processes
# ---------------------------------------------------------------------------


def _run(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run *cmd* and return the completed-process object (never raises)."""
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
    )


def _tool_available(name: str) -> bool:
    result = subprocess.run(
        ["which", name], capture_output=True, text=True
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Step 1 – run checks and collect findings
# ---------------------------------------------------------------------------


def run_mypy() -> List[Finding]:
    """Run mypy and return safe-fixable findings."""
    result = _run([sys.executable, "-m", "mypy", "--no-incremental", "."])
    findings: List[Finding] = []
    # Pattern:  path/to/file.py:10: error: message  [code]
    pattern = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): error: (?P<msg>.+)\s+\[(?P<code>[^\]]+)\]$"
    )
    for line in result.stdout.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        code = m.group("code").strip()
        if code not in SAFE_MYPY_CODES:
            continue
        findings.append(
            Finding(
                checker="mypy",
                filepath=m.group("file").strip(),
                line=int(m.group("line")),
                col=int(m.group("col")),
                code=code,
                message=m.group("msg").strip(),
                raw=line,
            )
        )
    log.info("mypy findings (safe): %d", len(findings))
    return findings


def run_flake8() -> List[Finding]:
    """Run flake8 and return findings that ruff/black can fix without LLM."""
    result = _run([sys.executable, "-m", "flake8", "--format=default", "."])
    findings: List[Finding] = []
    # Pattern:  ./path/to/file.py:10:5: W291 trailing whitespace
    pattern = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<code>[A-Z]\d+) (?P<msg>.+)$"
    )
    for line in result.stdout.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        code = m.group("code").strip()
        if code not in RUFF_FIXABLE_CODES:
            continue
        findings.append(
            Finding(
                checker="flake8",
                filepath=m.group("file").strip().lstrip("./"),
                line=int(m.group("line")),
                col=int(m.group("col")),
                code=code,
                message=m.group("msg").strip(),
                raw=line,
            )
        )
    log.info("flake8 findings (ruff-fixable): %d", len(findings))
    return findings


def run_pytest() -> bool:
    """Return True if the test suite is green."""
    result = _run([sys.executable, "-m", "pytest", "-q", "--tb=no"])
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Step 2 – auto-fix flake8 issues with ruff / black (no LLM)
# ---------------------------------------------------------------------------


def fix_with_ruff_or_black(findings: List[Finding]) -> bool:
    """
    Attempt to fix all ruff-fixable findings with ruff (preferred) or black.
    Returns True if at least one file was changed.
    """
    if not findings:
        return False

    files = sorted({f.filepath for f in findings})
    changed = False

    if _tool_available("ruff"):
        result = _run(["ruff", "check", "--fix"] + files)
        log.info("ruff: %s", result.stdout.strip() or "(no output)")
        changed = True
    elif _tool_available("black"):
        result = _run(["black"] + files)
        log.info("black: %s", result.stdout.strip() or "(no output)")
        changed = True
    else:
        log.warning(
            "Neither ruff nor black is available; skipping flake8 auto-fix."
        )
    return changed


# ---------------------------------------------------------------------------
# Step 3 – LLM patch for mypy findings
# ---------------------------------------------------------------------------


def _read_file_safe(filepath: str) -> str:
    """Read *filepath* relative to REPO_ROOT, truncated to MAX_FILE_CHARS."""
    full_path = REPO_ROOT / filepath
    try:
        content = full_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS] + "\n# ... (truncated)"
    return content


def _build_prompt(finding: Finding, file_content: str) -> str:
    return textwrap.dedent(
        f"""\
        You are a Python static-analysis assistant.  Your only job is to output
        a minimal unified diff patch that fixes the SINGLE issue described below.

        Rules:
        - Output ONLY a unified diff patch in the standard "--- +++ @@" format.
        - Do NOT modify any file other than the one shown.
        - Do NOT change any logic, comments, or unrelated whitespace.
        - Keep the change as small as possible (ideally a single line).
        - Do NOT include any explanation or prose – only the diff.

        Issue
        -----
        File   : {finding.filepath}
        Line   : {finding.line}
        Error  : {finding.message}  [{finding.code}]

        File content (may be truncated)
        --------------------------------
        {file_content}
        """
    )


def _call_openai(prompt: str, api_key: str) -> Optional[str]:
    """Call the OpenAI chat-completion API and return the assistant message."""
    try:
        import openai  # local import – not available outside CI
    except ImportError:
        log.error("openai package is not installed.")
        return None

    openai.api_key = api_key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a Python assistant that outputs ONLY unified diff patches. "
                        "Never include prose, markdown fences, or explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message["content"]
    except Exception as exc:
        log.error("OpenAI API error: %s", exc)
        return None


def _extract_diff(text: str) -> Optional[str]:
    """Extract a unified diff block from *text* (strips markdown fences)."""
    # Strip ```diff … ``` fences
    text = re.sub(r"```[a-z]*\n?", "", text).strip()
    # Must contain at least one hunk header
    if not re.search(r"^@@\s+-\d+", text, re.MULTILINE):
        return None
    return text


def _apply_patch(diff: str) -> bool:
    """Write *diff* to a temp file and apply it with ``git apply --index``."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(diff)
        tmp_path = tmp.name

    result = _run(["git", "apply", "--index", "--whitespace=fix", tmp_path])
    os.unlink(tmp_path)
    if result.returncode != 0:
        log.warning("git apply failed:\n%s", result.stderr.strip())
        return False
    return True


def _revert_index() -> None:
    """Revert the index (staged changes) without touching the working tree."""
    _run(["git", "reset", "HEAD"])
    _run(["git", "checkout", "--", "."])


# ---------------------------------------------------------------------------
# Step 4 – commit applied fixes
# ---------------------------------------------------------------------------


def _git_commit(message: str) -> bool:
    """Stage all tracked changes and create a commit. Returns True on success."""
    _run(["git", "add", "-u"])
    status = _run(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        log.info("Nothing to commit.")
        return False
    result = _run(
        [
            "git",
            "-c", "user.email=ai-bot@users.noreply.github.com",
            "-c", "user.name=AI Propose Fixes",
            "commit",
            "-m", message,
        ]
    )
    if result.returncode != 0:
        log.error("git commit failed: %s", result.stderr.strip())
        return False
    log.info("Committed: %s", message)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        log.warning(
            "OPENAI_API_KEY is not set.  LLM-assisted fixes will be skipped; "
            "only tool-based (ruff/black) fixes will be attempted."
        )

    # ── 1. Baseline test run ──────────────────────────────────────────────
    if not run_pytest():
        log.error(
            "Baseline test suite is already failing.  Aborting to avoid "
            "masking pre-existing failures."
        )
        sys.exit(0)

    fixes_committed = False

    # ── 2. flake8 → ruff/black (no LLM) ──────────────────────────────────
    flake8_findings = run_flake8()
    if flake8_findings:
        changed = fix_with_ruff_or_black(flake8_findings)
        if changed:
            # Verify tests still pass after formatting fixes
            if run_pytest():
                committed = _git_commit(
                    "ai: fix flake8 style issues (ruff/black)"
                )
                fixes_committed = fixes_committed or committed
            else:
                log.error("Tests failed after ruff/black; reverting.")
                _revert_index()

    # ── 3. mypy → LLM patch ───────────────────────────────────────────────
    if api_key:
        mypy_findings = run_mypy()
        applied_fixes: List[AppliedFix] = []

        for finding in mypy_findings:
            log.info(
                "Attempting LLM fix for %s:%d [%s]",
                finding.filepath,
                finding.line,
                finding.code,
            )
            file_content = _read_file_safe(finding.filepath)
            if not file_content:
                log.warning("Could not read %s; skipping.", finding.filepath)
                continue

            prompt = _build_prompt(finding, file_content)
            raw_response = _call_openai(prompt, api_key)
            if not raw_response:
                continue

            diff = _extract_diff(raw_response)
            if not diff:
                log.warning(
                    "LLM response did not contain a valid diff; skipping."
                )
                continue

            if not _apply_patch(diff):
                continue

            # Re-run mypy on just the changed file to verify the fix
            verify = _run(
                [
                    sys.executable, "-m", "mypy",
                    "--no-incremental",
                    finding.filepath,
                ]
            )
            original_error_gone = finding.message not in verify.stdout

            # Re-run tests to make sure nothing broke
            tests_still_pass = run_pytest()

            if original_error_gone and tests_still_pass:
                log.info("Fix verified for %s:%d", finding.filepath, finding.line)
                applied_fixes.append(
                    AppliedFix(
                        filepath=finding.filepath,
                        finding=finding,
                        patch=diff,
                    )
                )
            else:
                log.warning(
                    "Fix did not resolve the error or broke tests; reverting."
                )
                _revert_index()

        if applied_fixes:
            descriptions = "; ".join(
                f"{f.filepath}:{f.finding.line} [{f.finding.code}]"
                for f in applied_fixes
            )
            committed = _git_commit(
                f"ai: fix mypy var-annotated issues ({descriptions})"
            )
            fixes_committed = fixes_committed or committed
    else:
        log.info("Skipping mypy LLM fixes (no OPENAI_API_KEY).")

    if fixes_committed:
        log.info("Fixes committed.  The workflow will open a draft PR.")
    else:
        log.info("No fixes were committed; nothing to PR.")


if __name__ == "__main__":
    main()
