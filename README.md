# ML Observability Platform

A phased, event-driven ML observability platform for generating inference events, detecting drift, exposing metrics, and visualizing system behavior.

## Current Status

- ✅ Phase 1 complete — Infrastructure setup
- ✅ Phase 2 complete — Data generator service
- ✅ Phase 3 complete — Inference API
- ✅ Phase 4 complete — Drift detection service

Detailed implementation notes are documented per phase:

- [Phase 1 Documentation](docs/PHASE_1.md)
- [Phase 2 Documentation](docs/PHASE_2.md)
- [Phase 3 Documentation](inference-api/README.md)
- [Phase 4 Documentation](docs/PHASE_4.md)
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
| Inference API | 8001 | ML predictions | ✅ Running |
| Drift Service | 8000 | Drift detection | ✅ Running |

## Documentation Index

### Phase Documentation
- [`docs/PHASE_1.md`](docs/PHASE_1.md) — Infrastructure setup
- [`docs/PHASE_2.md`](docs/PHASE_2.md) — Data generator implementation
- [`docs/PHASE_4.md`](docs/PHASE_4.md) — Drift detection service

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
