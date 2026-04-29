#!/bin/bash
# Docker ML Observability Platform - Startup & Validation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/infra"

echo "════════════════════════════════════════════════════════════════"
echo "ML Observability Platform - Docker Startup Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✅ Docker version: $(docker --version)"
echo "✅ Docker Compose version: $(docker compose version)"
echo ""

# Navigate to infra directory
cd "$INFRA_DIR"

# Build images
echo "🔨 Building Docker images..."
docker compose build --progress=plain 2>&1 | tail -20
echo ""

# Start services
echo "🚀 Starting services..."
docker compose up -d
echo ""

# Wait for services to start
echo "⏳ Waiting for services to become healthy (60s)..."
sleep 60

# Check status
echo ""
echo "📊 Service Status:"
docker compose ps
echo ""

# Validation checks
echo "🔍 Running validation checks..."
echo ""

# Redis
echo -n "Redis connectivity... "
if docker exec ml-obs-redis redis-cli ping &> /dev/null; then
    REDIS_EVENTS=$(docker exec ml-obs-redis redis-cli XLEN ml-events 2>/dev/null || echo "0")
    echo "✅ ($REDIS_EVENTS events)"
else
    echo "❌ FAILED"
fi

# PostgreSQL
echo -n "PostgreSQL connectivity... "
if docker exec ml-obs-postgres pg_isready -U mlobs -d ml_observability &> /dev/null; then
    PG_COUNT=$(docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2>/dev/null || echo "0")
    echo "✅ ($PG_COUNT events)"
else
    echo "❌ FAILED"
fi

# Prometheus
echo -n "Prometheus metrics... "
if curl -s http://localhost:9090/api/v1/query?query=up &> /dev/null; then
    echo "✅"
else
    echo "❌ FAILED"
fi

# Inference API
echo -n "Inference API... "
HEALTH=$(curl -s http://localhost:8001/health | grep -q "healthy" && echo "✅" || echo "❌")
echo "$HEALTH"

# Drift Service
echo -n "Drift Service metrics... "
METRICS=$(curl -s http://localhost:8000/metrics | grep -q "drift_events_processed_total" && echo "✅" || echo "❌")
echo "$METRICS"

# Webhook Receiver
echo -n "Webhook Receiver... "
WEBHOOK=$(curl -s http://localhost:5000/health | grep -q "healthy" && echo "✅" || echo "❌")
echo "$WEBHOOK"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🎉 ML Observability Platform is ready!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📍 Access Points:"
echo "   • Grafana Dashboard:  http://localhost:3000 (admin/admin)"
echo "   • Prometheus:         http://localhost:9090"
echo "   • Alertmanager:       http://localhost:9093"
echo "   • Inference API:      http://localhost:8001"
echo "   • Drift Service:      http://localhost:8000"
echo "   • Replay Service:     http://localhost:8002"
echo "   • Webhook Receiver:   http://localhost:5000"
echo ""
echo "📝 Commands:"
echo "   • View logs:          docker compose logs -f <service>"
echo "   • Stop services:      docker compose down"
echo "   • Full cleanup:       docker compose down -v"
echo ""
