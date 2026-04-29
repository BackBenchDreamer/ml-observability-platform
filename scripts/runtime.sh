#!/usr/bin/env bash
set -euo pipefail

if command -v podman-compose >/dev/null 2>&1; then
    export CONTAINER_RUNTIME="podman"
    export COMPOSE_CMD="podman-compose"
    export EXEC_CMD="podman"
elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    export CONTAINER_RUNTIME="docker"
    export COMPOSE_CMD="docker compose"
    export EXEC_CMD="docker"
elif command -v docker-compose >/dev/null 2>&1; then
    export CONTAINER_RUNTIME="docker"
    export COMPOSE_CMD="docker-compose"
    export EXEC_CMD="docker"
else
    echo "No container runtime found (Docker or Podman required)"
    exit 1
fi

if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    export COMPOSE_FILE="podman-compose.yml"
else
    export COMPOSE_FILE="docker-compose.yml"
fi
