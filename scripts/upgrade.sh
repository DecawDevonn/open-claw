#!/usr/bin/env bash
# Upgrade OpenClaw to the latest version.
set -euo pipefail

echo "==> Upgrading OpenClaw"
pip install --upgrade open-claw

echo "==> Upgraded successfully"
python -c "import openclaw; print('Version:', openclaw.__version__)"
