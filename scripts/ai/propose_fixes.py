"""
Devonn Autonomous Fix Engine
============================
Detects CI failures, generates LLM-powered patches, opens PRs automatically.

Trigger conditions:
  - pytest failures
  - flake8 lint errors
  - New GitHub issues (via issue-trigger workflow)
  - Scheduled 30-minute sweep

Usage:
  python scripts/ai/propose_fixes.py [--issue-body "..."] [--dry-run]
"""

import subprocess
import json
import os
import sys
import argparse
import textwrap
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
REPO = os.environ.get("GITHUB_REPOSITORY", "DecawDevonn/open-claw")
BASE_BRANCH = "main"
OUTPUT_BRANCH = f"auto/fix-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", os.environ.get("GH_TOKEN_WRITE", ""))
MAX_PATCH_CHARS = 8000  # guard against runaway LLM output


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def run_tests() -> tuple[int, str]:
    """Run pytest and return (exit_code, combined_output)."""
    result = run(["python", "-m", "pytest", "--maxfail=5",
                  "--disable-warnings", "-q", "--tb=short"])
    return result.returncode, (result.stdout + result.stderr)[:6000]


def run_lint() -> tuple[int, str]:
    """Run flake8 and return (exit_code, output)."""
    result = run(["python", "-m", "flake8", ".", "--max-line-length=120",
                  "--exclude=.git,__pycache__,venv,.venv,node_modules"])
    return result.returncode, result.stdout[:3000]


def collect_source_context() -> str:
    """Collect key source files for the LLM to reason about."""
    context_parts = []
    key_files = ["app.py", "storage/base.py", "storage/memory.py",
                 "storage/mongo.py", "tests/test_api.py"]
    for path in key_files:
        p = Path(path)
        if p.exists():
            content = p.read_text()[:2000]
            context_parts.append(f"### {path}\n```python\n{content}\n```")
    return "\n\n".join(context_parts)


def generate_fix_with_llm(failure_logs: str, issue_body: str = "") -> str:
    """Call OpenAI to generate a unified diff patch for the failures."""
    if not OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY not set — skipping LLM fix generation")
        return ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        print("⚠️  openai package not installed — skipping LLM fix generation")
        return ""

    source_ctx = collect_source_context()
    issue_section = f"\n\n### GitHub Issue\n{issue_body}" if issue_body else ""

    prompt = textwrap.dedent(f"""
        You are an expert Python engineer working on the `open-claw` Flask API project.
        Your job is to produce a minimal, correct unified diff patch that fixes the failures below.

        ## Failure Logs
        ```
        {failure_logs[:3000]}
        ```
        {issue_section}

        ## Source Context
        {source_ctx[:4000]}

        ## Instructions
        - Output ONLY a valid unified diff (git diff format) — no prose, no markdown fences.
        - Keep changes minimal and surgical.
        - Do not change test files unless the test itself is wrong.
        - If no fix is possible, output exactly: NO_FIX
    """).strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.1,
        )
        patch = response.choices[0].message.content.strip()
        return patch[:MAX_PATCH_CHARS]
    except Exception as e:
        print(f"⚠️  LLM call failed: {e}")
        return ""


def apply_patch(patch: str) -> bool:
    """Apply a unified diff patch. Returns True on success."""
    if not patch or patch == "NO_FIX":
        return False
    patch_file = Path("auto_fix.patch")
    patch_file.write_text(patch)
    result = run(["git", "apply", "--check", "auto_fix.patch"])
    if result.returncode != 0:
        print(f"⚠️  Patch does not apply cleanly:\n{result.stderr[:500]}")
        patch_file.unlink(missing_ok=True)
        return False
    run(["git", "apply", "auto_fix.patch"], check=True)
    patch_file.unlink(missing_ok=True)
    return True


def create_branch() -> None:
    run(["git", "checkout", "-b", OUTPUT_BRANCH], check=True)


