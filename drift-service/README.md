# Drift Detection Service

A production-grade real-time ML drift detection service that monitors data and prediction distributions using statistical methods.

> **Note**: This service supports both Docker and Podman container runtimes.

## Overview

The drift-service is a long-running Python service that consumes ML inference events from Redis Streams, performs statistical drift detection, and publishes alerts when distribution shifts are detected. It's a critical component of the ML observability platform, enabling early detection of model degradation and data quality issues.

### Purpose

- **Real-time drift detection**: Continuously monitor feature and prediction distributions
- **Statistical rigor**: Use proven statistical tests (KS test, PSI) for drift detection
- **Alerting**: Automatically publish alerts when drift is detected
- **Observability**: Expose Prometheus metrics for monitoring and visualization

### Key Features

- ✅ **Statistical Drift Detection**: Kolmogorov-Smirnov test and Population Stability Index
- ✅ **Prediction Monitoring**: Chi-square test for label distribution changes
- ✅ **Consumer Groups**: Reliable event processing with Redis Stream consumer groups
- ✅ **Dual Format Support**: Handles both data-generator and inference-api event formats
- ✅ **Real-time Alerting**: Publishes structured alerts to Redis Streams
- ✅ **Prometheus Integration**: Comprehensive metrics for monitoring
- ✅ **FastAPI Server**: HTTP endpoints for health checks and metrics
- ✅ **Sliding Window Analysis**: Compares baseline vs current distributions

## Architecture

### Components

```
drift-service/
├── consumer.py      # Redis Stream consumer with consumer groups
├── drift.py         # Statistical drift detection algorithms
├── metrics.py       # Prometheus metrics management
├── main.py          # Service orchestrator and FastAPI server
├── requirements.txt # Python dependencies
├── Dockerfile       # Container build configuration
└── .env.example     # Environment configuration template
```

### Data Flow

```
┌─────────────────┐
│ Data Generator  │
│ Inference API   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Redis Stream: ml-events             │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│   Drift Service (Consumer Group)        │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  1. Event Consumption            │  │
│  │     - Read from stream           │  │
│  │     - Parse dual formats         │  │
│  │     - Acknowledge messages       │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  2. Baseline Collection          │  │
│  │     - First 100 samples          │  │
│  │     - Feature distributions      │  │
│  │     - Prediction baseline        │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  3. Sliding Window Analysis      │  │
│  │     - Maintain 100-sample window │  │
│  │     - Compare to baseline        │  │
│  │     - KS test + PSI calculation  │  │
│  └──────────────────────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐  │
│  │  4. Drift Detection              │  │
│  │     - PSI > 0.2 OR               │  │
│  │     - KS p-value < 0.05          │  │
│  └──────────────────────────────────┘  │
└────────┬─────────────────────┬──────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ Redis Stream:   │   │ Prometheus      │
│ ml-alerts       │   │ Metrics         │
└─────────────────┘   └─────────────────┘
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌─────────────────┐
│ Alert Consumers │   │ Grafana         │
└─────────────────┘   └─────────────────┘
```

### Consumer Group Pattern

The service uses Redis Stream consumer groups for reliable event processing:

- **Consumer Group**: `drift-detector` (configurable)
- **Consumer Name**: `drift-worker-1` (configurable)
- **Benefits**:
  - Multiple consumers can process the same stream
  - Automatic load balancing
  - Message acknowledgment prevents data loss
  - Pending message recovery

## Configuration

### Environment Variables

