#!/usr/bin/env bash
# Build the OpenClaw Docker image.
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-open-claw}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "==> Building Docker image ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo "==> Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
