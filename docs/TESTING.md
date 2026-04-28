# Testing Guide

## Overview

This guide provides comprehensive instructions for testing the ML Observability Platform's failure simulation and validation capabilities. It covers drift detection, alerting, replay functionality, and various failure scenarios.

**Purpose:**
- Validate drift detection mechanisms
- Test alerting pipeline end-to-end
- Verify replay functionality for prediction comparison
- Simulate and recover from service failures
- Monitor system health and debug issues

**Target Audience:**
- Developers testing new features
- QA engineers validating releases
- DevOps engineers troubleshooting production issues
- Data scientists validating drift detection accuracy

---

## Prerequisites

Before starting any tests, ensure the following:

### Required Software
```bash
# Verify podman and podman-compose
podman --version
podman-compose --version

# Verify Python 3
python3 --version

# Verify curl
curl --version
```

### System Requirements
- **Ports Available:** 3000, 5001, 6379, 8000, 8001, 8002, 9090, 9093, 5432
- **Memory:** At least 4GB available RAM
- **Disk Space:** At least 2GB free space

### Services Running
All services must be running before testing:
```bash
cd infra
podman-compose up -d
cd ..

# Wait 30 seconds for initialization
sleep 30

# Verify all services are healthy
curl -s http://localhost:8000/health  # Drift Service
curl -s http://localhost:8001/health  # Inference API
curl -s http://localhost:8002/health  # Replay Service
curl -s http://localhost:9090/-/healthy  # Prometheus
curl -s http://localhost:3000/api/health  # Grafana
```

---

## Testing Scenarios

### 1. Normal Operation Test

**Purpose:** Establish baseline behavior and verify all components work correctly.

**Steps:**

1. **Start the system:**
```bash
cd infra
podman-compose up -d
cd ..
sleep 30
```

2. **Generate normal traffic:**
```bash
# Using the data generator
cd data-generator
python3 generator.py &
GENERATOR_PID=$!
cd ..

# Let it run for 60 seconds
sleep 60

# Stop the generator
kill $GENERATOR_PID
```

3. **Verify metrics are being collected:**
```bash
# Check Prometheus metrics
curl -s http://localhost:8000/metrics | grep "ml_events_processed_total"
curl -s http://localhost:8000/metrics | grep "ml_drift_score"
curl -s http://localhost:8000/metrics | grep "ml_predictions_total"
```

4. **Check Grafana dashboards:**
- Open http://localhost:3000 (admin/admin)
- Navigate to "Drift Detection Dashboard"
- Verify panels show data
- Check that drift score is low (< 0.1)

**Expected Results:**
- ✓ All services respond to health checks
- ✓ Events are processed (ml_events_processed_total increases)
- ✓ Drift score remains low (< 0.1)
- ✓ Grafana dashboards display metrics
- ✓ No alerts firing in Alertmanager

---

### 2. Drift Detection Test

**Purpose:** Verify the system can detect distribution shifts in incoming data.

#### Method A: Manual Drift Triggering

**Steps:**

1. **Modify data generator parameters:**
```bash
# Edit data-generator/generator.py or set environment variable
export ENABLE_DRIFT=true

# Start generator with drift enabled
cd data-generator
python3 -c "
import sys
sys.path.insert(0, '.')
from generator import DataGenerator
import time

generator = DataGenerator(
    inference_url='http://localhost:8001/predict',
    rate_per_second=5,
    enable_drift=True
)

print('Starting data generator with DRIFT enabled...')
generator.start()
time.sleep(90)
generator.stop()
print('Generator stopped')
"
cd ..
```

2. **Monitor drift metrics in real-time:**
```bash
# Watch drift score every 10 seconds
watch -n 10 'curl -s http://localhost:8000/metrics | grep "ml_drift_score"'
```

3. **Check drift detection logs:**
```bash
podman logs drift-service | grep -i "drift"
```

**Expected Results:**
- ✓ Drift score increases above 0.2 within 60-90 seconds
- ✓ Drift service logs show "Drift detected" messages
- ✓ Feature-level drift scores increase
- ✓ Baseline vs current distribution diverges

#### Method B: Automated Testing with Demo Script

**Steps:**

1. **Run the automated demo:**
```bash
bash scripts/demo.sh
```

2. **Observe the output:**
The script will:
- Start all services
- Generate baseline traffic (60s)
- Enable drift mode (90s)
- Display metrics progression
- Call replay API
- Show summary

