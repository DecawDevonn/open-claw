#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXAMPLES_DIR="$REPO_ROOT/examples"

echo "╔══════════════════════════════════╗"
echo "║    OpenClaw Examples Runner      ║"
echo "╚══════════════════════════════════╝"
echo

# Setup check
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ Dependencies not installed. Run: pip install -r requirements.txt"
    exit 1
fi

if ! curl -sf http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "⚠️  API server not reachable at http://localhost:8080"
    echo "   Start it with: python app.py"
    echo
fi

menu() {
    echo "Select an example to run:"
    echo "  1) simple_agent.py           - Single agent workflow"
    echo "  2) multi_agent_workflow.py   - Parallel multi-agent workflow"
    echo "  3) fortress_workflow.py      - Fortress engine integration"
    echo "  4) cicd_pipeline.py          - CI/CD pipeline simulation"
    echo "  5) interactive_demo.py       - Step-by-step interactive tutorial"
    echo "  6) Run all (non-interactive)"
    echo "  q) Quit"
    echo
    read -rp "Choice: " choice
    echo

    case "$choice" in
        1) python3 "$EXAMPLES_DIR/simple_agent.py" ;;
        2) python3 "$EXAMPLES_DIR/multi_agent_workflow.py" ;;
        3) python3 "$EXAMPLES_DIR/fortress_workflow.py" ;;
        4) python3 "$EXAMPLES_DIR/cicd_pipeline.py" ;;
        5) python3 "$EXAMPLES_DIR/interactive_demo.py" ;;
        6)
            for ex in simple_agent multi_agent_workflow fortress_workflow cicd_pipeline; do
                echo "━━━  $ex  ━━━"
                python3 "$EXAMPLES_DIR/$ex.py" || echo "⚠️  $ex exited with error"
                echo
            done
            ;;
        q|Q) echo "Bye!"; exit 0 ;;
        *) echo "Unknown choice"; menu ;;
    esac
}

menu
