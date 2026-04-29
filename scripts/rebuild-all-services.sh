#!/usr/bin/env bash
set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source the runtime detection script
source "$SCRIPT_DIR/runtime.sh"

echo "=========================================="
echo "Rebuilding all services"
echo "Container Runtime: $CONTAINER_RUNTIME"
echo "Compose Command: $COMPOSE_CMD"
echo "Compose File: $COMPOSE_FILE"
echo "=========================================="

# Change to infra directory where compose files are located
cd "$PROJECT_ROOT/infra"

# Stop all services
echo ""
echo "Stopping all services..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" down; then
    echo "Warning: Failed to stop services (may not be running)"
fi

# Remove all containers and volumes
echo ""
echo "Removing containers and volumes..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" down -v; then
    echo "Warning: Failed to remove volumes"
fi

# Rebuild all services
echo ""
echo "Rebuilding all services (this may take a few minutes)..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" build --no-cache; then
    echo "Error: Failed to rebuild services"
    exit 1
fi

# Start all services
echo ""
echo "Starting all services..."
if ! $COMPOSE_CMD -f "$COMPOSE_FILE" up -d; then
    echo "Error: Failed to start services"
    exit 1
fi

# Wait for services to initialize
echo ""
echo "Waiting for services to initialize..."
sleep 5

# Show status of all services
echo ""
echo "=========================================="
echo "Service status:"
echo "=========================================="
$COMPOSE_CMD -f "$COMPOSE_FILE" ps

# Show brief logs from each service
echo ""
echo "=========================================="
echo "Recent logs from all services:"
echo "=========================================="
$COMPOSE_CMD -f "$COMPOSE_FILE" logs --tail=10

# Check health of key services
echo ""
echo "=========================================="
echo "Health checks:"
echo "=========================================="

# Check Prometheus
echo -n "Prometheus: "
if curl -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
    echo "✓ Healthy"
else
    echo "✗ Not responding"
fi

# Check Grafana
echo -n "Grafana: "
if curl -s http://localhost:3000/api/health >/dev/null 2>&1; then
    echo "✓ Healthy"
else
    echo "✗ Not responding"
fi

# Check Inference API
echo -n "Inference API: "
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✓ Healthy"
else
    echo "✗ Not responding"
fi

# Check Drift Service
echo -n "Drift Service: "
if curl -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "✓ Healthy"
else
    echo "✗ Not responding"
fi

echo ""
echo "=========================================="
echo "✓ All services rebuild complete!"
echo "=========================================="
echo ""
echo "Access points:"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Inference API: http://localhost:8000"
echo "  - Drift Service: http://localhost:8001"
echo "  - AlertManager: http://localhost:9093"
echo ""
echo "To view logs: $COMPOSE_CMD -f $COMPOSE_FILE logs -f [service-name]"
echo "To stop all: $COMPOSE_CMD -f $COMPOSE_FILE down"
echo "=========================================="

# Made with Bob