**Expected Results:**
- ✓ Script completes without errors
- ✓ Drift detected message appears
- ✓ Replay comparison shows prediction differences
- ✓ All services remain healthy

**Timeline:**
- 0-30s: Service initialization
- 30-90s: Baseline collection
- 90-180s: Drift detection period
- 180s+: Verification and replay

---

### 3. Alert Verification Test

**Purpose:** Validate that alerts fire correctly when drift is detected.

**Steps:**

1. **Trigger drift** (use Method A or B from previous section)

2. **Check Prometheus alerts page:**
```bash
# Open in browser
open http://localhost:9090/alerts

# Or check via API
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool
```

3. **Check Alertmanager UI:**
```bash
# Open in browser
open http://localhost:9093

# Or check via API
curl -s http://localhost:9093/api/v2/alerts | python3 -m json.tool
```

4. **Verify webhook receiver logs:**
```bash
# Check if alerts were received
podman logs webhook-receiver

# Look for alert payloads
podman logs webhook-receiver | grep -A 20 "Alert received"
```

5. **Inspect alert payload:**
```bash
# The webhook receiver logs should show:
# - alertname: HighDriftScore
# - severity: warning
# - drift score value
# - timestamp
```

**Expected Alert Payload:**
```json
{
  "alerts": [
    {
      "labels": {
        "alertname": "HighDriftScore",
        "severity": "warning"
      },
      "annotations": {
        "summary": "ML model drift detected",
        "description": "Drift score is 0.25 (threshold: 0.2)"
      },
      "status": "firing",
      "startsAt": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

**Expected Results:**
- ✓ Alert appears in Prometheus (pending → firing)
- ✓ Alert forwarded to Alertmanager
- ✓ Webhook receiver logs show alert received
- ✓ Alert contains correct labels and annotations
- ✓ Alert fires within 2 minutes of drift detection

**Troubleshooting:**
If alerts don't fire:
```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool

# Check alert rules
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool

# Verify drift score exceeds threshold
curl -s http://localhost:8000/metrics | grep "ml_drift_score"
```

---

### 4. Replay Validation Test

**Purpose:** Test the replay service's ability to compare predictions across time.

**Steps:**

1. **Ensure events are in the database:**
```bash
# Generate some predictions first
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'

# Repeat a few times or use data generator
```

2. **Call replay API with default parameters:**
```bash
curl -X POST http://localhost:8002/replay \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "comparison_mode": "statistical"}' | python3 -m json.tool
```

3. **Call replay API with specific limit:**
```bash
curl -X POST "http://localhost:8002/replay?limit=50" | python3 -m json.tool
```

4. **Interpret the response:**
```json
{
  "replayed_count": 10,
  "comparisons": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "old_prediction": {
        "label": 1,
        "confidence": 0.85
      },
      "new_prediction": {
        "label": 1,
        "confidence": 0.87
      },
      "confidence_diff": 0.02,
      "label_match": true
    }
  ],
  "statistics": {
    "total_replayed": 10,
    "label_matches": 9,
    "label_mismatches": 1,
    "avg_confidence_diff": 0.015,
    "max_confidence_diff": 0.05
  }
}
```

5. **Verify prediction differences:**
- Check `label_match` field (should be mostly true for stable models)
- Check `confidence_diff` (small values indicate stable predictions)
- Review `statistics` for overall comparison metrics

6. **Check database for stored events:**
```bash
# Connect to PostgreSQL
podman exec -it postgres psql -U mluser -d mldb

# Query events table
SELECT request_id, model_version, prediction_label, prediction_confidence, created_at 
FROM events 
ORDER BY created_at DESC 
LIMIT 10;

# Exit
\q
```

**Expected Results:**
- ✓ Replay API returns comparison results
- ✓ `replayed_count` matches requested limit
- ✓ Predictions are consistent (high label_match rate)
- ✓ Confidence differences are small (< 0.1)
- ✓ Events exist in PostgreSQL database
- ✓ Statistics provide meaningful insights

**Validation Criteria:**
- **Stable Model:** label_match > 95%, avg_confidence_diff < 0.05
- **Model Drift:** label_match < 90%, avg_confidence_diff > 0.1
- **Model Update:** Systematic confidence changes, label_match varies

---

### 5. Service Failure Scenarios

**Purpose:** Test system resilience and recovery from component failures.

#### Scenario A: Redis Failure

**Steps:**

1. **Stop Redis:**
```bash
podman stop redis
```

2. **Observe behavior:**
```bash
# Inference API should log connection errors
podman logs inference-api | tail -20

