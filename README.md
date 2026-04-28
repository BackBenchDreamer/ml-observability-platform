# ML Observability Platform

A phased, event-driven ML observability platform for generating inference events, detecting drift, exposing metrics, and visualizing system behavior.

## Current Status

- ✅ Phase 1 complete — Infrastructure setup
- ✅ Phase 2 complete — Data generator service
- ✅ Phase 3 complete — Inference API
- ✅ Phase 4 complete — Drift detection service
- ✅ Phase 5 complete — Monitoring and alerting system
- ✅ Phase 6 complete — Replay system

Detailed implementation notes are documented per phase:

- [Phase 1 Documentation](docs/PHASE_1.md)
- [Phase 2 Documentation](docs/PHASE_2.md)
- [Phase 3 Documentation](inference-api/README.md)
- [Phase 4 Documentation](docs/PHASE_4.md)
- [Phase 5 Documentation](docs/PHASE_5.md)
- [Build Specification](docs/BUILD_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Technical Decisions](docs/DECISIONS.md)

## Quick Start

### Prerequisites

- Podman
- podman-compose
- Python 3 (for running the data generator locally)

On macOS:

```bash
brew install podman podman-compose
podman machine init
podman machine start
```

### Start Full Stack

Start all services with Podman Compose:

```bash
cd infra
podman-compose -f podman-compose.yml up -d
```

Verify all services are healthy:

```bash
podman-compose ps
```

Wait until all services report `healthy` status (may take 30-60 seconds).

### Access Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Inference API**: http://localhost:8001
- **Drift Service**: http://localhost:8000
- **Replay Service**: http://localhost:8002
- **Redis**: `localhost:6379`
- **PostgreSQL**: `localhost:5432`

Default local development credentials:

- Grafana: `admin` / `admin`
- PostgreSQL: `mlobs` / `mlobs_pass`

### Quick Verification

**Check drift service health**:
```bash
curl http://localhost:8000/health
```

**View drift metrics**:
```bash
curl http://localhost:8000/metrics
```

**Check inference API**:
```bash
curl http://localhost:8001/health
```

**View service logs**:
```bash
podman-compose logs -f drift-service
```

## Run the Data Generator

For detailed setup and configuration, see:

- [Phase 2 Documentation](docs/PHASE_2.md)
- [Data Generator Service README](data-generator/README.md)

Basic local run:

```bash
cd data-generator
pip install -r requirements.txt
python generator.py
```

Run with drift enabled:

```bash
cd data-generator
ENABLE_DRIFT=true python generator.py
```

### Verify Events in Redis

```bash
podman exec ml-obs-redis redis-cli XLEN ml-events
podman exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-events 0
```

## Phase 3: Inference API

FastAPI service that provides ML predictions and publishes events to Redis.

- **Endpoint:** `POST /predict` for inference
- **Model:** RandomForest classifier with 3 features for binary classification
- **Eventing:** Automatically publishes prediction events to Redis Stream `ml-events`
- **Health Check:** `GET /health`
- **Port:** `8001`

Quick start:

```bash
cd infra && podman-compose up -d inference-api
```

