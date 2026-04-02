# DEVONN.AI v4 — Autonomous System Architecture

This document describes the closed-loop autonomous intelligence architecture of DEVONN.AI v4, covering the full execution pipeline, control center, self-improving loop, and infrastructure layer.

---

## System Overview

DEVONN.AI v4 is a **closed-loop autonomous intelligence architecture** composed of five integrated layers:

| Layer | Function |
|---|---|
| Cognition | Meta-planning + task planning |
| Execution | Parallel agent spawning + tool use |
| Evaluation | Metrics, scoring, and memory |
| Adaptation | Strategy and loop adjustment |
| Evolution | Self-refactor suggestions |

---

## 1. Core Intelligence Flow (Top Layer)

This is the primary execution pipeline — what happens when a task enters the system.

```
Input Task
    ↓
Meta-Planner (Strategy Engine)
    ↓
Task Planner (LangGraph Orchestrator)
    ↓
Agent Spawner
    ↓
Parallel Executors (ag1 | ag2 | ag3)
    ↓
Evaluator (Memory Layer)
    ↓
Loop & Adjust
    ↓
Self-Refactor Engine
    ↓
(back to Meta-Planner)
```

### Meta-Planner (Strategy Engine)

- Decides *how* to approach a task
- Chooses strategy: single agent vs multi-agent, depth vs speed
- Acts as the executive decision maker

### Task Planner (LangGraph Orchestrator)

- Breaks the goal into structured steps
- Creates a stateful execution graph
- Handles dependencies between steps
- LangGraph operates here as the state engine

### Agent Spawner

- Dynamically creates specialized agents:
  - **Researcher** — information gathering
  - **Analyzer** — data processing and reasoning
  - **Validator** — output verification
- Each agent has a defined role and toolset
- Acts as the modular intelligence factory

### Parallel Executors (ag1, ag2, ag3)

- Agents run simultaneously
- Each works on a different part of the problem
- Improves speed and coverage
- Enables true parallel cognition

### Evaluator (Memory Layer)

Stores results into two memory backends:

- **Neo4j** — graph relationships between entities, tasks, and outcomes
- **Vector DB** — semantic memory for similarity-based retrieval

Measures:
- Success rate
- Performance
- Accuracy

This is the system's learning backbone.

### Loop & Adjust

Uses evaluation feedback to:
- Retry failed subtasks
- Reduce agent count when over-provisioned
- Change strategy based on outcome data

This is adaptive intelligence in action.

### Self-Refactor Engine

- Generates optimization suggestions based on performance data
- Example suggestion: "Reduce agents from 5 → 3"
- Does **not** auto-execute changes (safety layer)
- All proposals require operator review before application

---

## 2. Control Center (Bottom Left — Observability)

Real-time visibility into system operations.

| Component | Description |
|---|---|
| Live Dashboard | Real-time agent activity and task status |
| Agent Tracker | Per-agent progress and role assignment |
| Success Metrics | Task completion rates (e.g., 100% success) |
| Proposal Log | Queue of pending self-refactor suggestions |

This section serves as mission control for AI operations.

---

## 3. Self-Improving Loop (Bottom Right)

The most important feature of v4. The system doesn't stop after one pass — it improves each cycle.

```
Meta-Planner
    ↓
Task Planner
    ↓
Agent Spawner
    ↓
Agents Execute
    ↓
Evaluator (Memory)
    ↓
Assessment
    ↓
Self-Refactor Suggestions
    ↓
Back to Meta-Planner
```

### What makes this powerful

- **Iterative intelligence** — improves each cycle rather than stopping after one pass
- **Strategy evolution** — adjusts approach dynamically based on what worked
- **Memory-driven decisions** — learns from past executions stored in Neo4j and Vector DB
- **Safety layer** — only suggests changes; no uncontrolled self-modification

---

## 4. Infrastructure Layer

### Compute Nodes

| Node | Role |
|---|---|
| Mac Mini | Primary orchestration + API hosting |
| Jetson Nano | Edge inference + lightweight agent execution |

This is an edge + local compute hybrid setup designed for scalable node-based execution.

---

## 5. Module Map (Code → Architecture)

Each architectural component maps to a code module:

| Architecture Component | Code Module |
|---|---|
| Meta-Planner | `openclaw/planner/meta_planner.py` |
| Task Planner | `openclaw/planner/task_planner.py` (LangGraph) |
| Agent Spawner | `openclaw/agents/spawner.py` |
| Parallel Executors | `openclaw/agents/executor.py` |
| Evaluator | `openclaw/memory/evaluator.py` |
| Neo4j Store | `openclaw/memory/graph_store.py` |
| Vector Store | `openclaw/memory/vector_store.py` |
| Self-Refactor Engine | `openclaw/engine/refactor.py` |
| Control Dashboard | `openclaw/dashboard/` |

---

## 6. Next Evolution (v5 Targets)

These are the planned upgrades beyond v4:

- **Identity tracking per agent** — reputation scores per agent role
- **Cross-task learning** — transfer knowledge between unrelated workflows
- **Autonomous proposal execution** — apply self-refactor suggestions with guardrails
- **Dynamic agent specialization** — agents evolve and refine their own roles over time

---

## Key Insight

> v4 is not just "agents that complete tasks."
> It is a system that **learns how to complete tasks better over time.**

This architecture is a closed feedback loop where every execution makes the next one smarter.
