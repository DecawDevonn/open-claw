#!/usr/bin/env bash
# Verify that the Docker image builds and the health endpoint responds.
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-open-claw}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
TEST_PORT="${TEST_PORT:-18080}"

echo "==> Building image ${IMAGE_NAME}:${IMAGE_TAG}"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo "==> Starting container on port ${TEST_PORT}"
CONTAINER_ID=$(docker run -d -p "${TEST_PORT}:8080" "${IMAGE_NAME}:${IMAGE_TAG}")

cleanup() {
    echo "==> Stopping container ${CONTAINER_ID}"
    docker stop "${CONTAINER_ID}" >/dev/null
    docker rm "${CONTAINER_ID}" >/dev/null
}
trap cleanup EXIT

echo "==> Waiting for server to start..."
sleep 5

echo "==> Checking health endpoint"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${TEST_PORT}/api/health")

if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo "==> Docker verification passed (HTTP ${HTTP_STATUS})"
else
    echo "ERROR: Health check failed (HTTP ${HTTP_STATUS})" >&2
    exit 1
fi