Example API call:

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'
```

For detailed service documentation, see [`inference-api/README.md`](inference-api/README.md).

## Phase 4: Drift Detection Service ✅

Real-time ML drift detection service with statistical analysis and alerting.

### Features

- ✅ **Statistical Drift Detection**: KS test and PSI for feature distributions
- ✅ **Prediction Monitoring**: Chi-square test for label distribution changes
- ✅ **Real-time Alerting**: Publishes alerts to Redis Streams (`ml-alerts`)
- ✅ **Prometheus Metrics**: Comprehensive metrics for monitoring
- ✅ **Consumer Groups**: Reliable event processing with acknowledgment
- ✅ **Dual Format Support**: Handles data-generator and inference-api events

### Endpoints

- **Health Check**: `GET /health` at http://localhost:8000/health
- **Metrics**: `GET /metrics` at http://localhost:8000/metrics

### Quick Start

**Start with Podman Compose**:
```bash
cd infra
podman-compose up -d drift-service
```

**View logs**:
```bash
podman-compose logs -f drift-service
```

**Check metrics**:
```bash
curl http://localhost:8000/metrics | grep drift
```

### Drift Detection Workflow

1. **Baseline Collection** (first 100 events):
   - Collects feature distributions
   - Establishes reference baseline
   - No drift detection during this phase

2. **Sliding Window Analysis** (after baseline):
   - Maintains 100-event sliding window
   - Compares to baseline using KS test and PSI
   - Detects drift if PSI > 0.2 OR p-value < 0.05

3. **Alert Publishing**:
   - Publishes to `ml-alerts` Redis Stream
   - Includes statistical details and distribution metrics

### Testing Drift Detection

**Generate baseline events**:
```bash
cd data-generator
python3 generator.py
# Let run for ~30 seconds, then Ctrl+C
```

**Generate drift events**:
```bash
ENABLE_DRIFT=true python3 generator.py
# Let run for ~30 seconds, then Ctrl+C
```

**Check for drift alerts**:
```bash
podman exec ml-obs-redis redis-cli XREAD COUNT 10 STREAMS ml-alerts 0
```

### Metrics Exposed

- `drift_events_processed_total` - Total events processed
- `drift_detected_total{feature, drift_type}` - Drift detections by feature
- `drift_psi_score{feature}` - PSI scores per feature
- `drift_ks_statistic{feature}` - KS test statistics
- `drift_prediction_distribution{label}` - Prediction distribution
- `drift_processing_latency_seconds` - Processing time histogram

### Configuration

Key environment variables (see [`drift-service/.env.example`](drift-service/.env.example)):

- `BASELINE_WINDOW_SIZE=100` - Baseline sample count
- `SLIDING_WINDOW_SIZE=100` - Sliding window size
- `DRIFT_THRESHOLD_PSI=0.2` - PSI drift threshold
- `DRIFT_THRESHOLD_KS=0.05` - KS test p-value threshold

For comprehensive documentation, see:
- [Drift Service README](drift-service/README.md) - Service-level documentation
- [Phase 4 Documentation](docs/PHASE_4.md) - Complete phase implementation details

## Phase 5: Monitoring and Alerting System ✅

Converts passive monitoring into an active alerting system with automated notifications.

### Alert Pipeline Flow

1. **Prometheus** scrapes metrics from drift-service every 15 seconds
2. **Alert rules** evaluate conditions (drift, latency, throughput)
3. **Alertmanager** receives and groups alerts
4. **Webhook receiver** logs alert notifications

### Key Components

- **Prometheus Alert Rules** (`infra/alerts.yml`):
  - `HighDriftScore`: Triggers when `ml_drift_score > 0.2` for 2 minutes
  - `PredictionThroughputDrop`: Triggers when prediction rate drops to 0 for 2 minutes
  - `HighInferenceLatency`: Triggers when P95 latency exceeds 1 second for 2 minutes

- **Alertmanager** (`infra/alertmanager.yml`):
  - Routes alerts to webhook receiver
  - Groups alerts by severity and service
  - Configurable notification channels

- **Webhook Receiver** (`infra/webhook_receiver.py`):
  - Receives alert notifications from Alertmanager
  - Logs alert details for debugging
  - Extensible for Slack, email, or PagerDuty integration

- **Grafana Dashboards** (3 dashboards):
  - **ML Drift Monitoring**: Real-time drift scores and detection events
  - **Prediction Distribution**: Prediction label distribution and trends
  - **System Health**: Service health, latency, and throughput metrics

### How to Test Alerts

**Start the system**:
```bash
cd infra
podman-compose up -d
```

**Trigger HighDriftScore alert**:
```bash
cd data-generator
ENABLE_DRIFT=true python generator.py
# Let run for 2+ minutes to trigger alert
```

**Trigger PredictionThroughputDrop alert**:
```bash
# Stop the data-generator
# Wait 2+ minutes for alert to fire
```

**Check alerts**:
- Prometheus alerts: http://localhost:9090/alerts
- Alertmanager: http://localhost:9093
- Webhook logs: `podman logs -f webhook-receiver`

### Grafana Dashboards

Access pre-configured dashboards at http://localhost:3000 (admin/admin):

- **ML Drift Monitoring**: http://localhost:3000/d/ml-drift-monitor
- **Prediction Distribution**: http://localhost:3000/d/prediction-dist
- **System Health**: http://localhost:3000/d/system-health

For detailed documentation, see [Phase 5 Documentation](docs/PHASE_5.md).

## Phase 6: Replay System ✅

Event replay system for debugging ML failures and comparing model versions.

### Why Replay Matters

When ML models fail in production, you need to:
- **Reproduce the exact failure** with historical data
- **Compare predictions** between model versions
- **Debug confidence changes** to understand model behavior
- **Validate fixes** before redeployment

The replay system stores every inference event in PostgreSQL and allows you to replay them through the current model to see how predictions have changed.

### System Flow

```
1. Inference API → PostgreSQL (event persistence)
   ↓
2. Replay Service fetches events from PostgreSQL
   ↓
3. Replay Service sends features to Inference API
   ↓
4. Compare old vs new predictions
   ↓
