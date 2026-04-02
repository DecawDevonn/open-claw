#!/usr/bin/env bash
# Build and publish the OpenClaw package to PyPI.
set -euo pipefail

if [[ -z "${PYPI_TOKEN:-}" ]]; then
    echo "ERROR: PYPI_TOKEN environment variable is not set." >&2
    exit 1
fi

echo "==> Cleaning previous builds"
rm -rf dist/ build/ *.egg-info

echo "==> Building distribution packages"
pip install --quiet --upgrade build
python -m build

echo "==> Uploading to PyPI"
pip install --quiet --upgrade twine
twine upload --username __token__ --password "${PYPI_TOKEN}" dist/*

echo "==> Published successfully"
