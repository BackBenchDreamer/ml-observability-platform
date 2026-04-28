# Phase 4 Validation Guide

**Version**: 1.0.0  
**Date**: 2026-04-28  
**Status**: Complete

## Table of Contents

1. [Introduction](#1-introduction)
2. [Pre-Deployment Checklist](#2-pre-deployment-checklist)
3. [Deployment Steps](#3-deployment-steps)
4. [Service Health Checks](#4-service-health-checks)
5. [End-to-End Flow Validation](#5-end-to-end-flow-validation)
6. [Prometheus Validation](#6-prometheus-validation)
7. [Grafana Dashboard Validation](#7-grafana-dashboard-validation)
8. [Performance Validation](#8-performance-validation)
9. [Error Handling Validation](#9-error-handling-validation)
10. [Cleanup and Teardown](#10-cleanup-and-teardown)
11. [Troubleshooting Common Issues](#11-troubleshooting-common-issues)
12. [Success Criteria](#12-success-criteria)
13. [Next Steps](#13-next-steps)

---

## 1. Introduction

### Purpose

This validation guide provides comprehensive step-by-step instructions for testing the complete Phase 4 implementation of the ML Observability Platform. It ensures that all components work correctly together and that the drift detection system operates as expected.

### What Will Be Validated

- ✅ Infrastructure deployment (Redis, PostgreSQL, Prometheus, Grafana)
- ✅ Inference API service
- ✅ Drift detection service
- ✅ Event streaming and consumption
- ✅ Statistical drift detection (KS test, PSI)
- ✅ Alert publishing
- ✅ Metrics collection and exposure
- ✅ Prometheus scraping
- ✅ Grafana dashboard visualization
- ✅ Error handling and recovery
- ✅ Performance benchmarks

### Prerequisites

Before starting validation, ensure you have:

- **Podman** installed (version 4.0+)
- **podman-compose** installed (version 1.0+)
- **curl** for API testing
- **jq** for JSON parsing (optional but recommended)
- **Python 3.11+** for running the data generator
- At least **4GB RAM** available
- At least **10GB disk space** available

---

## 2. Pre-Deployment Checklist

### Step 1: Verify Podman Installation

```bash
podman --version
```

**Expected Output**:
```
podman version 4.x.x
```

### Step 2: Verify podman-compose Installation

```bash
podman-compose --version
```

**Expected Output**:
```
podman-compose version 1.x.x
```

### Step 3: Check Available Ports

Ensure the following ports are not in use:

```bash
# Check if ports are available
lsof -i :6379  # Redis
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Drift Service
lsof -i :8001  # Inference API
lsof -i :9090  # Prometheus
lsof -i :3000  # Grafana
```

**Expected**: No output (ports are free)

If ports are in use, either stop the conflicting services or modify the port mappings in `infra/podman-compose.yml`.

### Step 4: Verify Project Structure

```bash
cd /Users/jeyadheepv/grepo/ml-observability-platform
tree -L 2 -d
```

**Expected Structure**:
```
.
├── data-generator/
├── docs/
├── drift-service/
├── inference-api/
├── infra/
│   └── grafana/
└── schemas/
```

### Step 5: Verify Configuration Files

```bash
# Check critical files exist
ls -la infra/podman-compose.yml
ls -la infra/prometheus.yml
ls -la infra/grafana/provisioning/dashboards/drift-detection.json
ls -la drift-service/Dockerfile
ls -la inference-api/Dockerfile
```

**Expected**: All files should exist with appropriate permissions.

---

## 3. Deployment Steps

### Step 1: Start Infrastructure

Navigate to the infrastructure directory and start all services:

```bash
cd infra
podman-compose -f podman-compose.yml up -d
```

**Expected Output**:
```
Creating network ml-obs-network
Creating volume ml-obs_redis-data
Creating volume ml-obs_postgres-data
Creating volume ml-obs_prometheus-data
Creating volume ml-obs_grafana-data
Creating ml-obs-redis ... done
Creating ml-obs-postgres ... done
Creating ml-obs-prometheus ... done
Creating ml-obs-grafana ... done
Creating ml-obs-inference-api ... done
Creating ml-obs-drift-service ... done
```

**Wait Time**: Allow 30-60 seconds for all services to initialize and pass health checks.

### Step 2: Verify All Services Started

```bash
podman-compose ps
```

**Expected Output**:
```
NAME                      STATUS      PORTS
ml-obs-redis              Up (healthy)     0.0.0.0:6379->6379/tcp
ml-obs-postgres           Up (healthy)     0.0.0.0:5432->5432/tcp
ml-obs-prometheus         Up (healthy)     0.0.0.0:9090->9090/tcp
ml-obs-grafana            Up (healthy)     0.0.0.0:3000->3000/tcp
ml-obs-inference-api      Up (healthy)     0.0.0.0:8001->8001/tcp
ml-obs-drift-service      Up (healthy)     0.0.0.0:8000->8000/tcp
```

**All services should show "Up (healthy)" status.**

### Step 3: Check Service Logs

Verify each service started without errors:

**Redis**:
```bash
podman-compose logs redis | tail -20
```
Expected: "Ready to accept connections"

**PostgreSQL**:
```bash
podman-compose logs postgres | tail -20
```
Expected: "database system is ready to accept connections"

**Prometheus**:
```bash
podman-compose logs prometheus | tail -20
```
Expected: "Server is ready to receive web requests"

**Grafana**:
```bash
podman-compose logs grafana | tail -20
```
Expected: "HTTP Server Listen"

**Inference API**:
```bash
podman-compose logs inference-api | tail -20
```
Expected: "Application startup complete"

**Drift Service**:
```bash
podman-compose logs -f drift-service
```
Expected: 
- "Connected to Redis"
- "Consumer group created/exists"
- "Drift detection service started"
- "Uvicorn running on http://0.0.0.0:8000"

Press `Ctrl+C` to stop following logs.

---

## 4. Service Health Checks

### Test 1: Redis Health Check

```bash
podman exec ml-obs-redis redis-cli ping
```

**Expected Output**: `PONG`

**Verify Stream Support**:
```bash
podman exec ml-obs-redis redis-cli INFO | grep stream
```

### Test 2: PostgreSQL Health Check

```bash
podman exec ml-obs-postgres pg_isready -U mlobs -d ml_observability
```

**Expected Output**: `ml_observability:5432 - accepting connections`

### Test 3: Inference API Health Check

```bash
curl http://localhost:8001/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "service": "inference-api",
  "model_version": "1.0.0",
  "timestamp": "2026-04-28T20:00:00.000000"
}
```

### Test 4: Drift Service Health Check

```bash
curl http://localhost:8000/health
```

**Expected Output**:
```json
{
  "status": "healthy",
  "service": "drift-detection",
  "timestamp": "2026-04-28T20:00:00.000000"
}
```

### Test 5: Prometheus Health Check

```bash
curl http://localhost:9090/-/healthy
```

**Expected Output**: `Prometheus is Healthy.`

**Verify Configuration**:
```bash
curl http://localhost:9090/api/v1/status/config | jq '.status'
```
Expected: `"success"`

### Test 6: Grafana Health Check

```bash
curl http://localhost:3000/api/health
```

**Expected Output**:
```json
{
  "database": "ok",
  "version": "10.x.x"
}
```

---

## 5. End-to-End Flow Validation

This section validates the complete data flow from event generation through drift detection to alerting.

### Test 1: Generate Events

Start the data generator to publish events to Redis:

```bash
# Open a new terminal
cd data-generator
python3 generator.py
```

**Expected Output**:
```
Starting ML event generator...
Publishing events to Redis stream: ml-events
Event published: request_id=...
Event published: request_id=...
...
```

**Let it run for 30-60 seconds** to generate 100+ events for baseline collection.

### Test 2: Verify Events in Redis

In another terminal, check that events are being published:

```bash
podman exec ml-obs-redis redis-cli XLEN ml-events
```

**Expected Output**: A number greater than 0 and increasing (e.g., `150`)

**View Recent Events**:
```bash
podman exec ml-obs-redis redis-cli XREAD COUNT 2 STREAMS ml-events 0
```

Expected: JSON event data with features and predictions

### Test 3: Check Drift Service Processing

Verify the drift service is consuming and processing events:

```bash
curl http://localhost:8000/metrics | grep events_processed_total
```

**Expected Output**:
```
# HELP events_processed_total Total number of events processed
# TYPE events_processed_total counter
events_processed_total 150.0
```

The counter should match or be close to the number of events in Redis.

### Test 4: Monitor Baseline Collection

Watch the drift service logs for baseline collection progress:

```bash
podman-compose logs -f drift-service | grep -i baseline
```

**Expected Output**:
```
INFO: Collecting baseline samples: 50/100
INFO: Collecting baseline samples: 75/100
INFO: Collecting baseline samples: 100/100
INFO: Baseline collection complete
```

**Verify Baseline Metrics**:
```bash
curl http://localhost:8000/metrics | grep baseline
```

Expected:
```
drift_baseline_samples_collected 100.0
drift_baseline_complete 1.0
```

**Stop the data generator** (Ctrl+C) once baseline is complete.

### Test 5: Verify Drift Detection (Normal Data)

With baseline collected, check drift scores for normal data:

```bash
curl http://localhost:8000/metrics | grep drift_score
```

**Expected Output**:
```
drift_score_feature_1 0.05
drift_score_feature_2 0.03
drift_score_feature_3 0.04
```

Scores should be low (< 0.2) for normal data.

### Test 6: Test Drift Simulation

Enable drift in the data generator to simulate distribution shift:

```bash
cd data-generator
ENABLE_DRIFT=true python3 generator.py
```

**Let it run for 30-60 seconds** to generate drifted events.

**Expected Output**:
```
Starting ML event generator...
DRIFT ENABLED - Generating shifted distributions
Event published: request_id=...
```

### Test 7: Verify Drift Detection (Drifted Data)

Check that drift is detected:

```bash
# Check drift scores (should increase)
curl http://localhost:8000/metrics | grep drift_score

# Check drift detection counter
curl http://localhost:8000/metrics | grep drift_detected_total
```

**Expected Output**:
```
drift_score_feature_1 0.35
drift_score_feature_2 0.28
drift_score_feature_3 0.42
drift_detected_total{drift_type="psi+ks_test",feature="feature_1"} 5.0
drift_detected_total{drift_type="psi+ks_test",feature="feature_3"} 3.0
```

Drift scores should exceed 0.2, and `drift_detected_total` should increment.

**Check Drift Service Logs**:
```bash
podman-compose logs drift-service | grep -i "drift detected"
```

Expected: Multiple "Drift detected" messages with feature names and scores.

### Test 8: Verify Alerts Published

Check that alerts were published to the `ml-alerts` stream:

```bash
# Check alert stream length
podman exec ml-obs-redis redis-cli XLEN ml-alerts
```

**Expected Output**: Number > 0 (e.g., `8`)

**Read Alert Details**:
```bash
podman exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-alerts 0
```

**Expected Output**:
```
1) 1) "ml-alerts"
   2) 1) 1) "1714334400000-0"
         2) 1) "alert"
            2) "{\"drift_type\":\"psi+ks_test\",\"feature\":\"feature_1\",\"score\":0.35,\"timestamp\":\"2026-04-28T20:00:00.000000\",\"details\":{\"ks_statistic\":0.18,\"p_value\":0.02,\"psi_score\":0.35,\"baseline_mean\":0.0,\"baseline_std\":1.0,\"sliding_mean\":5.2,\"sliding_std\":1.1}}"
```

**Verify Alert Metrics**:
```bash
curl http://localhost:8000/metrics | grep alerts_published_total
```

Expected: Counter > 0

**Stop the data generator** (Ctrl+C).

---

## 6. Prometheus Validation

### Test 1: Verify Drift Service Target

Check that Prometheus is successfully scraping the drift service:

```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="drift-service")'
```

**Expected Output**:
```json
{
  "discoveredLabels": {...},
  "labels": {
    "instance": "drift-service:8000",
    "job": "drift-service"
  },
  "scrapePool": "drift-service",
  "scrapeUrl": "http://drift-service:8000/metrics",
  "globalUrl": "http://drift-service:8000/metrics",
  "lastError": "",
  "lastScrape": "2026-04-28T20:00:00.000Z",
  "lastScrapeDuration": 0.015,
  "health": "up",
  "scrapeInterval": "15s",
  "scrapeTimeout": "10s"
}
```

**Key Fields**:
- `health`: Should be `"up"`
- `lastError`: Should be empty `""`
- `lastScrapeDuration`: Should be < 1 second

### Test 2: Query Drift Metrics

Test various Prometheus queries:

**Events Processed**:
```bash
curl 'http://localhost:9090/api/v1/query?query=events_processed_total' | jq '.data.result[0].value'
```

Expected: `["timestamp", "150"]` (or current count)

**Drift Detected**:
```bash
curl 'http://localhost:9090/api/v1/query?query=drift_detected_total' | jq '.data.result'
```

Expected: Array with drift detection counts per feature

**Feature Drift Scores**:
```bash
curl 'http://localhost:9090/api/v1/query?query=drift_score_feature_1' | jq '.data.result[0].value'
```

Expected: `["timestamp", "0.35"]` (current drift score)

**Processing Latency (P95)**:
```bash
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(processing_latency_seconds_bucket[5m]))' | jq '.data.result[0].value'
```

Expected: `["timestamp", "0.05"]` (< 0.1 seconds)

### Test 3: Verify All Scrape Targets

```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Expected Output**:
```json
{"job": "prometheus", "health": "up"}
{"job": "drift-service", "health": "up"}
```

All targets should have `"health": "up"`.

### Test 4: Test Time-Series Queries

**Drift Detection Rate (last 5 minutes)**:
```bash
curl 'http://localhost:9090/api/v1/query?query=rate(drift_detected_total[5m])' | jq '.data.result'
```

**Events Per Second**:
```bash
curl 'http://localhost:9090/api/v1/query?query=rate(events_processed_total[1m])' | jq '.data.result'
```

---

## 7. Grafana Dashboard Validation

### Test 1: Access Grafana

Open your web browser and navigate to:

```
http://localhost:3000
```

**Login Credentials**:
- Username: `admin`
- Password: `admin`

**Expected**: Grafana home page loads successfully. You may be prompted to change the password (optional for testing).

### Test 2: Verify Data Source

Navigate to: **Configuration** → **Data Sources**

**Expected**:
- Prometheus data source should be listed
- Status: Green checkmark with "Data source is working"

**Test Data Source**:
Click on the Prometheus data source and click **Save & Test** button.

Expected: "Data source is working" message

### Test 3: Navigate to Dashboard

Navigate to: **Dashboards** → **Browse** → **ML Observability** → **ML Drift Detection Dashboard**

**Expected**: Dashboard loads with 15 panels organized in 5 rows.

### Test 4: Verify Dashboard Panels

The dashboard should contain the following panels with real-time data:

#### Row 1: Overview Metrics (4 panels)

**Panel 1: Events Processed**
- Type: Stat panel
- Metric: `rate(events_processed_total[5m])`
- Unit: Events per second (eps)
- Color: Green (< 10 eps), Yellow (10-50 eps), Red (> 50 eps)
- Expected: Shows current event processing rate

**Panel 2: Total Drift Detections**
- Type: Stat panel
- Metric: `sum(drift_detected_total)`
- Unit: Count
- Color: Green (0), Red (> 0)
- Expected: Shows total number of drift detections

**Panel 3: Alerts Published**
- Type: Stat panel
- Metric: `sum(alerts_published_total)`
- Unit: Count
- Expected: Shows total alerts published to ml-alerts stream

**Panel 4: Processing Latency (P95)**
- Type: Gauge panel
- Metric: `histogram_quantile(0.95, rate(processing_latency_seconds_bucket[5m]))`
- Unit: Seconds
- Thresholds: Green (< 0.1s), Yellow (0.1-0.5s), Red (> 0.5s)
- Expected: Shows 95th percentile processing latency

#### Row 2: Feature Drift Scores (3 panels)

**Panel 5: Feature 1 Drift Score**
- Type: Time series
- Metric: `drift_score_feature_1`
- Range: 0-1
- Thresholds: Green (< 0.2), Yellow (0.2-0.4), Red (> 0.4)
- Expected: Line graph showing drift score over time

**Panel 6: Feature 2 Drift Score**
- Type: Time series
- Metric: `drift_score_feature_2`
- Range: 0-1
- Thresholds: Green (< 0.2), Yellow (0.2-0.4), Red (> 0.4)
- Expected: Line graph showing drift score over time

**Panel 7: Feature 3 Drift Score**
- Type: Time series
- Metric: `drift_score_feature_3`
- Range: 0-1
- Thresholds: Green (< 0.2), Yellow (0.2-0.4), Red (> 0.4)
- Expected: Line graph showing drift score over time

#### Row 3: Statistical Tests (3 panels)

**Panel 8: KS Test Statistics**
- Type: Time series
- Metrics: `drift_ks_statistic{feature="feature_1"}`, `feature_2`, `feature_3`
- Expected: Shows Kolmogorov-Smirnov test statistics for each feature

**Panel 9: KS Test P-Values**
- Type: Time series
- Metrics: `drift_ks_p_value{feature="feature_1"}`, `feature_2`, `feature_3`
- Threshold: 0.05 (significance level)
- Expected: Shows p-values; values < 0.05 indicate drift

**Panel 10: PSI Scores**
- Type: Time series
- Metrics: `drift_psi_score{feature="feature_1"}`, `feature_2`, `feature_3`
- Threshold: 0.2 (drift threshold)
- Expected: Shows Population Stability Index for each feature

#### Row 4: Prediction Distribution (2 panels)

**Panel 11: Prediction Distribution**
- Type: Bar gauge or Time series
- Metrics: `drift_prediction_distribution{label="0"}`, `label="1"`
- Expected: Shows distribution of prediction labels over time

**Panel 12: Prediction Drift**
- Type: Stat panel
- Metric: `sum(drift_detected_total{drift_type="prediction_drift"})`
- Expected: Shows count of prediction drift detections

#### Row 5: System Health (3 panels)

**Panel 13: Baseline Status**
- Type: Stat panel
- Metrics: 
  - `drift_baseline_samples_collected`
  - `drift_baseline_complete`
- Expected: Shows baseline collection progress (100/100 when complete)

**Panel 14: Sliding Window Size**
- Type: Stat panel
- Metric: `drift_sliding_window_samples`
- Expected: Shows current sliding window size (should be 100)

**Panel 15: Drift Detection Rate**
- Type: Time series
- Metric: `rate(drift_detected_total[5m])`
- Expected: Shows rate of drift detections over time

### Test 5: Verify Real-Time Updates

Set the dashboard refresh rate to **5 seconds** (top-right corner).

**Expected Behavior**:
- All panels should update every 5 seconds
- Time series graphs should show new data points
- Stat panels should reflect current values
- No "No Data" messages (if events are being generated)

### Test 6: Test Time Range Selection

Change the time range (top-right corner) to:
- Last 5 minutes
- Last 15 minutes
- Last 1 hour

**Expected**: All panels should adjust to show data for the selected time range.

### Test 7: Verify Annotations

If drift was detected, you should see red vertical lines on time series panels indicating drift events.

**Expected**: Annotations appear at timestamps when `drift_detected_total` increased.

### Test 8: Test Panel Interactions

- **Hover** over time series graphs: Tooltip should show exact values
- **Click and drag** to zoom into a time range
- **Click** on legend items to show/hide specific metrics
- **Click** on panel title → **Edit**: Opens panel editor

---

## 8. Performance Validation

### Test 1: Processing Latency

Measure the drift service processing latency:

```bash
curl http://localhost:8000/metrics | grep processing_latency_seconds
```

**Expected Output**:
```
processing_latency_seconds_bucket{le="0.005"} 50.0
processing_latency_seconds_bucket{le="0.01"} 120.0
processing_latency_seconds_bucket{le="0.025"} 145.0
processing_latency_seconds_bucket{le="0.05"} 150.0
processing_latency_seconds_bucket{le="0.1"} 150.0
processing_latency_seconds_sum 5.5
processing_latency_seconds_count 150.0
```

**Calculate P95 Latency**:
```bash
curl 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(processing_latency_seconds_bucket[5m]))' | jq '.data.result[0].value[1]'
```

**Expected**: P95 latency < 100ms (0.1 seconds)

### Test 2: Event Throughput

Measure events processed per second:

```bash
curl 'http://localhost:9090/api/v1/query?query=rate(events_processed_total[1m])' | jq '.data.result[0].value[1]'
```

**Expected**: 
- With data generator: 3-5 events/second
- System should handle 100+ events/second without issues

### Test 3: Memory Usage

Check drift service memory consumption:

```bash
podman stats ml-obs-drift-service --no-stream
```

**Expected Output**:
```
CONTAINER            CPU %   MEM USAGE / LIMIT   MEM %   NET I/O       BLOCK I/O   PIDS
ml-obs-drift-service 2.5%    85MB / 4GB          2.1%    1.2MB / 800KB 0B / 0B     5
```

**Acceptable Ranges**:
- Memory: 50-150 MB (with baseline + sliding windows)
- CPU: < 10% during normal operation
- Memory should be stable, not continuously increasing

### Test 4: Redis Memory Usage

Check Redis memory consumption:

```bash
podman exec ml-obs-redis redis-cli INFO memory | grep used_memory_human
```

**Expected**: < 100 MB for typical workloads

### Test 5: Stress Test (Optional)

Generate high event volume:

```bash
cd data-generator
# Run multiple generators in parallel
for i in {1..5}; do
  python3 generator.py &
done
```

**Monitor**:
```bash
# Watch processing rate
watch -n 1 'curl -s http://localhost:8000/metrics | grep events_processed_total'

# Watch latency
watch -n 1 'curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(processing_latency_seconds_bucket[1m]))" | jq ".data.result[0].value[1]"'
```

**Expected**:
- Service continues processing without errors
- Latency remains < 200ms even under load
- No memory leaks (memory stabilizes)

**Stop generators**:
```bash
pkill -f generator.py
```

---

## 9. Error Handling Validation

### Test 1: Service Restart

Test that the drift service recovers gracefully from restart:

```bash
# Restart drift service
podman-compose restart drift-service

# Wait 10 seconds
sleep 10

# Check health
curl http://localhost:8000/health
```

**Expected**:
- Service restarts successfully
- Health check returns healthy status
- Service reconnects to Redis
- Consumer group continues from last acknowledged message
- No data loss

**Verify in logs**:
```bash
podman-compose logs drift-service | tail -30
```

Expected: "Connected to Redis", "Consumer group exists", "Service started"

### Test 2: Redis Disconnect and Reconnect

Test drift service behavior when Redis is temporarily unavailable:

```bash
# Stop Redis
podman-compose stop redis

# Check drift service logs
podman-compose logs -f drift-service
```

**Expected Behavior**:
- Drift service logs connection errors
- Service continues attempting to reconnect
- Health endpoint may return unhealthy

**Restart Redis**:
```bash
podman-compose start redis

# Wait for Redis to be healthy
sleep 10
```

**Expected Recovery**:
- Drift service automatically reconnects
- Processing resumes
- Health check returns healthy
- No manual intervention required

**Verify**:
```bash
curl http://localhost:8000/health
podman-compose logs drift-service | tail -20
```

### Test 3: Invalid Event Handling

Publish a malformed event to test error handling:

```bash
# Publish invalid event
podman exec ml-obs-redis redis-cli XADD ml-events '*' invalid 'bad_data'

# Check drift service logs
podman-compose logs drift-service | grep -i error
```

**Expected Behavior**:
- Error logged: "Error processing event" or "Failed to parse event"
- Service continues processing subsequent events
- Invalid event is acknowledged (not reprocessed)
- Metrics show error count (if implemented)

**Verify Service Still Works**:
```bash
# Generate valid event
cd data-generator
python3 -c "from generator import publish_event; import redis; r = redis.Redis(host='localhost', port=6379); publish_event(r)"

# Check processing continues
curl http://localhost:8000/metrics | grep events_processed_total
```

### Test 4: Consumer Group Recovery

Test pending message recovery:

```bash
# Check pending messages
podman exec ml-obs-redis redis-cli XPENDING ml-events drift-detector

# Force restart without acknowledgment (simulate crash)
podman kill ml-obs-drift-service
podman-compose up -d drift-service

# Wait for service to start
sleep 10

# Check logs for pending message recovery
podman-compose logs drift-service | grep -i pending
```

**Expected**:
- Service detects pending messages
- Pending messages are reprocessed
- No data loss

### Test 5: Baseline Reset

Test behavior when baseline needs to be recollected:

```bash
# Clear Redis streams (simulates fresh start)
podman exec ml-obs-redis redis-cli DEL ml-events
podman exec ml-obs-redis redis-cli DEL ml-alerts

# Restart drift service
podman-compose restart drift-service

# Generate new events
cd data-generator
python3 generator.py
```

**Expected**:
- Service starts baseline collection from scratch
- Baseline metrics reset to 0
- After 100 events, baseline collection completes
- Drift detection resumes normally

---

## 10. Cleanup and Teardown

### Stop All Services

```bash
cd infra
podman-compose -f podman-compose.yml down
```

**Expected Output**:
```
Stopping ml-obs-drift-service ... done
Stopping ml-obs-inference-api ... done
Stopping ml-obs-grafana ... done
Stopping ml-obs-prometheus ... done
Stopping ml-obs-postgres ... done
Stopping ml-obs-redis ... done
Removing ml-obs-drift-service ... done
Removing ml-obs-inference-api ... done
Removing ml-obs-grafana ... done
Removing ml-obs-prometheus ... done
Removing ml-obs-postgres ... done
Removing ml-obs-redis ... done
Removing network ml-obs-network
```

### Remove Volumes (Optional)

**⚠️ Warning**: This will delete all data including Prometheus metrics, Grafana dashboards, and Redis data.

```bash
podman-compose -f podman-compose.yml down -v
```

**Expected Output**:
```
Removing volume ml-obs_redis-data
Removing volume ml-obs_postgres-data
Removing volume ml-obs_prometheus-data
Removing volume ml-obs_grafana-data
```

### Verify Cleanup

```bash
# Check no containers running
podman ps -a | grep ml-obs
```

**Expected**: No output (all containers removed)

```bash
# Check no volumes (if removed)
podman volume ls | grep ml-obs
```

**Expected**: No output (if volumes were removed)

### Clean Up Images (Optional)

```bash
# List images
podman images | grep ml-obs

# Remove specific images
podman rmi ml-obs-drift-service
podman rmi ml-obs-inference-api
```

---

## 11. Troubleshooting Common Issues

### Issue 1: Port Already in Use

**Symptoms**:
- Service fails to start
- Error: "address already in use"

**Solution**:

```bash
# Find process using the port (example: port 8000)
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in podman-compose.yml
# Example: Change "8000:8000" to "8002:8000"
```

### Issue 2: Service Won't Start

**Symptoms**:
- Container exits immediately
- Status shows "Exited (1)"

**Diagnosis**:

```bash
# Check logs for errors
podman-compose logs <service-name>

# Check container exit code
podman inspect ml-obs-<service-name> | jq '.[0].State'
```

**Common Causes**:
1. **Missing dependencies**: Ensure Redis is healthy before drift-service starts
2. **Configuration error**: Check environment variables in podman-compose.yml
3. **Build failure**: Rebuild image with `podman-compose build <service-name>`

**Solution**:

```bash
# Verify dependencies are healthy
podman-compose ps

# Restart service
podman-compose restart <service-name>

# Rebuild if needed
podman-compose build <service-name>
podman-compose up -d <service-name>
```

### Issue 3: No Metrics in Grafana

**Symptoms**:
- Dashboard shows "No Data"
- Panels are empty

**Diagnosis**:

```bash
# Check Prometheus is scraping drift-service
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="drift-service")'

# Check drift-service metrics endpoint
curl http://localhost:8000/metrics
```

**Common Causes**:
1. **Prometheus not scraping**: Check prometheus.yml configuration
2. **Drift service not exposing metrics**: Verify /metrics endpoint works
3. **No events processed**: Generate events with data generator
4. **Time range issue**: Adjust Grafana time range to include data

**Solution**:

```bash
# Restart Prometheus to reload config
podman-compose restart prometheus

# Verify scrape targets
curl http://localhost:9090/api/v1/targets

# Generate events
cd data-generator
python3 generator.py

# Check metrics appear
curl http://localhost:8000/metrics | grep events_processed_total
```

### Issue 4: Drift Not Detected

**Symptoms**:
- `drift_detected_total` remains 0
- Drift scores stay low even with ENABLE_DRIFT=true

**Diagnosis**:

```bash
# Check baseline is complete
curl http://localhost:8000/metrics | grep baseline_complete

# Check drift scores
curl http://localhost:8000/metrics | grep drift_score

# Check drift thresholds
podman-compose logs drift-service | grep -i threshold
```

**Common Causes**:
1. **Baseline not complete**: Need 100 events before drift detection starts
2. **Drift not significant enough**: Increase drift magnitude in generator
3. **Thresholds too high**: Lower PSI/KS thresholds in configuration
4. **Sliding window not full**: Need 100 events in sliding window

**Solution**:

```bash
# Ensure baseline is complete (100 events)
# Generate more events if needed
cd data-generator
python3 generator.py  # Run until baseline complete

# Enable strong drift
ENABLE_DRIFT=true python3 generator.py

# Check drift service logs
podman-compose logs -f drift-service | grep -i drift

# Verify drift scores increase
watch -n 2 'curl -s http://localhost:8000/metrics | grep drift_score'
```

### Issue 5: Consumer Group Errors

**Symptoms**:
- Error: "BUSYGROUP Consumer Group name already exists"
- Error: "NOGROUP No such consumer group"

**Diagnosis**:

```bash
# Check consumer groups
podman exec ml-obs-redis redis-cli XINFO GROUPS ml-events

# Check consumers in group
podman exec ml-obs-redis redis-cli XINFO CONSUMERS ml-events drift-detector
```

**Solution for BUSYGROUP** (normal, handled by service):
- This is expected on restart
- Service automatically handles this error
- No action needed

**Solution for NOGROUP**:
```bash
# Recreate consumer group
podman exec ml-obs-redis redis-cli XGROUP CREATE ml-events drift-detector 0 MKSTREAM

# Restart drift service
podman-compose restart drift-service
```

**Solution for stuck consumer**:
```bash
# Delete consumer group and recreate
podman exec ml-obs-redis redis-cli XGROUP DESTROY ml-events drift-detector

# Restart drift service (will recreate group)
podman-compose restart drift-service
```

### Issue 6: High Memory Usage

**Symptoms**:
- Drift service memory continuously increasing
- System becomes slow

**Diagnosis**:

```bash
# Monitor memory over time
watch -n 5 'podman stats ml-obs-drift-service --no-stream'

# Check window sizes
curl http://localhost:8000/metrics | grep window
```

**Solution**:

```bash
# Reduce window sizes in podman-compose.yml
# Change BASELINE_WINDOW_SIZE and SLIDING_WINDOW_SIZE to 50

# Restart service
podman-compose restart drift-service
```

### Issue 7: Grafana Dashboard Not Loading

**Symptoms**:
- Dashboard not found
- Dashboard shows errors

**Diagnosis**:

```bash
# Check Grafana logs
podman-compose logs grafana | grep -i error

# Verify dashboard file exists
ls -la infra/grafana/provisioning/dashboards/drift-detection.json

# Check provisioning configuration
cat infra/grafana/provisioning/dashboards/dashboards.yml
```

**Solution**:

```bash
# Restart Grafana
podman-compose restart grafana

# Wait for provisioning
sleep 15

# Access Grafana and refresh browser
# Navigate to Dashboards → Browse
```

---

## 12. Success Criteria

Phase 4 is successfully validated when all of the following criteria are met:

### Infrastructure

- ✅ All 6 services start successfully (Redis, PostgreSQL, Prometheus, Grafana, Inference API, Drift Service)
- ✅ All services pass health checks
- ✅ All services show "Up (healthy)" status in `podman-compose ps`
- ✅ No errors in service logs

### Event Flow

- ✅ Events flow from data generator to Redis Stream (`ml-events`)
- ✅ Drift service consumes events from Redis Stream
- ✅ Consumer group created successfully
- ✅ Events acknowledged after processing

### Drift Detection

- ✅ Baseline collection completes (100 events)
- ✅ `drift_baseline_complete` metric shows 1.0
- ✅ Drift detection works with normal data (low scores < 0.2)
- ✅ Drift detection works with drifted data (high scores > 0.2)
- ✅ `drift_detected_total` increments when drift occurs
- ✅ Drift scores update in real-time

### Alerting

- ✅ Alerts published to `ml-alerts` stream when drift detected
- ✅ Alert format is valid JSON with required fields
- ✅ `alerts_published_total` metric increments
- ✅ Alerts contain statistical details (KS, PSI, distribution stats)

### Metrics & Monitoring

- ✅ Drift service exposes metrics at `/metrics` endpoint
- ✅ Prometheus scrapes drift-service successfully
- ✅ All drift-service targets show "up" status in Prometheus
- ✅ Metrics queries return valid data
- ✅ Time-series data available for visualization

### Grafana Dashboard

- ✅ Grafana accessible at http://localhost:3000
- ✅ Prometheus data source configured and working
- ✅ ML Drift Detection Dashboard loads successfully
- ✅ All 15 panels display data
- ✅ Dashboard updates in real-time (5s refresh)
- ✅ Time range selection works
- ✅ Annotations show drift events

### Performance

- ✅ Processing latency P95 < 100ms
- ✅ Service handles 100+ events/second
- ✅ Memory usage stable (50-150 MB)
- ✅ CPU usage < 10% during normal operation
- ✅ No memory leaks observed

### Error Handling

- ✅ Service recovers from restart
- ✅ Service reconnects after Redis disconnect
- ✅ Invalid events handled gracefully
- ✅ Pending messages recovered after crash
- ✅ No data loss during failures

### Documentation

- ✅ All validation steps documented
- ✅ Expected outputs provided
- ✅ Troubleshooting guide available
- ✅ Success criteria clearly defined

---

## 13. Next Steps

After successful validation, consider the following next steps:

### 1. Review and Adjust Thresholds

Based on your specific use case, you may need to adjust drift detection thresholds:

```yaml
# In podman-compose.yml, drift-service environment:
DRIFT_THRESHOLD_PSI: 0.2    # Adjust based on sensitivity needs
DRIFT_THRESHOLD_KS: 0.05    # Adjust based on significance level
```

**Recommendations**:
- **More sensitive** (detect smaller drifts): PSI=0.1, KS=0.1
- **Less sensitive** (only major drifts): PSI=0.3, KS=0.01
- **Balanced** (default): PSI=0.2, KS=0.05

### 2. Customize Grafana Dashboards

Enhance the dashboard for your specific needs:

- Add custom panels for business-specific metrics
- Create alerts based on drift thresholds
- Add annotations for model deployments
- Create separate dashboards for different models
- Set up dashboard snapshots for reporting

**Access Dashboard Editor**:
- Navigate to dashboard
- Click panel title → Edit
- Modify queries, visualizations, thresholds
- Save dashboard

### 3. Set Up Alerting Rules in Prometheus

Create alert rules for critical conditions:

```yaml
# Add to prometheus.yml
rule_files:
  - 'alerts.yml'

# Create alerts.yml
groups:
  - name: drift_alerts
    interval: 30s
    rules:
      - alert: HighDriftDetected
        expr: drift_score_feature_1 > 0.4
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High drift detected on feature_1"
          description: "Drift score {{ $value }} exceeds threshold"
```

### 4. Configure Alert Notifications

Set up notifications for drift alerts:

**Options**:
- **Email**: Configure SMTP in Grafana
- **Slack**: Set up Slack webhook integration
- **PagerDuty**: Configure PagerDuty integration
- **Webhook**: Send alerts to custom endpoints

**Grafana Alerting**:
- Navigate to Alerting → Contact points
- Add notification channels
- Create alert rules based on Prometheus queries

### 5. Plan for Production Deployment

Prepare for production:

**Infrastructure**:
- [ ] Set up persistent volumes for production data
- [ ] Configure backup and restore procedures
- [ ] Implement log aggregation (ELK, Loki)
- [ ] Set up monitoring and alerting
- [ ] Configure SSL/TLS for external access

**Security**:
- [ ] Change default passwords (Grafana, PostgreSQL)
- [ ] Implement authentication for APIs
- [ ] Set up network policies
- [ ] Enable Redis authentication
- [ ] Configure firewall rules

**Scalability**:
- [ ] Plan for horizontal scaling (multiple drift-service instances)
- [ ] Set up load balancing
- [ ] Configure Redis cluster for high availability
- [ ] Implement database replication

### 6. Consider Scaling Strategies

For high-volume production workloads:

**Horizontal Scaling**:
```yaml
# Add multiple drift-service instances
drift-service-1:
  # ... same config ...
  environment:
    CONSUMER_NAME: drift-worker-1

drift-service-2:
  # ... same config ...
  environment:
    CONSUMER_NAME: drift-worker-2
```

**Benefits**:
- Load balancing across consumers
- Higher throughput
- Fault tolerance
- Zero-downtime deployments

### 7. Implement Historical Data Storage

Store drift metrics for long-term analysis:

- Configure PostgreSQL schema for drift history
- Create tables for drift scores, alerts, baselines
- Implement data retention policies
- Set up periodic data exports
- Create historical trend analysis queries

### 8. Integrate with ML Pipeline

Connect drift detection to your ML workflow:

- Trigger model retraining on drift detection
- Implement A/B testing for model versions
- Set up automated model validation
- Create feedback loops for continuous improvement
- Integrate with MLOps platforms (MLflow, Kubeflow)

### 9. Enhance Drift Detection

Add advanced drift detection capabilities:

- **Multivariate drift**: Detect drift across multiple features simultaneously
- **Concept drift**: Detect changes in prediction patterns
- **Adaptive thresholds**: Automatically adjust thresholds based on historical data
- **Root cause analysis**: Identify which features contribute most to drift
- **Drift prediction**: Predict future drift based on trends

### 10. Documentation and Training

Ensure team readiness:

- Document operational procedures
- Create runbooks for common issues
- Train team on dashboard interpretation
- Establish on-call procedures
- Create incident response playbooks

---

## Appendix A: Quick Reference Commands

### Service Management

```bash
# Start all services
cd infra && podman-compose up -d

# Stop all services
podman-compose down

# Restart specific service
podman-compose restart drift-service

# View logs
podman-compose logs -f drift-service

# Check service status
podman-compose ps
```

### Health Checks

```bash
# All services
curl http://localhost:6379  # Redis (connection test)
curl http://localhost:8000/health  # Drift Service
curl http://localhost:8001/health  # Inference API
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

### Metrics

```bash
# View all drift metrics
curl http://localhost:8000/metrics

# Specific metrics
curl http://localhost:8000/metrics | grep drift_score
curl http://localhost:8000/metrics | grep events_processed
curl http://localhost:8000/metrics | grep drift_detected
```

### Redis Operations

```bash
# Check stream length
podman exec ml-obs-redis redis-cli XLEN ml-events

# Read events
podman exec ml-obs-redis redis-cli XREAD COUNT 5 STREAMS ml-events 0

# Check alerts
podman exec ml-obs-redis redis-cli XLEN ml-alerts
podman exec ml-obs-redis redis-cli XREAD COUNT 5 STREAMS ml-alerts 0

# Consumer group info
podman exec ml-obs-redis redis-cli XINFO GROUPS ml-events
```

### Data Generation

```bash
# Normal data
cd data-generator && python3 generator.py

# Drifted data
cd data-generator && ENABLE_DRIFT=true python3 generator.py
```

---

## Appendix B: Metrics Reference

### Counter Metrics

| Metric | Description | Labels |

|--------|-------------|--------|
| `events_processed_total` | Total events processed by drift service | - |
| `drift_detected_total` | Total drift detections | `feature`, `drift_type` |
| `alerts_published_total` | Total alerts published to ml-alerts stream | - |

### Gauge Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `drift_score_feature_1` | Current drift score for feature 1 | - |
| `drift_score_feature_2` | Current drift score for feature 2 | - |
| `drift_score_feature_3` | Current drift score for feature 3 | - |
| `drift_ks_statistic` | KS test statistic | `feature` |
| `drift_ks_p_value` | KS test p-value | `feature` |
| `drift_psi_score` | Population Stability Index | `feature` |
| `drift_prediction_distribution` | Prediction label distribution | `label` |
| `drift_baseline_samples_collected` | Number of baseline samples collected | - |
| `drift_sliding_window_samples` | Current sliding window size | - |
| `drift_baseline_complete` | Baseline collection status (0 or 1) | - |

### Histogram Metrics

| Metric | Description | Buckets |
|--------|-------------|---------|
| `processing_latency_seconds` | Event processing latency | 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 |

---

## Appendix C: Alert Schema

### Alert Format

Alerts published to the `ml-alerts` Redis Stream follow this JSON schema:

```json
{
  "drift_type": "psi+ks_test",
  "feature": "feature_1",
  "score": 0.35,
  "timestamp": "2026-04-28T20:00:00.000000",
  "details": {
    "ks_statistic": 0.18,
    "p_value": 0.02,
    "psi_score": 0.35,
    "baseline_mean": 0.0,
    "baseline_std": 1.0,
    "sliding_mean": 5.2,
    "sliding_std": 1.1
  }
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `drift_type` | string | Type of drift detected (`psi+ks_test`, `prediction_drift`) |
| `feature` | string | Feature name where drift was detected |
| `score` | float | Drift score (PSI value) |
| `timestamp` | string | ISO 8601 timestamp of detection |
| `details.ks_statistic` | float | Kolmogorov-Smirnov test statistic |
| `details.p_value` | float | KS test p-value |
| `details.psi_score` | float | Population Stability Index |
| `details.baseline_mean` | float | Mean of baseline distribution |
| `details.baseline_std` | float | Standard deviation of baseline |
| `details.sliding_mean` | float | Mean of current sliding window |
| `details.sliding_std` | float | Standard deviation of sliding window |

---

## Appendix D: Environment Variables Reference

### Drift Service Configuration

| Variable | Default | Description | Valid Values |
|----------|---------|-------------|--------------|
| `REDIS_HOST` | `localhost` | Redis hostname | Any valid hostname |
| `REDIS_PORT` | `6379` | Redis port | 1-65535 |
| `STREAM_NAME` | `ml-events` | Input stream name | Any string |
| `ALERT_STREAM_NAME` | `ml-alerts` | Alert stream name | Any string |
| `CONSUMER_GROUP` | `drift-detector` | Consumer group name | Any string |
| `CONSUMER_NAME` | `drift-worker-1` | Consumer identifier | Any string |
| `BASELINE_WINDOW_SIZE` | `100` | Baseline sample count | > 0 |
| `SLIDING_WINDOW_SIZE` | `100` | Sliding window size | > 0 |
| `DRIFT_THRESHOLD_PSI` | `0.2` | PSI drift threshold | 0.0-1.0 |
| `DRIFT_THRESHOLD_KS` | `0.05` | KS p-value threshold | 0.0-1.0 |
| `METRICS_PORT` | `8000` | Metrics server port | 1-65535 |
| `LOG_LEVEL` | `INFO` | Logging level | DEBUG, INFO, WARNING, ERROR |
| `CHECK_INTERVAL_MS` | `1000` | Stream polling interval | > 0 |

---

## Appendix E: Prometheus Query Examples

### Basic Queries

```promql
# Current drift score for feature 1
drift_score_feature_1

# All drift scores
drift_score_feature_1
drift_score_feature_2
drift_score_feature_3

# Total events processed
events_processed_total

# Total drift detections
sum(drift_detected_total)

# Drift detections by feature
drift_detected_total{feature="feature_1"}
```

### Rate Queries

```promql
# Events per second (1 minute rate)
rate(events_processed_total[1m])

# Drift detections per minute (5 minute rate)
rate(drift_detected_total[5m]) * 60

# Alert publishing rate
rate(alerts_published_total[5m])
```

### Aggregation Queries

```promql
# Maximum drift score across all features
max(drift_score_feature_1, drift_score_feature_2, drift_score_feature_3)

# Average drift score
avg(drift_score_feature_1 + drift_score_feature_2 + drift_score_feature_3) / 3

# Total drift detections by drift type
sum by (drift_type) (drift_detected_total)
```

### Latency Queries

```promql
# P50 latency
histogram_quantile(0.50, rate(processing_latency_seconds_bucket[5m]))

# P95 latency
histogram_quantile(0.95, rate(processing_latency_seconds_bucket[5m]))

# P99 latency
histogram_quantile(0.99, rate(processing_latency_seconds_bucket[5m]))

# Average latency
rate(processing_latency_seconds_sum[5m]) / rate(processing_latency_seconds_count[5m])
```

### Alert Queries

```promql
# High drift score alert
drift_score_feature_1 > 0.4

# Drift detected in last 5 minutes
changes(drift_detected_total[5m]) > 0

# High processing latency
histogram_quantile(0.95, rate(processing_latency_seconds_bucket[5m])) > 0.1

# Low event throughput
rate(events_processed_total[5m]) < 1
```

---

## Appendix F: Grafana Panel Queries

### Overview Metrics Panels

**Events Processed (Stat)**:
```promql
rate(events_processed_total[5m])
```

**Total Drift Detections (Stat)**:
```promql
sum(drift_detected_total)
```

**Alerts Published (Stat)**:
```promql
sum(alerts_published_total)
```

**Processing Latency P95 (Gauge)**:
```promql
histogram_quantile(0.95, sum by (le) (rate(processing_latency_seconds_bucket[5m])))
```

### Feature Drift Score Panels

**Feature 1 Drift Score (Time Series)**:
```promql
drift_score_feature_1
```

**Feature 2 Drift Score (Time Series)**:
```promql
drift_score_feature_2
```

**Feature 3 Drift Score (Time Series)**:
```promql
drift_score_feature_3
```

### Statistical Test Panels

**KS Statistics (Time Series)**:
```promql
drift_ks_statistic{feature="feature_1"}
drift_ks_statistic{feature="feature_2"}
drift_ks_statistic{feature="feature_3"}
```

**KS P-Values (Time Series)**:
```promql
drift_ks_p_value{feature="feature_1"}
drift_ks_p_value{feature="feature_2"}
drift_ks_p_value{feature="feature_3"}
```

**PSI Scores (Time Series)**:
```promql
drift_psi_score{feature="feature_1"}
drift_psi_score{feature="feature_2"}
drift_psi_score{feature="feature_3"}
```

---

## Appendix G: Troubleshooting Decision Tree

```
Issue: Service won't start
├─ Check: Container status
│  ├─ Exited (1) → Check logs for errors
│  ├─ Restarting → Check health check configuration
│  └─ Not found → Run podman-compose up -d
│
├─ Check: Dependencies
│  ├─ Redis not healthy → Wait or restart Redis
│  ├─ Port conflict → Change port or kill process
│  └─ Build failed → Run podman-compose build
│
└─ Check: Configuration
   ├─ Invalid env vars → Fix podman-compose.yml
   └─ Missing files → Verify project structure

Issue: No metrics in Grafana
├─ Check: Prometheus scraping
│  ├─ Target down → Check drift-service health
│  ├─ Scrape errors → Check /metrics endpoint
│  └─ No targets → Verify prometheus.yml
│
├─ Check: Data availability
│  ├─ No events → Start data generator
│  ├─ Baseline incomplete → Generate 100+ events
│  └─ Time range → Adjust Grafana time range
│
└─ Check: Dashboard
   ├─ Dashboard not found → Restart Grafana
   ├─ Panel errors → Check query syntax
   └─ Data source → Verify Prometheus connection

Issue: Drift not detected
├─ Check: Baseline
│  ├─ Not complete → Generate more events
│  └─ Complete → Check drift_baseline_complete=1
│
├─ Check: Drift magnitude
│  ├─ Too small → Enable ENABLE_DRIFT=true
│  └─ Thresholds → Lower PSI/KS thresholds
│
└─ Check: Sliding window
   ├─ Not full → Generate more events
   └─ Full → Check drift scores increasing
```

---

## Appendix H: Performance Tuning Guide

### For Higher Throughput

```yaml
# Reduce polling interval
CHECK_INTERVAL_MS: 100

# Reduce window sizes
BASELINE_WINDOW_SIZE: 50
SLIDING_WINDOW_SIZE: 50

# Add more consumers
# Deploy multiple drift-service instances with different CONSUMER_NAME
```

### For Lower Resource Usage

```yaml
# Increase polling interval
CHECK_INTERVAL_MS: 5000

# Reduce log verbosity
LOG_LEVEL: WARNING

# Smaller windows
BASELINE_WINDOW_SIZE: 50
SLIDING_WINDOW_SIZE: 50
```

### For More Sensitive Detection

```yaml
# Lower thresholds
DRIFT_THRESHOLD_PSI: 0.1
DRIFT_THRESHOLD_KS: 0.1

# Larger windows for stability
BASELINE_WINDOW_SIZE: 200
SLIDING_WINDOW_SIZE: 200
```

### For Less Sensitive Detection

```yaml
# Higher thresholds
DRIFT_THRESHOLD_PSI: 0.3
DRIFT_THRESHOLD_KS: 0.01

# Smaller windows
BASELINE_WINDOW_SIZE: 50
SLIDING_WINDOW_SIZE: 50
```

---

## Appendix I: Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `BUSYGROUP Consumer Group name already exists` | Consumer group exists from previous run | Normal, service handles automatically |
| `NOGROUP No such consumer group` | Consumer group not created | Service will create it automatically |
| `Connection refused` | Redis not running or wrong host/port | Check Redis status, verify REDIS_HOST/PORT |
| `Failed to parse event` | Invalid event format | Check event schema, verify data generator |
| `Baseline not complete` | Less than 100 events collected | Generate more events |
| `address already in use` | Port conflict | Change port or kill conflicting process |
| `Health check failed` | Service not responding | Check logs, verify service started |
| `No data` in Grafana | No metrics available | Generate events, check Prometheus scraping |

---

## Conclusion

This validation guide provides comprehensive testing procedures for Phase 4 of the ML Observability Platform. By following these steps, you can ensure that:

- All infrastructure components are properly deployed
- The drift detection service operates correctly
- Statistical drift detection works as expected
- Alerts are published when drift occurs
- Metrics are collected and visualized
- The system handles errors gracefully
- Performance meets requirements

For questions or issues not covered in this guide, refer to:
- [Phase 4 Documentation](PHASE_4.md)
- [Drift Service README](../drift-service/README.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Build Specification](BUILD_SPEC.md)

---

**Validation Guide Complete** ✅  
**Ready for Production Testing** 🚀

**Made with Bob** 🤖