5. Return confidence differences
```

### Features

- ✅ **PostgreSQL Event Persistence**: All events stored with `request_id` uniqueness
- ✅ **Batch Replay**: Replay up to 50 events at once
- ✅ **Model Version Filtering**: Filter events by specific model version
- ✅ **Confidence Comparison**: Calculate prediction confidence differences
- ✅ **Health Monitoring**: Database and inference API connectivity checks

### Endpoints

- **Replay Events**: `POST /replay?model_version=v2&limit=50`
- **Health Check**: `GET /health` at http://localhost:8002/health
- **API Docs**: http://localhost:8002/docs

### Quick Start

**Start replay service**:
```bash
cd infra
podman-compose up -d replay-service
```

**Check service health**:
```bash
curl http://localhost:8002/health
```

### API Usage Examples

**Replay last 10 events**:
```bash
curl -X POST "http://localhost:8002/replay?limit=10"
```

**Replay events for specific model version**:
```bash
curl -X POST "http://localhost:8002/replay?model_version=v1.0.0&limit=20"
```

**Example response**:
```json
{
  "replayed_count": 10,
  "model_version": "v1.0.0",
  "comparisons": [
    {
      "request_id": "abc-123",
      "old_prediction": {
        "label": 0,
        "confidence": 0.85
      },
      "new_prediction": {
        "label": 0,
        "confidence": 0.92
      },
      "confidence_diff": 0.07
    }
  ]
}
```

### Testing Replay

**Generate some events**:
```bash
cd data-generator
python3 generator.py
# Let run for 30 seconds, then Ctrl+C
```

**Verify events are stored**:
```bash
podman exec ml-obs-postgres psql -U mlobs -d ml_observability \
  -c "SELECT COUNT(*) FROM ml_events;"
```

**Replay the events**:
```bash
curl -X POST "http://localhost:8002/replay?limit=5"
```

### Database Schema

Events are stored in the `ml_events` table:
- `request_id` (PRIMARY KEY) - Ensures uniqueness
- `timestamp` - Event timestamp (indexed)
- `model_version` - Model version (indexed)
- `features` - JSONB feature data
- `prediction` - JSONB prediction data
- `metadata` - JSONB metadata

### Configuration

Key environment variables (see [`replay-service/.env.example`](replay-service/.env.example)):

- `POSTGRES_HOST=postgres` - PostgreSQL host
- `POSTGRES_DB=ml_observability` - Database name
- `INFERENCE_API_URL=http://inference-api:8001` - Inference API endpoint
- `MAX_BATCH_SIZE=50` - Maximum events per replay request

For comprehensive documentation, see [Replay Service README](replay-service/README.md).

## Project Structure

```text
ml-observability-platform/
├── data-generator/       # Synthetic event generator
├── inference-api/        # ML inference service
├── drift-service/        # Real-time drift detection
├── observer-engine/      # (Future) Advanced observability
├── replay-service/       # (Future) Event replay
├── infra/                # Infrastructure configuration
│   ├── podman-compose.yml
│   ├── prometheus.yml
│   └── grafana/
├── schemas/              # Event schemas
└── docs/                 # Documentation
```

## Services Overview

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| Redis | 6379 | Event streaming backbone | ✅ Running |
| PostgreSQL | 5432 | Event persistence | ✅ Running |
| Prometheus | 9090 | Metrics collection | ✅ Running |
| Grafana | 3000 | Visualization | ✅ Running |
| Alertmanager | 9093 | Alert routing | ✅ Running |
| Webhook Receiver | 5001 | Alert notifications | ✅ Running |
| Inference API | 8001 | ML predictions | ✅ Running |
| Drift Service | 8000 | Drift detection | ✅ Running |
| Replay Service | 8002 | Event replay | ✅ Running |

## Documentation Index

### Phase Documentation
- [`docs/PHASE_1.md`](docs/PHASE_1.md) — Infrastructure setup
- [`docs/PHASE_2.md`](docs/PHASE_2.md) — Data generator implementation
- [`docs/PHASE_4.md`](docs/PHASE_4.md) — Drift detection service
- [`docs/PHASE_5.md`](docs/PHASE_5.md) — Monitoring and alerting system

### Service Documentation
- [`data-generator/README.md`](data-generator/README.md) — Data generator service
- [`inference-api/README.md`](inference-api/README.md) — Inference API service
- [`drift-service/README.md`](drift-service/README.md) — Drift detection service

### Architecture & Specifications
- [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md) — Full phased build workflow
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — Key technical decisions

## Stop the Platform

```bash
cd infra
podman-compose down
```

## License

See [LICENSE](LICENSE).
