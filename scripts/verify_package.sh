#!/usr/bin/env bash
# Verify the built Python package (sdist/wheel) before publishing.
set -euo pipefail

echo "==> Installing twine for package checks"
pip install --quiet --upgrade twine

echo "==> Checking dist/ packages"
twine check dist/*

echo "==> Package verification passed"