# Drift service should log consumer errors
podman logs drift-service | tail -20
```

3. **Restart Redis:**
```bash
podman start redis
sleep 10
```

4. **Verify recovery:**
```bash
# Services should reconnect automatically
curl http://localhost:8001/health
curl http://localhost:8000/health
```

**Expected Results:**
- ✓ Services log connection errors
- ✓ Health checks return degraded status
- ✓ Services automatically reconnect after Redis restart
- ✓ Event processing resumes
- ✓ No data loss (events buffered or retried)

#### Scenario B: PostgreSQL Failure

**Steps:**

1. **Stop PostgreSQL:**
```bash
podman stop postgres
```

2. **Test replay service:**
```bash
# Should return 503 Service Unavailable
curl -X POST http://localhost:8002/replay
```

3. **Restart PostgreSQL:**
```bash
podman start postgres
sleep 15
```

4. **Verify recovery:**
```bash
curl http://localhost:8002/health
curl -X POST "http://localhost:8002/replay?limit=5"
```

**Expected Results:**
- ✓ Replay service returns 503 error
- ✓ Health check shows database disconnected
- ✓ Service reconnects after PostgreSQL restart
- ✓ Historical data remains intact

#### Scenario C: Inference API Failure

**Steps:**

1. **Stop Inference API:**
```bash
podman stop inference-api
```

2. **Test data generator:**
```bash
# Should log connection errors
cd data-generator
python3 generator.py &
GENERATOR_PID=$!
sleep 10
kill $GENERATOR_PID
cd ..
```

3. **Test replay service:**
```bash
# Should return 502 Bad Gateway
curl -X POST "http://localhost:8002/replay?limit=5"
```

4. **Restart Inference API:**
```bash
podman start inference-api
sleep 10
```

5. **Verify recovery:**
```bash
curl http://localhost:8001/health
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2}'
```

**Expected Results:**
- ✓ Data generator logs connection failures
- ✓ Replay service returns 502 error
- ✓ Service restarts successfully
- ✓ Predictions resume normally

#### Scenario D: Drift Service Failure

**Steps:**

1. **Stop Drift Service:**
```bash
podman stop drift-service
```

2. **Generate events:**
```bash
# Events should still be published to Redis
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2}'
```

3. **Check Redis stream:**
```bash
podman exec -it redis redis-cli XLEN ml-events
```

4. **Restart Drift Service:**
```bash
podman start drift-service
sleep 10
```

5. **Verify catch-up:**
```bash
# Service should process backlog
podman logs drift-service | grep "Processing event"
curl http://localhost:8000/metrics | grep "ml_events_processed_total"
```

**Expected Results:**
- ✓ Events continue to be published
- ✓ Events accumulate in Redis stream
- ✓ Drift service processes backlog on restart
- ✓ No events lost
- ✓ Metrics resume updating

#### Scenario E: Prometheus Failure

**Steps:**

1. **Stop Prometheus:**
```bash
podman stop prometheus
```

2. **Verify services continue:**
```bash
# Services should continue operating
curl http://localhost:8000/metrics
curl http://localhost:8001/health
```

3. **Restart Prometheus:**
```bash
podman start prometheus
sleep 10
```

4. **Verify scraping resumes:**
```bash
# Check targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool
```

**Expected Results:**
- ✓ Services continue operating without Prometheus
- ✓ Metrics endpoints remain accessible
- ✓ Prometheus resumes scraping on restart
- ✓ Historical metrics preserved (within retention)

---

## Manual Testing

### Triggering Drift Manually

**Method 1: Environment Variable**

```bash
# Set drift mode
export ENABLE_DRIFT=true

# Run generator
cd data-generator
python3 generator.py
cd ..
```

**Method 2: Modify Generator Code**

Edit `data-generator/generator.py`:
```python
# Change line ~31
ENABLE_DRIFT = True  # Force drift mode

# Or modify drift parameters (lines 36-39)
DRIFT_MEAN = 10.0  # Increase for more dramatic drift
DRIFT_STD = 2.0
```

**Method 3: Direct API Calls with Shifted Data**

```bash
# Normal data (mean ~0)
for i in {1..50}; do
  curl -X POST http://localhost:8001/predict \
    -H "Content-Type: application/json" \
    -d "{\"feature_1\": $(python3 -c 'import random; print(random.gauss(0, 1))'), \"feature_2\": $(python3 -c 'import random; print(random.gauss(0, 1))'), \"feature_3\": $(python3 -c 'import random; print(random.gauss(0, 1))')}"
  sleep 0.2
