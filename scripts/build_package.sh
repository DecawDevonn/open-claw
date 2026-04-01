#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "╔══════════════════════════════════╗"
echo "║    OpenClaw Package Builder      ║"
echo "╚══════════════════════════════════╝"
echo

# ---- Run tests ----
echo "── Running Tests ──"
python3 -m pytest tests/ -v --tb=short
echo

# ---- Lint ----
echo "── Linting ──"
python3 -m flake8 app.py cli.py openclaw_client.py config.py formatters.py \
    --max-line-length=120 --ignore=E501 || echo "⚠️  Lint warnings present"
echo

# ---- Build wheel ----
echo "── Building Wheel ──"
pip install build --quiet
python3 -m build --wheel --outdir dist/
echo

echo "── Build Artifacts ──"
ls -lh dist/*.whl 2>/dev/null || echo "No wheel found"
echo

echo "✓  Build complete"
echo "  Install locally: pip install dist/*.whl"
echo "  Upload to PyPI:  twine upload dist/*"
