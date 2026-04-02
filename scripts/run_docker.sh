#!/usr/bin/env bash
# Run the OpenClaw Docker container.
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-open-claw}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
HOST_PORT="${HOST_PORT:-8080}"
CONTAINER_PORT="${CONTAINER_PORT:-8080}"

echo "==> Starting ${IMAGE_NAME}:${IMAGE_TAG} on port ${HOST_PORT}"
docker run --rm \
    -p "${HOST_PORT}:${CONTAINER_PORT}" \
    -e SECRET_KEY="${SECRET_KEY:-change-me}" \
    -e MONGO_URI="${MONGO_URI:-}" \
    "${IMAGE_NAME}:${IMAGE_TAG}"