done

# Wait for baseline
sleep 60

# Drifted data (mean ~5)
for i in {1..50}; do
  curl -X POST http://localhost:8001/predict \
    -H "Content-Type: application/json" \
    -d "{\"feature_1\": $(python3 -c 'import random; print(random.gauss(5, 1))'), \"feature_2\": $(python3 -c 'import random; print(random.gauss(5, 1))'), \"feature_3\": $(python3 -c 'import random; print(random.gauss(5, 1))')}"
  sleep 0.2
done
```

### Verifying Drift Detection

**Step 1: Check Drift Metrics**
```bash
# Current drift score
curl -s http://localhost:8000/metrics | grep "ml_drift_score"

# Drift detection count
curl -s http://localhost:8000/metrics | grep "ml_drift_detected_total"

# Feature-specific drift
curl -s http://localhost:8000/metrics | grep "feature_drift_score"
```

**Step 2: Check Drift Service Logs**
```bash
# View recent logs
podman logs drift-service --tail 50

# Follow logs in real-time
podman logs -f drift-service

# Search for drift events
podman logs drift-service | grep -i "drift detected"
```

**Step 3: Query Prometheus**
```bash
# Open Prometheus UI
open http://localhost:9090

# Run queries:
# - ml_drift_score
# - rate(ml_drift_detected_total[5m])
# - ml_baseline_samples
# - ml_sliding_window_samples
```

**Step 4: Check Grafana Dashboard**
- Navigate to http://localhost:3000
- Open "Drift Detection Dashboard"
- Look for:
  - Drift score spike
  - Feature distribution changes
  - Statistical test results
  - Alert annotations

### Validating Alerts

**Step 1: Check Prometheus Alerts**
```bash
# List all alerts
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool

# Check specific alert
curl -s http://localhost:9090/api/v1/alerts | python3 -c "
import sys, json
alerts = json.load(sys.stdin)
for alert in alerts.get('data', {}).get('alerts', []):
    if alert['labels'].get('alertname') == 'HighDriftScore':
        print(json.dumps(alert, indent=2))
"
```

**Step 2: Check Alertmanager**
```bash
# List active alerts
curl -s http://localhost:9093/api/v2/alerts | python3 -m json.tool

# Check alert status
curl -s http://localhost:9093/api/v2/alerts | python3 -c "
import sys, json
alerts = json.load(sys.stdin)
print(f'Total alerts: {len(alerts)}')
for alert in alerts:
    print(f\"Alert: {alert['labels']['alertname']}, Status: {alert['status']['state']}\")
"
```

**Step 3: Verify Webhook Delivery**
```bash
# Check webhook receiver logs
podman logs webhook-receiver | grep "Alert received"

# View full alert payload
podman logs webhook-receiver | grep -A 30 "Alert received"

# Count alerts received
podman logs webhook-receiver | grep -c "Alert received"
```

**Step 4: Test Manual Alert**
```bash
# Send test alert to webhook
curl -X POST http://localhost:5001/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {
        "alertname": "TestAlert",
        "severity": "info"
      },
      "annotations": {
        "summary": "Manual test alert",
        "description": "Testing webhook receiver"
      },
      "status": "firing",
      "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
    }]
  }'
```

---

## Automated Testing

### Using Demo Script

The `scripts/demo.sh` script provides automated end-to-end testing.

**Basic Usage:**
```bash
# Run full demo
bash scripts/demo.sh
```

**What the Script Does:**

1. **Validates Prerequisites**
   - Checks for podman-compose, python3, curl
   - Exits if dependencies missing

2. **Starts System**
   - Runs `podman-compose up -d`
   - Waits 30 seconds for initialization

3. **Health Checks**
   - Verifies all services respond
   - Retries with backoff for slow starts

4. **Baseline Generation**
   - Runs data generator in normal mode
   - Collects 60 seconds of baseline data

5. **Drift Simulation**
   - Enables drift mode
   - Generates 90 seconds of drifted data
   - Monitors metrics every 10 seconds

6. **Replay Testing**
   - Calls replay API
   - Compares predictions
   - Displays results

7. **Summary**
   - Shows service URLs
   - Lists what happened
   - Provides next steps

**Expected Output:**
```
[STEP] Validating prerequisites...
[SUCCESS] All prerequisites satisfied

