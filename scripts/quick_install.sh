#!/usr/bin/env bash
# Quick install script: create venv and install OpenClaw.
set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"

echo "==> Checking Python version"
python3 --version

echo "==> Creating virtual environment at ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

echo "==> Activating virtual environment"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "==> Installing OpenClaw"
pip install --upgrade pip --quiet
pip install open-claw

echo ""
echo "==> Installation complete!"
echo "    Activate with: source ${VENV_DIR}/bin/activate"
echo "    Run with:      python app.py"
echo "    Health check:  curl http://localhost:8080/api/health"
