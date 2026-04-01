#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${OPENCLAW_BASE_URL:-http://localhost:8080}"
PASS=0
FAIL=0

ok()   { echo "✓  $1"; PASS=$((PASS+1)); }
fail() { echo "✗  $1"; FAIL=$((FAIL+1)); }

echo "╔══════════════════════════════════╗"
echo "║      OpenClaw CLI Test Suite     ║"
echo "╚══════════════════════════════════╝"
echo "  Base URL: $BASE_URL"
echo

# ---- Dependency checks ----
echo "── Dependency Checks ──"
python3 -c "import flask"    && ok "flask" || fail "flask not installed"
python3 -c "import requests" && ok "requests" || fail "requests not installed"
python3 -c "import click"    && ok "click" || fail "click not installed"

# ---- API connectivity ----
echo
echo "── API Connectivity ──"
if curl -sf "$BASE_URL/api/health" > /dev/null 2>&1; then
    ok "GET /api/health"
else
    fail "GET /api/health (is the server running?)"
fi

if curl -sf "$BASE_URL/api/status" > /dev/null 2>&1; then
    ok "GET /api/status"
else
    fail "GET /api/status"
fi

# ---- CLI commands ----
echo
echo "── CLI Commands ──"
cd "$REPO_ROOT"

python3 cli.py --help > /dev/null 2>&1 && ok "cli.py --help" || fail "cli.py --help"
python3 cli.py config > /dev/null 2>&1 && ok "openclaw config" || fail "openclaw config"
python3 cli.py status > /dev/null 2>&1 && ok "openclaw status" || fail "openclaw status"
python3 cli.py agents list > /dev/null 2>&1 && ok "openclaw agents list" || fail "openclaw agents list"
python3 cli.py tasks list > /dev/null 2>&1 && ok "openclaw tasks list" || fail "openclaw tasks list"
python3 cli.py --output json agents list > /dev/null 2>&1 && ok "openclaw --output json agents list" || fail "JSON output"
python3 cli.py --output yaml agents list > /dev/null 2>&1 && ok "openclaw --output yaml agents list" || fail "YAML output"

# ---- Summary ----
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PASSED: $PASS   FAILED: $FAIL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