[STEP] Starting ML Observability Platform...
[SUCCESS] Services started

[STEP] Waiting for services to initialize (30 seconds)...

[STEP] Checking service health...
[INFO] Checking Prometheus...
[SUCCESS] Prometheus is healthy
[INFO] Checking Grafana...
[SUCCESS] Grafana is healthy
...

[STEP] Starting data generator in normal mode...
[INFO] Generating baseline traffic for 60 seconds...

[STEP] Enabling drift mode in data generator...
[INFO] This will introduce distribution shift in the data...

[STEP] Waiting for drift detection and alert (90 seconds)...
[METRICS - 10s]
ml_drift_score 0.05
[METRICS - 20s]
ml_drift_score 0.12
[METRICS - 30s]
ml_drift_score 0.23
...

[STEP] Calling replay service to compare predictions...
Replay Results:
{
  "replayed_count": 100,
  "comparisons": [...],
  "statistics": {...}
}

[STEP] Demo complete! 🎉
```

**Customizing the Demo:**

Edit `scripts/demo.sh` to modify:
- Baseline duration (line 129)
- Drift duration (line 174)
- Event rate (lines 121, 166)
- Replay limit (line 211)

---

## Monitoring and Debugging

### Service Logs

**View All Service Logs:**
```bash
# List all containers
podman ps

# View specific service logs
podman logs inference-api
podman logs drift-service
podman logs replay-service
podman logs prometheus
podman logs grafana
podman logs alertmanager
podman logs webhook-receiver
podman logs redis
podman logs postgres
```

**Follow Logs in Real-Time:**
```bash
# Follow single service
podman logs -f drift-service

# Follow with timestamps
podman logs -f --timestamps drift-service

# Follow last N lines
podman logs -f --tail 50 drift-service
```

**Search Logs:**
```bash
# Search for errors
podman logs drift-service | grep -i error

# Search for drift events
podman logs drift-service | grep -i "drift detected"

# Search with context
podman logs drift-service | grep -B 5 -A 5 "error"
```

**Export Logs:**
```bash
# Save logs to file
podman logs drift-service > drift-service.log

# Save all service logs
for service in inference-api drift-service replay-service; do
  podman logs $service > ${service}.log
done
```

### Metrics Inspection

**Prometheus Queries:**

```bash
# Query current drift score
curl -s 'http://localhost:9090/api/v1/query?query=ml_drift_score' | python3 -m json.tool

# Query event processing rate
curl -s 'http://localhost:9090/api/v1/query?query=rate(ml_events_processed_total[1m])' | python3 -m json.tool

# Query prediction latency (P95)
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(ml_inference_latency_seconds_bucket[5m]))' | python3 -m json.tool

# Query drift detection count
curl -s 'http://localhost:9090/api/v1/query?query=ml_drift_detected_total' | python3 -m json.tool
```

**Range Queries:**
```bash
# Query drift score over last hour
curl -s 'http://localhost:9090/api/v1/query_range?query=ml_drift_score&start='$(date -u -d '1 hour ago' +%s)'&end='$(date -u +%s)'&step=60' | python3 -m json.tool
```

**Useful Prometheus Queries:**

| Metric | Query | Description |
|--------|-------|-------------|
| Drift Score | `ml_drift_score` | Current drift score (0-1) |
| Event Rate | `rate(ml_events_processed_total[1m])` | Events per second |
| Prediction Rate | `rate(ml_predictions_total[1m])` | Predictions per second |
| P95 Latency | `histogram_quantile(0.95, rate(ml_inference_latency_seconds_bucket[5m]))` | 95th percentile latency |
| Drift Alerts | `ml_drift_detected_total` | Total drift alerts |
| Baseline Size | `ml_baseline_samples` | Baseline sample count |
| Window Size | `ml_sliding_window_samples` | Current window size |

**Direct Metrics Access:**
```bash
# Get all metrics from drift service
curl -s http://localhost:8000/metrics

# Filter specific metrics
curl -s http://localhost:8000/metrics | grep "ml_drift"

# Get metrics with values only
curl -s http://localhost:8000/metrics | grep -v "^#"
```

### Redis Stream Inspection

**Connect to Redis:**
```bash
podman exec -it redis redis-cli
```

**Redis Commands:**
```redis
# Check stream length
XLEN ml-events

