# Examples Overview

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the API server:
   ```bash
   python app.py
   ```

---

## Examples

### 1. `simple_agent.py` — Single Agent

**What it does:** Creates one agent, submits a task, runs it to completion,
queries the result, and cleans up.

**Run:**
```bash
python examples/simple_agent.py
```

**Expected output:**
```
── 1. Health Check ──────────────────────
✓  API healthy: healthy
── 2. Create Agent ──────────────────────
✓  Created agent: <uuid>
...
✓  Clean-up done
```

**Modify:** Change `capabilities`, task `name`, or `result` payload to fit your use case.

---

### 2. `multi_agent_workflow.py` — Parallel Agents

**What it does:** Spins up 3 agents concurrently using `ThreadPoolExecutor`,
each running 2 tasks, then collects and reports results.

**Run:**
```bash
python examples/multi_agent_workflow.py
```

**Expected output:**
```
── Multi-Agent Workflow ─────────────────
✓  API reachable
── Launching agents in parallel ─────────
✓  Agent 0 completed 2 tasks
✓  Agent 1 completed 2 tasks
✓  Agent 2 completed 2 tasks
```

**Modify:** Adjust `NUM_AGENTS` and `TASKS_PER_AGENT` constants at the top of the file.

---

### 3. `fortress_workflow.py` — Fortress Integration

**What it does:** Queries Fortress stats, creates a sandboxed agent, executes
a command via the Fortress endpoint, and queries the fact graph.

**Run:**
```bash
python examples/fortress_workflow.py
```

**Note:** Fortress-specific endpoints (`/api/v1/fortress/*`) return 404 if the
Fortress module is not installed. The example handles this gracefully.

**Modify:** Change the `command` in Step 4 to run your workload.

---

### 4. `cicd_pipeline.py` — CI/CD Simulation

**What it does:** Simulates deploying 3 services (`auth-service`,
`api-gateway`, `worker-service`) with health checks after each, automatic
rollback on failure, and final status reporting.

**Run:**
```bash
python examples/cicd_pipeline.py
```

**Expected output:**
```
── CI/CD Pipeline: Pre-Flight Check ─────
✓  API healthy – starting deployment pipeline
── Deploying Services ───────────────────
✓  Deployed auth-service
✓  Deployed api-gateway
✓  Deployed worker-service
── Pipeline Complete ────────────────────
✓  All 3 services deployed successfully
```

**Modify:** Update the `SERVICES` list and `deploy_service()` function to match
your actual services.

---

### 5. `interactive_demo.py` — Step-by-Step Tutorial

**What it does:** An interactive walkthrough that pauses at each step,
explains what is happening, and makes live API calls with educational output.
Ideal for onboarding new users.

**Run:**
```bash
python examples/interactive_demo.py
```

The demo will prompt you to press Enter at each stage. Use `Ctrl+C` to exit.

---

## Running All Examples

Use the helper script:

```bash
bash scripts/run_examples.sh
```

Or run each example manually:

```bash
for ex in simple_agent multi_agent_workflow fortress_workflow cicd_pipeline; do
    echo "=== $ex ===" && python examples/$ex.py
done
```