The service is configured via environment variables. See [`.env.example`](.env.example) for a complete template.

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `STREAM_NAME` | `ml-events` | Input stream name |
| `ALERT_STREAM_NAME` | `ml-alerts` | Output alert stream name |
| `CONSUMER_GROUP` | `drift-detector` | Consumer group name |
| `CONSUMER_NAME` | `drift-worker-1` | Unique consumer identifier |
| `BASELINE_WINDOW_SIZE` | `100` | Number of samples for baseline |
| `SLIDING_WINDOW_SIZE` | `100` | Number of samples in sliding window |
| `DRIFT_THRESHOLD_PSI` | `0.2` | PSI threshold for drift detection |
| `DRIFT_THRESHOLD_KS` | `0.05` | KS test p-value threshold |
| `METRICS_PORT` | `8000` | Port for FastAPI metrics server |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CHECK_INTERVAL_MS` | `1000` | Stream polling interval in milliseconds |

### Drift Thresholds

**PSI (Population Stability Index)**:
- `< 0.1`: No significant change
- `0.1 - 0.2`: Small change
- `> 0.2`: **Drift detected** (default threshold)

**KS Test (Kolmogorov-Smirnov)**:
- p-value `< 0.05`: **Drift detected** (default threshold)
- Measures maximum distance between cumulative distributions

**Drift Trigger**: Drift is detected if **PSI > 0.2 OR p-value < 0.05**

### Window Sizes

- **Baseline Window**: First 100 events establish the reference distribution
- **Sliding Window**: Most recent 100 events for comparison
- Both windows are configurable via environment variables

## Running the Service

### Local Development (Non-Container)

1. **Install dependencies**:
   ```bash
   cd drift-service
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Ensure Redis is running**:
   ```bash
   # If using container infrastructure
   cd ../infra
   
   # Docker:
   docker compose -f docker-compose.yml up -d redis
   
   # Podman:
   podman-compose -f podman-compose.yml up -d redis
   ```

4. **Run the service**:
   ```bash
   python3 main.py
   ```

### With Container Compose

**Start all services** (recommended):

Docker:
```bash
cd infra
docker compose -f docker-compose.yml up -d
```

Podman:
```bash
cd infra
podman-compose -f podman-compose.yml up -d
```

**Start only drift-service**:

Docker:
```bash
cd infra
docker compose -f docker-compose.yml up -d drift-service
```

Podman:
```bash
cd infra
podman-compose -f podman-compose.yml up -d drift-service
```

**View logs**:

Docker:
```bash
docker compose -f infra/docker-compose.yml logs -f drift-service
```

Podman:
```bash
podman-compose -f infra/podman-compose.yml logs -f drift-service
```

**Restart service**:

Docker:
```bash
docker compose -f infra/docker-compose.yml restart drift-service
```

Podman:
```bash
podman-compose -f infra/podman-compose.yml restart drift-service
```

**Stop service**:

Docker:
```bash
docker compose -f infra/docker-compose.yml stop drift-service
```

Podman:
```bash
podman-compose -f infra/podman-compose.yml stop drift-service
```

## API Endpoints

The service exposes a FastAPI server on port 8000 (configurable).

### GET /health

Health check endpoint.

**Request**:
```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "service": "drift-detection",
  "timestamp": "2024-01-01T00:00:00.000000"
}
```

### GET /metrics

Prometheus metrics endpoint in text format.

**Request**:
```bash
curl http://localhost:8000/metrics
```