# View last 10 events
XREVRANGE ml-events + - COUNT 10

# View first 10 events
XRANGE ml-events - + COUNT 10

# Get stream info
XINFO STREAM ml-events

# Check consumer groups
XINFO GROUPS ml-events

# Check consumers in group
XINFO CONSUMERS ml-events drift-consumers

# View pending messages
XPENDING ml-events drift-consumers

# Exit
exit
```

**One-Liner Checks:**
```bash
# Check stream length
podman exec redis redis-cli XLEN ml-events

# View latest event
podman exec redis redis-cli XREVRANGE ml-events + - COUNT 1

# Check consumer group lag
podman exec redis redis-cli XINFO GROUPS ml-events
```

### PostgreSQL Database Queries

**Connect to Database:**
```bash
podman exec -it postgres psql -U mluser -d mldb
```

**Useful SQL Queries:**
```sql
-- Count total events
SELECT COUNT(*) FROM events;

-- View recent events
SELECT request_id, model_version, prediction_label, prediction_confidence, created_at 
FROM events 
ORDER BY created_at DESC 
LIMIT 10;

-- Count events by model version
SELECT model_version, COUNT(*) as count 
FROM events 
GROUP BY model_version;

-- View events from last hour
SELECT * FROM events 
WHERE created_at > NOW() - INTERVAL '1 hour' 
ORDER BY created_at DESC;

-- Calculate average confidence
SELECT AVG(prediction_confidence) as avg_confidence 
FROM events;

-- View prediction distribution
SELECT prediction_label, COUNT(*) as count 
FROM events 
GROUP BY prediction_label;

-- Check database size
SELECT pg_size_pretty(pg_database_size('mldb'));

-- Exit
\q
```

**One-Liner Queries:**
```bash
# Count events
podman exec postgres psql -U mluser -d mldb -c "SELECT COUNT(*) FROM events;"

# View latest events
podman exec postgres psql -U mluser -d mldb -c "SELECT * FROM events ORDER BY created_at DESC LIMIT 5;"

# Check table size
podman exec postgres psql -U mluser -d mldb -c "SELECT pg_size_pretty(pg_total_relation_size('events'));"
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Services Won't Start

**Symptoms:**
- `podman-compose up` fails
- Containers exit immediately
- Port binding errors

**Diagnosis:**
```bash
# Check container status
podman ps -a

# Check logs for failed container
podman logs <container-name>

# Check port availability
netstat -tuln | grep -E '(3000|5001|6379|8000|8001|8002|9090|9093|5432)'
```

**Solutions:**

1. **Port already in use:**
```bash
# Find process using port
lsof -i :8000

# Kill process or change port in podman-compose.yml
```

2. **Permission issues:**
```bash
# Check SELinux (if applicable)
getenforce

# Temporarily disable
sudo setenforce 0
```

3. **Resource constraints:**
```bash
# Check available memory
free -h

# Check disk space
df -h
```

#### Issue 2: No Metrics in Grafana

**Symptoms:**
- Dashboards show "No data"
- Panels are empty
- Data source shows errors

**Diagnosis:**
```bash
# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool

# Check if metrics exist
curl -s http://localhost:8000/metrics | grep "ml_drift_score"

# Check Grafana data source
curl -s http://admin:admin@localhost:3000/api/datasources
```

**Solutions:**

1. **Prometheus not scraping:**
```bash
# Check prometheus.yml configuration
cat infra/prometheus.yml

# Restart Prometheus
podman restart prometheus
```

2. **Drift service not exposing metrics:**
```bash
# Check drift service health
curl http://localhost:8000/health

# Check metrics endpoint
curl http://localhost:8000/metrics

# Restart drift service
podman restart drift-service
```

3. **Grafana data source misconfigured:**
- Open http://localhost:3000
- Go to Configuration → Data Sources
- Edit Prometheus data source
- Set URL to `http://prometheus:9090`
- Click "Save & Test"

#### Issue 3: Drift Not Detected

**Symptoms:**
- Drift score remains low despite shifted data
- No alerts firing
- Baseline not updating

**Diagnosis:**
```bash
# Check if events are being processed
curl -s http://localhost:8000/metrics | grep "ml_events_processed_total"

# Check baseline size
curl -s http://localhost:8000/metrics | grep "ml_baseline_samples"

# Check drift service logs
podman logs drift-service | grep -i "baseline\|drift"
```

