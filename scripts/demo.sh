#!/bin/bash
# ML Observability Platform - Demo Script
# Updated for Docker on Windows + Linux/WSL2
# Original: Podman on Mac | Modified: Docker on Windows

set -e

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() { echo -e "\n${GREEN}[STEP]${NC} $1"; }
print_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_success() { echo -e "${BLUE}[SUCCESS]${NC} $1"; }

# Error handler
error_exit() {
    print_error "$1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "mac"
    else
        echo "linux"
    fi
}

OS=$(detect_os)
print_info "Detected OS: $OS"

# Validate prerequisites
print_step "Validating prerequisites..."

# Check for Docker (not podman-compose)
command_exists docker || error_exit "Docker not found. Please install Docker Desktop."
command_exists python3 || error_exit "python3 not found. Please install it first."
command_exists curl || error_exit "curl not found. Please install it first."

print_success "All prerequisites satisfied"

# 1. Start system
print_step "Starting ML Observability Platform with Docker..."
cd infra

print_info "Stopping any existing containers..."
docker compose down 2>/dev/null || true

print_info "Building images..."
docker compose build --quiet 2>/dev/null || true

print_info "Starting services (docker compose up -d)..."
docker compose up -d

cd ..
print_success "Services started"

# 2. Wait for services to initialize
print_step "Waiting for services to initialize (45 seconds)..."
sleep 45

# 3. Check service health
print_step "Checking service health..."

# Check Redis
print_info "Checking Redis..."
if docker exec ml-obs-redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is healthy"
else
    error_exit "Redis is not responding"
fi

# Check PostgreSQL
print_info "Checking PostgreSQL..."
if docker exec ml-obs-postgres pg_isready -U mlobs -d ml_observability > /dev/null 2>&1; then
    print_success "PostgreSQL is healthy"
else
    error_exit "PostgreSQL is not responding"
fi

# Check Prometheus
print_info "Checking Prometheus..."
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_success "Prometheus is healthy"
else
    error_exit "Prometheus is not responding"
fi

# Check Grafana
print_info "Checking Grafana..."
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    print_success "Grafana is healthy"
else
    error_exit "Grafana is not responding"
fi

# Check Inference API (port 8001)
print_info "Checking Inference API..."
for i in {1..10}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Inference API is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        error_exit "Inference API is not responding after 10 attempts"
    fi
    sleep 3
done

# Check Drift Service (port 8000)
print_info "Checking Drift Service..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Drift Service is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        error_exit "Drift Service is not responding after 10 attempts"
    fi
    sleep 3
done

# Check Replay Service (port 8002)
print_info "Checking Replay Service..."
for i in {1..10}; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        print_success "Replay Service is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        error_exit "Replay Service is not responding after 10 attempts"
    fi
    sleep 3
done

# Check Webhook Receiver (port 5000)
print_info "Checking Webhook Receiver..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    print_success "Webhook Receiver is healthy"
else
    error_exit "Webhook Receiver is not responding"
fi

print_success "All services are healthy"

# 4. Monitor data generation in normal mode
print_step "Monitoring data pipeline in normal mode..."
print_info "The data-generator service is running continuously in Docker"
print_info "Collecting baseline metrics for 60 seconds..."

# Monitor metrics every 10 seconds
for i in {1..6}; do
    REDIS_COUNT=$(docker exec ml-obs-redis redis-cli XLEN ml-events 2>/dev/null || echo "0")
    PG_COUNT=$(docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2>/dev/null | tr -d ' ' || echo "0")

    echo -e "\n${YELLOW}[BASELINE - ${i}0s]${NC}"
    echo "  Redis stream events: $REDIS_COUNT"
    echo "  PostgreSQL stored:   $PG_COUNT"

    if [ $i -lt 6 ]; then
        sleep 10
    fi
done

print_success "Baseline metrics collected"

# 5. Check current inference metrics
print_step "Checking current inference metrics..."
print_info "Testing inference API prediction..."

PRED_RESPONSE=$(curl -s -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}')

echo -e "\n${BLUE}Prediction Response:${NC}"
echo "$PRED_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PRED_RESPONSE"

# 6. Enable drift mode
print_step "Enabling drift mode..."
print_info "Setting ENABLE_DRIFT=true in data-generator..."

# Create temporary docker-compose override file with drift enabled
DRIFT_COMPOSE="infra/docker-compose.drift.yml"
cat > "$DRIFT_COMPOSE" << 'DRIFT_EOF'
version: '3.8'
services:
  data-generator:
    environment:
      ENABLE_DRIFT: "true"
DRIFT_EOF

print_info "Restarting data-generator with drift enabled..."
docker compose -f infra/docker-compose.yml -f "$DRIFT_COMPOSE" up -d data-generator