def commit_and_push(message: str) -> None:
    run(["git", "config", "user.email", "devonn-ai@users.noreply.github.com"])
    run(["git", "config", "user.name", "Devonn AI Agent"])
    run(["git", "add", "."], check=True)
    run(["git", "commit", "-m", message], check=True)
    run(["git", "push", "origin", OUTPUT_BRANCH], check=True)


def open_pr(title: str, body: str) -> None:
    result = run([
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        "--base", BASE_BRANCH,
        "--label", "auto-fix",
    ])
    if result.returncode == 0:
        print(f"✅ PR created: {result.stdout.strip()}")
    else:
        print(f"⚠️  PR creation failed: {result.stderr[:300]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Devonn Autonomous Fix Engine")
    parser.add_argument("--issue-body", default="", help="GitHub issue body to fix")
    parser.add_argument("--dry-run", action="store_true", help="Run analysis only, no commits")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Devonn Autonomous Fix Engine  |  {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    # ── 1. Run tests ──────────────────────────────────────────────────────────
    print("🔍 Running test suite...")
    test_code, test_logs = run_tests()

    # ── 2. Run lint ───────────────────────────────────────────────────────────
    print("🔍 Running linter...")
    lint_code, lint_logs = run_lint()

    all_clear = (test_code == 0) and (lint_code == 0) and not args.issue_body

    if all_clear:
        print("\n✅ All checks pass — no action needed.")
        return

    # ── 3. Collect failure context ────────────────────────────────────────────
    failure_summary = ""
    if test_code != 0:
        failure_summary += f"## Test Failures\n```\n{test_logs}\n```\n\n"
    if lint_code != 0:
        failure_summary += f"## Lint Errors\n```\n{lint_logs}\n```\n\n"
    if args.issue_body:
        failure_summary += f"## GitHub Issue\n{args.issue_body}\n\n"

    print(f"\n⚠️  Issues detected:\n{failure_summary[:500]}...")

    # ── 4. Generate LLM fix ───────────────────────────────────────────────────
    print("\n🤖 Calling LLM fix engine...")
    patch = generate_fix_with_llm(failure_summary, args.issue_body)

    if not patch or patch == "NO_FIX":
        print("❌ LLM could not generate a fix — opening informational PR.")
        if args.dry_run:
            print("[DRY RUN] Would open informational PR.")
            return
        create_branch()
        open_pr(
            title=f"[Auto] CI failure detected — manual review needed",
            body=f"## Automated Detection\n\nThe Devonn Fix Engine detected failures but could not auto-patch them.\n\n{failure_summary[:2000]}"
        )
        return

    # ── 5. Apply patch ────────────────────────────────────────────────────────
    print("\n🔧 Applying generated patch...")
    applied = apply_patch(patch)

    if not applied:
        print("❌ Patch could not be applied cleanly.")
        return

    # ── 6. Re-run tests to validate fix ──────────────────────────────────────
    print("\n🔍 Re-running tests to validate fix...")
    retest_code, retest_logs = run_tests()

    if retest_code != 0:
        print("❌ Fix did not resolve all failures — discarding patch.")
        run(["git", "checkout", "--", "."])
        return

    print("✅ Fix validated — all tests pass!")

    if args.dry_run:
        print("[DRY RUN] Would commit and open PR.")
        run(["git", "checkout", "--", "."])
        return

    # ── 7. Commit, push, open PR ──────────────────────────────────────────────
    create_branch()
    commit_and_push("auto: AI-generated fix — all tests passing")
    open_pr(
        title=f"[Auto Fix] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        body=f"## Devonn Autonomous Fix\n\nThis PR was generated automatically by the Devonn AI Fix Engine.\n\n### Failures Detected\n{failure_summary[:1500]}\n\n### Patch Applied\n```diff\n{patch[:1000]}\n```\n\n✅ All tests pass after fix."
    )


if __name__ == "__main__":
    main()