**Solutions:**

1. **Insufficient baseline:**
```bash
# Wait for baseline collection (default: 100 samples)
# Check current baseline size
curl -s http://localhost:8000/metrics | grep "ml_baseline_samples"

# Generate more events
cd data-generator
python3 generator.py &
sleep 60
kill %1
cd ..
```

2. **Drift not significant enough:**
```bash
# Increase drift magnitude in generator
# Edit data-generator/generator.py
# Change DRIFT_MEAN from 5.0 to 10.0
```

3. **Threshold too high:**
```bash
# Check current threshold in drift-service/drift.py
# Default PSI threshold: 0.2
# Lower threshold for more sensitive detection
```

#### Issue 4: Alerts Not Firing

**Symptoms:**
- Drift detected but no alerts
- Alertmanager shows no alerts
- Webhook receiver receives nothing

**Diagnosis:**
```bash
# Check Prometheus alert rules
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool

# Check if alert condition is met
curl -s 'http://localhost:9090/api/v1/query?query=ml_drift_score>0.2' | python3 -m json.tool

# Check Alertmanager config
cat infra/alertmanager.yml
```

**Solutions:**

1. **Alert rule not loaded:**
```bash
# Check alerts.yml syntax
cat infra/alerts.yml

# Restart Prometheus
podman restart prometheus

# Verify rules loaded
curl -s http://localhost:9090/api/v1/rules | python3 -m json.tool
```

2. **Alert condition not met:**
```bash
# Check current drift score
curl -s http://localhost:8000/metrics | grep "ml_drift_score"

# Alert requires: ml_drift_score > 0.2 for 2 minutes
# Wait for condition to persist
```

3. **Alertmanager not receiving:**
```bash
# Check Prometheus → Alertmanager connection
curl -s http://localhost:9090/api/v1/alertmanagers | python3 -m json.tool

# Check Alertmanager logs
podman logs alertmanager
```

4. **Webhook not configured:**
```bash
# Verify webhook receiver in alertmanager.yml
cat infra/alertmanager.yml | grep -A 5 "webhook_configs"

# Test webhook manually
curl -X POST http://localhost:5001/alert \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"labels":{"alertname":"Test"},"status":"firing"}]}'
```

#### Issue 5: Replay Service Errors

**Symptoms:**
- Replay API returns 500/503 errors
- No events returned
- Database connection failures

**Diagnosis:**
```bash
# Check replay service health
curl http://localhost:8002/health

# Check database connection
podman exec postgres psql -U mluser -d mldb -c "SELECT 1;"

# Check replay service logs
podman logs replay-service
```

**Solutions:**

1. **Database not ready:**
```bash
# Wait for PostgreSQL initialization
sleep 15

# Restart replay service
podman restart replay-service
```

2. **No events in database:**
```bash
# Check event count
podman exec postgres psql -U mluser -d mldb -c "SELECT COUNT(*) FROM events;"

# Generate events
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2}'
```

3. **Inference API unreachable:**
```bash
# Check inference API health
curl http://localhost:8001/health

# Check network connectivity
podman exec replay-service curl http://inference-api:8001/health
```

#### Issue 6: High Memory Usage

**Symptoms:**
- System becomes slow
- Containers being killed (OOM)
- High swap usage

**Diagnosis:**
```bash
# Check container memory usage
podman stats --no-stream

# Check system memory
free -h

# Check specific service
podman stats drift-service --no-stream
```

**Solutions:**

1. **Redis memory growth:**
```bash
# Check Redis memory
podman exec redis redis-cli INFO memory

# Trim old events from stream
podman exec redis redis-cli XTRIM ml-events MAXLEN ~ 10000

# Set maxmemory in redis.conf
```

2. **PostgreSQL memory:**
```bash
# Check database size
podman exec postgres psql -U mluser -d mldb -c "SELECT pg_size_pretty(pg_database_size('mldb'));"

# Archive old events
podman exec postgres psql -U mluser -d mldb -c "DELETE FROM events WHERE created_at < NOW() - INTERVAL '7 days';"
```

3. **Drift service memory:**
```bash
# Reduce baseline/window size
# Edit drift-service/.env
# Set BASELINE_SIZE=50 (default: 100)
# Set WINDOW_SIZE=50 (default: 100)

# Restart service
podman restart drift-service
```

---

## Success Criteria

### Functional Requirements