**Response**: Prometheus text format metrics (see [Metrics](#metrics) section)

## Metrics

The service exposes comprehensive Prometheus metrics for monitoring.

### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `drift_events_processed_total` | - | Total number of events processed |
| `drift_detected_total` | `feature`, `drift_type` | Total drift detections by feature and type |
| `drift_alerts_published_total` | - | Total alerts published to Redis |

### Gauges

| Metric | Labels | Description |
|--------|--------|-------------|
| `drift_score_feature_1` | - | Current PSI score for feature_1 |
| `drift_score_feature_2` | - | Current PSI score for feature_2 |
| `drift_score_feature_3` | - | Current PSI score for feature_3 |
| `drift_ks_statistic` | `feature` | KS test statistic per feature |
| `drift_ks_p_value` | `feature` | KS test p-value per feature |
| `drift_psi_score` | `feature` | PSI score per feature |
| `drift_prediction_distribution` | `label` | Prediction label distribution |
| `drift_baseline_samples_collected` | - | Number of baseline samples collected |
| `drift_sliding_window_samples` | - | Current sliding window size |
| `drift_baseline_complete` | - | Baseline completion status (0 or 1) |

### Histograms

| Metric | Buckets | Description |
|--------|---------|-------------|
| `drift_processing_latency_seconds` | 0.001 to 5.0 | Event processing time distribution |

### Example Queries

**Drift detection rate**:
```promql
rate(drift_detected_total[5m])
```

**Average processing latency**:
```promql
rate(drift_processing_latency_seconds_sum[5m]) / rate(drift_processing_latency_seconds_count[5m])
```

**Current drift scores**:
```promql
drift_psi_score
```

## Drift Detection Logic

### Statistical Methods

#### 1. Kolmogorov-Smirnov (KS) Test

Tests whether two samples come from the same distribution.

- **Null Hypothesis**: Baseline and sliding window have the same distribution
- **Test Statistic**: Maximum distance between cumulative distributions
- **Decision**: Reject null hypothesis if p-value < 0.05 (drift detected)

**Implementation**: [`drift.py:164-166`](drift.py#L164-L166)

#### 2. Population Stability Index (PSI)

Measures the shift in population distribution.

**Formula**:
```
PSI = Σ (Actual% - Expected%) × ln(Actual% / Expected%)
```

**Interpretation**:
- PSI < 0.1: No significant change
- 0.1 ≤ PSI < 0.2: Small change
- PSI ≥ 0.2: Significant change (drift)

**Implementation**: [`drift.py:256-294`](drift.py#L256-L294)

#### 3. Chi-Square Test (Predictions)

Tests independence between baseline and sliding prediction distributions.

- Used for categorical prediction labels
- Detects shifts in prediction class balance

**Implementation**: [`drift.py:221-232`](drift.py#L221-L232)

### Detection Workflow

1. **Baseline Collection** (first 100 events):
   - Collect feature values for each feature
   - Collect prediction labels
   - No drift detection during this phase

2. **Sliding Window** (after baseline):
   - Maintain 100-event sliding window
   - Compare to baseline using KS test and PSI
   - Detect drift if PSI > 0.2 OR p-value < 0.05

3. **Alert Publishing**:
   - Publish to `ml-alerts` stream when drift detected
   - Include statistical details and distribution metrics

## Alert Format

Alerts are published to the `ml-alerts` Redis Stream with the following structure:

### Feature Drift Alert

```json
{
  "drift_type": "psi+ks_test",
  "feature": "feature_1",
  "score": 0.25,
  "timestamp": "2024-01-01T00:00:00.000000",
  "details": {
    "ks_statistic": 0.15,
    "p_value": 0.03,
    "psi_score": 0.25,
    "baseline_mean": 0.0,
    "baseline_std": 1.0,
    "sliding_mean": 5.0,
    "sliding_std": 1.0
  }
}
```

### Prediction Drift Alert

```json
{
  "drift_type": "prediction",
  "feature": "prediction",
  "score": 0.22,
  "timestamp": "2024-01-01T00:00:00.000000",
  "details": {
    "psi_score": 0.22,
    "p_value": 0.04,
    "baseline_distribution": {"0": 0.5, "1": 0.5},
    "sliding_distribution": {"0": 0.7, "1": 0.3}
  }
}
```

### Consuming Alerts

**Docker:**
```bash
# Read alerts from Redis
docker exec ml-obs-redis redis-cli XREAD COUNT 10 STREAMS ml-alerts 0
```

**Podman:**
```bash
# Read alerts from Redis
podman exec ml-obs-redis redis-cli XREAD COUNT 10 STREAMS ml-alerts 0
```

## Event Format Support

The service supports two event formats:

### 1. Data Generator Format

Single `event` field containing JSON:

```json
{
  "event": "{\"request_id\": \"...\", \"feature_1\": 0.5, ...}"
}
```

### 2. Inference API Format

Flattened structure with JSON string fields:

```json
{
  "request_id": "...",
  "timestamp": "...",
  "features": "{\"feature_1\": 0.5, ...}",
  "prediction": "{\"label\": 0, ...}",
  "metadata": "{...}"
}
```

Both formats are automatically detected and parsed by [`consumer.py`](consumer.py).

## Troubleshooting

### Consumer Group Already Exists

**Symptom**: Error message about consumer group already existing

**Solution**: This is handled automatically. The service will use the existing group.

### Redis Connection Issues

**Symptom**: `Failed to connect to Redis` errors

**Solutions**:
1. Verify Redis is running:
   
   Docker:
   ```bash
   docker compose ps redis
   ```
   
   Podman:
   ```bash
   podman-compose ps redis
   ```

2. Check Redis connectivity:
   
   Docker:
   ```bash
   docker exec ml-obs-redis redis-cli ping
   ```
   
   Podman:
   ```bash
   podman exec ml-obs-redis redis-cli ping
   ```

3. Verify `REDIS_HOST` and `REDIS_PORT` environment variables

4. Check network connectivity (ensure service is on `ml-obs-network`)

### Event Parsing Errors

**Symptom**: `Error parsing event` in logs

**Solutions**:
1. Verify event format matches expected schema
2. Check Redis stream contents:
   
   Docker:
   ```bash
   docker exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-events 0
   ```
   
   Podman:
   ```bash
   podman exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-events 0
   ```
3. Enable DEBUG logging: `LOG_LEVEL=DEBUG`

### Insufficient Baseline Samples

**Symptom**: No drift detection occurring

**Solutions**:
1. Check baseline collection status:
   ```bash
   curl http://localhost:8000/metrics | grep baseline
   ```

2. Verify events are being consumed:
   ```bash
   curl http://localhost:8000/metrics | grep events_processed
   ```

3. Ensure at least 100 events have been published to `ml-events`

### No Drift Detected

**Symptom**: Drift expected but not detected

**Solutions**:
1. Check current drift scores:
   ```bash
   curl http://localhost:8000/metrics | grep drift_score
   ```

2. Verify thresholds are appropriate:
   - Lower `DRIFT_THRESHOLD_PSI` (e.g., 0.1)
   - Raise `DRIFT_THRESHOLD_KS` (e.g., 0.1)

3. Check if sliding window is full:
   ```bash
   curl http://localhost:8000/metrics | grep sliding_window
   ```

### High Processing Latency

**Symptom**: Slow event processing

**Solutions**:
1. Check processing latency metrics:
   ```bash
   curl http://localhost:8000/metrics | grep processing_latency
   ```

2. Reduce window sizes for faster processing
3. Increase `CHECK_INTERVAL_MS` to reduce polling frequency
4. Consider horizontal scaling with multiple consumers

## Development

### Running Tests Locally

```bash
cd drift-service
python3 -m pytest tests/
```

### Monitoring Logs

**Local development**:
```bash
python3 main.py
```

**Container logs**:

Docker:
```bash
docker compose logs -f drift-service
```

Podman:
```bash
podman-compose logs -f drift-service
```

**Debug mode**:
```bash
LOG_LEVEL=DEBUG python3 main.py
```

### Adjusting Thresholds

For testing drift detection:

1. **Lower thresholds** (more sensitive):
   ```bash
   DRIFT_THRESHOLD_PSI=0.1 DRIFT_THRESHOLD_KS=0.1 python3 main.py
   ```

2. **Higher thresholds** (less sensitive):
   ```bash
   DRIFT_THRESHOLD_PSI=0.3 DRIFT_THRESHOLD_KS=0.01 python3 main.py
   ```

### Testing with Data Generator

1. Start infrastructure:
   
   Docker:
   ```bash
   cd infra && docker compose up -d
   ```
   
   Podman:
   ```bash
   cd infra && podman-compose up -d
   ```

2. Run data generator (baseline):
   ```bash
   cd data-generator && python3 generator.py
   ```

3. Wait for baseline collection (100 events)

4. Run data generator with drift:
   ```bash
   ENABLE_DRIFT=true python3 generator.py
   ```

5. Monitor drift detection:
   ```bash
   curl http://localhost:8000/metrics | grep drift_detected
   ```

## Performance

- **Throughput**: Processes 100+ events/second
- **Latency**: < 100ms per event (typical)
- **Memory**: ~50-100 MB (baseline + sliding windows)
- **CPU**: Low utilization during normal operation

## Integration

### With Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'drift-service'
    static_configs:
      - targets: ['drift-service:8000']
```

### With Grafana

Create dashboards using metrics:
- Drift scores over time
- Alert frequency
- Processing latency
- Baseline/sliding window status

### With Alert Consumers

Consume alerts from `ml-alerts` stream:

```python
import redis
import json

r = redis.Redis(host='localhost', port=6379)
messages = r.xread({'ml-alerts': '0'}, count=10)

for stream, msgs in messages:
    for msg_id, data in msgs:
        alert = json.loads(data[b'alert'])
        print(f"Drift detected: {alert['feature']} - {alert['drift_type']}")
```

## Related Documentation

- [Project README](../README.md) - Platform overview
- [Architecture](../docs/ARCHITECTURE.md) - System design and flow
- [Testing](../docs/TESTING.md) - Validation workflow
- [Inference API Documentation](../inference-api/README.md) - Inference service

## License

See [LICENSE](../LICENSE).
