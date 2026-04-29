#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source the runtime detection script
source "$SCRIPT_DIR/runtime.sh"

echo "=========================================="
echo "Rebuilding inference-api service"
echo "Container Runtime: $CONTAINER_RUNTIME"
echo "Compose Command: $COMPOSE_CMD"
echo "Compose File: $COMPOSE_FILE"
echo "=========================================="

# Change to infra directory where compose files are located
cd "$PROJECT_ROOT/infra"

# Stop the inference-api service
echo ""
echo "Stopping inference-api service..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" stop inference-api; then
    echo "Warning: Failed to stop inference-api service (may not be running)"
fi

# Remove the existing container
echo ""
echo "Removing inference-api container..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" rm -f inference-api; then
    echo "Warning: Failed to remove inference-api container (may not exist)"
fi

# Rebuild the inference-api service
echo ""
echo "Rebuilding inference-api service..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache inference-api; then
    echo "Error: Failed to rebuild inference-api service"
    exit 1
fi

# Start the inference-api service
echo ""
echo "Starting inference-api service..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" up -d inference-api; then
    echo "Error: Failed to start inference-api service"
    exit 1
fi

# Wait a moment for the service to initialize
echo ""
echo "Waiting for service to initialize..."
sleep 3

# Show logs to confirm it's running
echo ""
echo "=========================================="
echo "Service logs (last 20 lines):"
echo "=========================================="
$COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=20 inference-api

# Check service status
echo ""
echo "=========================================="
echo "Service status:"
echo "=========================================="
$COMPOSE_CMD -f "$COMPOSE_FILE" ps inference-api

echo ""
echo "=========================================="
echo "✓ inference-api rebuild complete!"
echo "=========================================="

# Made with Bob