**✓ Drift Detection:**
- [ ] System detects distribution shifts within 90 seconds
- [ ] Drift score increases above threshold (0.2)
- [ ] Feature-level drift scores calculated correctly
- [ ] Baseline collection completes successfully
- [ ] Sliding window updates continuously

**✓ Alerting:**
- [ ] Alerts fire when drift score exceeds threshold
- [ ] Alerts appear in Prometheus within 2 minutes
- [ ] Alerts forwarded to Alertmanager
- [ ] Webhook receiver logs alert payloads
- [ ] Alert annotations contain correct information

**✓ Replay Functionality:**
- [ ] Replay API returns comparison results
- [ ] Predictions are replayed through current model
- [ ] Confidence differences calculated correctly
- [ ] Statistics provide meaningful insights
- [ ] Events retrieved from database successfully

**✓ Monitoring:**
- [ ] All metrics exposed via Prometheus
- [ ] Grafana dashboards display data
- [ ] Service health checks respond correctly
- [ ] Logs contain relevant information
- [ ] Time-series data collected continuously

### Performance Requirements

**✓ Throughput:**
- [ ] System handles 5+ events/second
- [ ] No event loss under normal load
- [ ] Redis stream processes events in real-time
- [ ] Database writes complete successfully

**✓ Latency:**
- [ ] Inference API responds < 100ms (P95)
- [ ] Drift detection processes events < 1s
- [ ] Replay API responds < 5s for 50 events
- [ ] Metrics scraping completes < 10s

**✓ Resource Usage:**
- [ ] Total memory usage < 2GB
- [ ] CPU usage < 50% under load
- [ ] Disk usage grows predictably
- [ ] No memory leaks over 24 hours

### Reliability Requirements

**✓ Fault Tolerance:**
- [ ] Services recover from Redis failures
- [ ] Services recover from PostgreSQL failures
- [ ] No data loss during service restarts
- [ ] Consumer groups resume correctly
- [ ] Backlog processing works after downtime

**✓ Data Integrity:**
- [ ] Events stored correctly in database
- [ ] Predictions match expected format
- [ ] Metrics values are accurate
- [ ] No duplicate event processing
- [ ] Timestamps are correct

---

## Next Steps

After completing testing:

1. **Review Results:**
   - Document any failures or unexpected behavior
   - Collect performance metrics
   - Identify optimization opportunities

2. **Tune Parameters:**
   - Adjust drift detection thresholds
   - Optimize baseline/window sizes
   - Configure alert sensitivity

3. **Production Preparation:**
   - Set up persistent volumes
   - Configure backup strategies
   - Implement authentication
   - Set up monitoring alerts

4. **Documentation:**
   - Update runbooks with findings
   - Document known issues
   - Create troubleshooting guides

5. **Continuous Testing:**
   - Schedule regular test runs
   - Automate validation checks
   - Monitor for regressions

---

## Quick Reference

### Essential Commands

```bash
# Start system
cd infra && podman-compose up -d && cd ..

# Stop system
cd infra && podman-compose down && cd ..

# Run demo
bash scripts/demo.sh

# Check health
curl http://localhost:8000/health  # Drift
curl http://localhost:8001/health  # Inference
curl http://localhost:8002/health  # Replay

# View metrics
curl http://localhost:8000/metrics | grep "ml_drift"

# Check alerts
curl -s http://localhost:9090/api/v1/alerts | python3 -m json.tool

# Replay events
curl -X POST "http://localhost:8002/replay?limit=10" | python3 -m json.tool

# View logs
podman logs drift-service
podman logs -f inference-api

# Check Redis
podman exec redis redis-cli XLEN ml-events

# Check database
podman exec postgres psql -U mluser -d mldb -c "SELECT COUNT(*) FROM events;"
```

### Service URLs

- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)
- **Alertmanager:** http://localhost:9093
- **Inference API:** http://localhost:8001
- **Drift Service:** http://localhost:8000
- **Replay Service:** http://localhost:8002
- **Webhook Receiver:** http://localhost:5001

---

## Conclusion

This testing guide provides comprehensive coverage of the ML Observability Platform's testing requirements. Follow the scenarios systematically to validate all functionality, and use the troubleshooting section to resolve any issues encountered.

For additional information, refer to:
- [API Documentation](API.md)
- [Validation Guide](VALIDATION_GUIDE.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Build Specification](BUILD_SPEC.md)

**Happy Testing! 🚀**

---

*Made with Bob*