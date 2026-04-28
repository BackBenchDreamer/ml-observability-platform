#!/bin/bash
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

# Validate prerequisites
print_step "Validating prerequisites..."
command_exists podman-compose || error_exit "podman-compose not found. Please install it first."
command_exists python3 || error_exit "python3 not found. Please install it first."
command_exists curl || error_exit "curl not found. Please install it first."
print_success "All prerequisites satisfied"

# 1. Start system
print_step "Starting ML Observability Platform..."
cd infra
podman-compose down 2>/dev/null || true
podman-compose up -d
cd ..
print_success "Services started"

# 2. Wait for services to initialize
print_step "Waiting for services to initialize (30 seconds)..."
sleep 30

# 3. Check service health
print_step "Checking service health..."

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

# Check Inference API
print_info "Checking Inference API..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Inference API is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        error_exit "Inference API is not responding after 10 attempts"
    fi
    sleep 3
done

# Check Drift Service
print_info "Checking Drift Service..."
for i in {1..10}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Drift Service is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        error_exit "Drift Service is not responding after 10 attempts"
    fi
    sleep 3
done

# Check Replay Service
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

print_success "All services are healthy"

# 4. Start data generator in normal mode
print_step "Starting data generator in normal mode..."
print_info "Generating baseline traffic for 60 seconds..."

# Create a temporary Python script to run the generator
cat > /tmp/run_generator.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'data-generator'))
from generator import DataGenerator
import time

generator = DataGenerator(
    inference_url="http://localhost:8000/predict",
    rate_per_second=5,
    enable_drift=False
)

print("Starting data generator in normal mode...")
generator.start()

# Run for 60 seconds
time.sleep(60)

generator.stop()
print("Data generator stopped")
EOF

python3 /tmp/run_generator.py &
GENERATOR_PID=$!

# 5. Wait for baseline metrics to stabilize
print_step "Collecting baseline metrics (60 seconds)..."
sleep 60

# Kill the generator
kill $GENERATOR_PID 2>/dev/null || true
wait $GENERATOR_PID 2>/dev/null || true

print_success "Baseline metrics collected"

# Check current metrics
print_info "Current drift metrics:"
curl -s http://localhost:8001/metrics | grep "drift_detected" || true

# 6. Enable drift mode
print_step "Enabling drift mode in data generator..."
print_info "This will introduce distribution shift in the data..."

# Create a temporary Python script to run the generator with drift
cat > /tmp/run_generator_drift.py << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'data-generator'))
from generator import DataGenerator
import time

generator = DataGenerator(
    inference_url="http://localhost:8000/predict",
    rate_per_second=5,
    enable_drift=True
)

print("Starting data generator with DRIFT enabled...")
generator.start()

# Run for 90 seconds to allow drift detection
time.sleep(90)

generator.stop()
print("Data generator stopped")
EOF

python3 /tmp/run_generator_drift.py &
DRIFT_GENERATOR_PID=$!

# 7. Wait for drift detection and alert
print_step "Waiting for drift detection and alert (90 seconds)..."
print_info "Monitoring drift metrics..."

# Monitor drift metrics every 10 seconds
for i in {1..9}; do
    sleep 10
    echo -e "\n${YELLOW}[METRICS - ${i}0s]${NC}"
    curl -s http://localhost:8001/metrics | grep -E "(drift_detected|drift_score|prediction_distribution)" | head -10 || true
done

# Kill the drift generator
kill $DRIFT_GENERATOR_PID 2>/dev/null || true
wait $DRIFT_GENERATOR_PID 2>/dev/null || true

print_success "Drift detection period complete"

# Check if drift was detected
print_info "Final drift status:"
DRIFT_STATUS=$(curl -s http://localhost:8001/metrics | grep "drift_detected" || echo "drift_detected 0")
echo "$DRIFT_STATUS"

# 8. Call replay API to compare predictions
print_step "Calling replay service to compare predictions..."
print_info "Replaying last 100 predictions..."

REPLAY_RESPONSE=$(curl -s -X POST http://localhost:8002/replay \
    -H "Content-Type: application/json" \
    -d '{
        "limit": 100,
        "comparison_mode": "statistical"
    }')

echo -e "\n${BLUE}Replay Results:${NC}"
echo "$REPLAY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REPLAY_RESPONSE"

# 9. Print summary and access information
print_step "Demo complete! 🎉"

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    DEMO SUMMARY                           ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"

echo -e "\n${BLUE}Services Running:${NC}"
echo "  • Prometheus:      http://localhost:9090"
echo "  • Grafana:         http://localhost:3000 (admin/admin)"
echo "  • Inference API:   http://localhost:8000"
echo "  • Drift Service:   http://localhost:8001"
echo "  • Replay Service:  http://localhost:8002"
echo "  • Alertmanager:    http://localhost:9093"

echo -e "\n${BLUE}What Happened:${NC}"
echo "  1. ✓ Started all services with podman-compose"
echo "  2. ✓ Verified service health"
echo "  3. ✓ Generated baseline traffic (60 seconds)"
echo "  4. ✓ Enabled drift mode and generated shifted data (90 seconds)"
echo "  5. ✓ Drift detection system analyzed the distribution shift"
echo "  6. ✓ Replay service compared predictions"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "  • View dashboards in Grafana: http://localhost:3000"
echo "  • Check Prometheus metrics: http://localhost:9090"
echo "  • Review alerts in Alertmanager: http://localhost:9093"
echo "  • Query drift metrics: curl http://localhost:8001/metrics"
echo "  • Test replay API: curl -X POST http://localhost:8002/replay -H 'Content-Type: application/json' -d '{\"limit\": 50}'"

echo -e "\n${YELLOW}To stop the system:${NC}"
echo "  cd infra && podman-compose down"

echo -e "\n${GREEN}═══════════════════════════════════════════════════════════${NC}\n"

# Cleanup temporary files
rm -f /tmp/run_generator.py /tmp/run_generator_drift.py

print_success "Demo script completed successfully!"

# Made with Bob
