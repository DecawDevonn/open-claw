#!/usr/bin/env bash
# Verify that OpenClaw is installed correctly and the server responds.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "==> Checking Python import"
python3 -c "import openclaw; print('openclaw', openclaw.__version__)"

echo "==> Checking health endpoint at ${BASE_URL}/api/health"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/health")

if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo "==> Health check passed (HTTP ${HTTP_STATUS})"
else
    echo "ERROR: Health check failed (HTTP ${HTTP_STATUS})" >&2
    exit 1
fi

echo "==> All checks passed"