print_success "Drift mode enabled"

# 7. Monitor drift detection
print_step "Monitoring drift detection (90 seconds)..."
print_info "Watching metrics for drift signals..."

for i in {1..9}; do
    REDIS_COUNT=$(docker exec ml-obs-redis redis-cli XLEN ml-events 2>/dev/null || echo "0")
    PG_COUNT=$(docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2>/dev/null | tr -d ' ' || echo "0")
    DRIFT_METRICS=$(curl -s http://localhost:8000/metrics | grep -E "drift_detected_total|ml_drift_score" | head -5 || echo "No drift detected yet")

    echo -e "\n${YELLOW}[DRIFT DETECTION - ${i}0s]${NC}"
    echo "  Redis stream events: $REDIS_COUNT"
    echo "  PostgreSQL stored:   $PG_COUNT"
    echo "  Drift metrics:"
    echo "$DRIFT_METRICS" | sed 's/^/    /'

    if [ $i -lt 9 ]; then
        sleep 10
    fi
done

print_success "Drift detection period complete"

# 8. Disable drift mode and restore normal operation
print_step "Restoring normal mode..."
print_info "Removing drift override configuration..."

rm -f "$DRIFT_COMPOSE"
docker compose -f infra/docker-compose.yml up -d data-generator

print_success "Normal mode restored"

# 9. Call replay API
print_step "Calling replay service to compare predictions..."
print_info "Replaying last 10 predictions..."

REPLAY_RESPONSE=$(curl -s -X POST "http://localhost:8002/replay?limit=10")

echo -e "\n${BLUE}Replay Results:${NC}"
echo "$REPLAY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REPLAY_RESPONSE"

# 10. Check alerts in webhook
print_step "Checking alerts received..."
print_info "Viewing webhook-receiver logs..."

WEBHOOK_LOGS=$(docker logs ml-obs-webhook-receiver 2>&1 | grep -i "alert\|drift" | tail -5 || echo "No alerts logged yet")

if [ ! -z "$WEBHOOK_LOGS" ]; then
    echo -e "\n${BLUE}Recent Alerts:${NC}"
    echo "$WEBHOOK_LOGS"
else
    echo "No alerts received yet (alerts require drift threshold to be exceeded)"
fi

# 11. Print summary
print_step "Demo complete! 🎉"

echo -e "\n${GREEN}═════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    DEMO SUMMARY                           ${NC}"
echo -e "${GREEN}═════════════════════════════════════════════════════════════${NC}"

echo -e "\n${BLUE}Services Running:${NC}"
echo "  • Prometheus:         http://localhost:9090"
echo "  • Grafana:            http://localhost:3000 (admin/admin)"
echo "  • Inference API:      http://localhost:8001"
echo "  • Drift Service:      http://localhost:8000"
echo "  • Replay Service:     http://localhost:8002"
echo "  • Webhook Receiver:   http://localhost:5000"
echo "  • Alertmanager:       http://localhost:9093"

echo -e "\n${BLUE}What Happened:${NC}"
echo "  1. ✓ Started all services with docker compose"
echo "  2. ✓ Verified service health"
echo "  3. ✓ Monitored baseline traffic from data-generator"
echo "  4. ✓ Enabled drift mode in data-generator"
echo "  5. ✓ Drift detection system analyzed distribution shift"
echo "  6. ✓ Replay service compared predictions"
echo "  7. ✓ Webhook receiver monitored for alerts"

FINAL_REDIS=$(docker exec ml-obs-redis redis-cli XLEN ml-events 2>/dev/null || echo "0")
FINAL_PG=$(docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2>/dev/null | tr -d ' ' || echo "0")

echo -e "\n${BLUE}Final Metrics:${NC}"
echo "  • Total events generated: $FINAL_REDIS"
echo "  • Events persisted:       $FINAL_PG"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "  • View dashboards in Grafana: http://localhost:3000"
echo "  • Check Prometheus metrics: http://localhost:9090"
echo "  • Review alerts in Alertmanager: http://localhost:9093"
echo "  • Query drift metrics: curl http://localhost:8000/metrics | grep drift_"
echo "  • Test replay API: curl -X POST http://localhost:8002/replay?limit=5"
echo "  • View logs: docker compose logs -f <service>"

echo -e "\n${YELLOW}To stop the system:${NC}"
echo "  cd infra && docker compose down"

echo -e "\n${YELLOW}To clean up everything (remove volumes):${NC}"
echo "  cd infra && docker compose down -v"

echo -e "\n${GREEN}═════════════════════════════════════════════════════════════${NC}\n"

print_success "Demo script completed successfully!"
