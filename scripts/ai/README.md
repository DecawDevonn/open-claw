# AI Propose Fixes

This directory contains the LLM-assisted static-analysis workflow that automatically proposes low-risk code fixes by opening **draft pull requests**.

---

## How it works

1. **Trigger** – The workflow runs daily at 02:00 UTC (`schedule`) or on demand (`workflow_dispatch`).
2. **Static checks** – `propose_fixes.py` runs:
   - `mypy` (collects `var-annotated` and other low-risk warnings)
   - `flake8` (collects safe style codes: `E225`, `W291`, `W293`, `W292`)
   - `pytest` (used as a safety gate before and after patching)
3. **OpenAI query** – For each low-risk finding the script sends the relevant code snippet to `gpt-4o-mini` and requests a minimal unified diff.
4. **Patch & verify** – The diff is applied with `patch -p1`. If `pytest` still passes the patch is kept; otherwise it is reverted.
5. **Draft PR** – A new branch `ai/proposed-fixes/<timestamp>` is pushed and a **draft** pull request is opened via the GitHub API so a human can review before merging.
6. **Run log** – Every run appends a JSON entry to `scripts/ai/run_log.json` (timestamp, number of findings, PRs opened).

---

## Required secrets

| Secret | Purpose |
|---|---|
| `OPENAI_API_KEY` | Authenticate with the OpenAI API |
| `GITHUB_TOKEN` | Automatically provided by GitHub Actions – used to push branches and open PRs |

---

## Running locally

```bash
# Install dependencies
pip install -r scripts/ai/requirements.txt

# Optional: set your OpenAI key
export OPENAI_API_KEY=sk-...

# Run from the repository root
python scripts/ai/propose_fixes.py
```

Without `OPENAI_API_KEY` the script will still run all static checks and log results to `run_log.json`; it will simply skip the OpenAI query and patch steps.

---

## Files

| File | Description |
|---|---|
| `propose_fixes.py` | Main script |
| `requirements.txt` | Python dependencies |
| `run_log.json` | Append-only log of every script run |
| `README.md` | This file |
