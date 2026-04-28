# ML Observability Platform

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Prometheus](https://img.shields.io/badge/Prometheus-2.45+-orange.svg)
![Grafana](https://img.shields.io/badge/Grafana-10.0+-yellow.svg)

> Production-style ML observability system with real-time drift detection, event streaming, and historical replay capabilities for monitoring machine learning models in production.

## Overview

This platform provides comprehensive observability for ML systems through event-driven architecture, statistical drift detection, and automated alerting. Built with industry-standard tools (Prometheus, Grafana, Redis Streams), it demonstrates production-ready patterns for monitoring model performance, detecting data drift, and debugging ML failures through historical event replay.

**Key Features:**
- **Real-time Drift Detection** — Statistical analysis (KS test, PSI) on streaming inference events
- **Event-Driven Architecture** — Redis Streams for reliable event processing with consumer groups
- **Historical Replay** — PostgreSQL-backed event replay for debugging and model comparison
- **Comprehensive Monitoring** — Prometheus metrics, Grafana dashboards, and Alertmanager integration
- **Production Patterns** — Health checks, structured logging, containerized services with Podman

## Architecture

The platform follows a microservices architecture with event streaming at its core:

```
Data Generator → Inference API → Redis Streams → Drift Service → Prometheus
                       ↓                              ↓
                  PostgreSQL                    Alertmanager
                       ↓                              ↓
                 Replay Service                 Webhook Receiver
```

**Key Architectural Decisions:**
- **Redis Streams** for event backbone (reliable, ordered, consumer groups)
- **PostgreSQL** for event persistence (JSONB for flexible schema)
- **FastAPI** for service APIs (async, auto-documentation, type safety)
- **Prometheus** for metrics (industry standard, powerful querying)
- **Podman** for containerization (rootless, Docker-compatible)

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed design and [Technical Decisions](docs/DECISIONS.md) for rationale.

## How It Works

### 1. Prediction Flow

1. **Data Generator** creates synthetic inference requests with configurable drift
2. **Inference API** receives requests, runs RandomForest model, returns predictions
3. **Event Publishing** — API publishes prediction events to Redis Stream `ml-events`
4. **Event Persistence** — Events stored in PostgreSQL for replay capability

### 2. Drift Detection

1. **Baseline Collection** — First 100 events establish reference distributions
2. **Sliding Window Analysis** — Maintains 100-event window for comparison
3. **Statistical Testing** — Applies KS test and PSI to detect distribution shifts
4. **Alert Publishing** — Drift events published to Redis Stream `ml-alerts`
5. **Metrics Exposure** — Prometheus metrics updated for monitoring

**Drift Thresholds:**
- PSI (Population Stability Index) > 0.2
- KS test p-value < 0.05

### 3. Alerting

1. **Prometheus** scrapes metrics from drift-service every 15 seconds
2. **Alert Rules** evaluate conditions (drift score, latency, throughput)
3. **Alertmanager** receives, groups, and routes alerts
4. **Webhook Receiver** logs notifications (extensible for Slack/PagerDuty)

## Quick Start

### Prerequisites

- Podman and podman-compose
- Python 3.9+

```bash
# macOS installation
brew install podman podman-compose
podman machine init
podman machine start
```

### Run Demo

Use the automated demo script for quick validation:

```bash
./scripts/demo.sh
```

The demo script will:
1. Start all services with podman-compose
2. Wait for services to become healthy
3. Generate baseline events (30 seconds)
4. Generate drift events (30 seconds)
5. Display drift alerts and metrics
6. Show Grafana dashboard URLs

**Expected Outcomes:**
- All services report healthy status
- Drift alerts appear in Redis Stream `ml-alerts`
- Prometheus metrics show `ml_drift_score > 0.2`
- Grafana dashboards display drift detection events

See [Testing Guide](docs/TESTING.md) for detailed testing instructions and validation steps.

### Manual Start

```bash
# Start all services
cd infra
podman-compose up -d

# Verify services are healthy
podman-compose ps

# Generate events
cd ../data-generator
python3 generator.py

# Enable drift
ENABLE_DRIFT=true python3 generator.py
```

### Access Services

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Inference API**: http://localhost:8001/docs
- **Drift Service**: http://localhost:8000/metrics
- **Replay Service**: http://localhost:8002/docs

## Observability Features

### Drift Detection

**Statistical Methods:**
- **Kolmogorov-Smirnov (KS) Test** — Detects distribution shifts in continuous features
- **Population Stability Index (PSI)** — Measures distribution divergence
- **Chi-Square Test** — Monitors prediction label distribution changes

**Monitoring Approach:**
- Baseline established from first 100 events
- Sliding window of 100 events for continuous comparison
- Per-feature drift scoring with configurable thresholds
- Alert publishing to Redis Streams for downstream processing

**Metrics Exposed:**
```
drift_events_processed_total          # Total events processed
drift_detected_total{feature}         # Drift detections by feature
drift_psi_score{feature}              # PSI scores per feature
drift_ks_statistic{feature}           # KS test statistics
drift_prediction_distribution{label}  # Prediction distribution
drift_processing_latency_seconds      # Processing time histogram
```

### Monitoring Dashboards

**Grafana Dashboards** (pre-configured):

1. **ML Drift Monitoring** — Real-time drift scores, detection events, feature distributions
2. **Prediction Distribution** — Label distribution trends, confidence scores, throughput
3. **System Health** — Service health, latency percentiles, error rates, resource usage

Access at http://localhost:3000 (admin/admin)

### Alerting System

**Alert Rules:**
- `HighDriftScore` — Triggers when drift score > 0.2 for 2 minutes
- `PredictionThroughputDrop` — Triggers when prediction rate drops to 0 for 2 minutes
- `HighInferenceLatency` — Triggers when P95 latency exceeds 1 second for 2 minutes

**Alert Flow:**
```
Prometheus → Alertmanager → Webhook Receiver → [Slack/PagerDuty/Email]
```

Check active alerts:
- Prometheus: http://localhost:9090/alerts
- Alertmanager: http://localhost:9093
- Webhook logs: `podman logs -f webhook-receiver`

## Replay System

### Purpose

The replay system enables debugging of ML failures by replaying historical inference events through the current model version. This allows you to:

- **Reproduce failures** with exact historical inputs
- **Compare predictions** between model versions
- **Analyze confidence changes** to understand model behavior
- **Validate fixes** before redeployment

### How to Use

**Replay last 10 events:**
```bash
curl -X POST "http://localhost:8002/replay?limit=10"
```

**Replay events for specific model version:**
```bash
curl -X POST "http://localhost:8002/replay?model_version=v1.0.0&limit=20"
```

**Example Response:**
```json
{
  "replayed_count": 10,
  "model_version": "v1.0.0",
  "comparisons": [
    {
      "request_id": "abc-123",
      "old_prediction": {"label": 0, "confidence": 0.85},
      "new_prediction": {"label": 0, "confidence": 0.92},
      "confidence_diff": 0.07
    }
  ]
}
```

### Use Cases

- **Model Regression Testing** — Validate new model versions against historical data
- **Debugging Production Issues** — Reproduce exact conditions that caused failures
- **A/B Testing Analysis** — Compare prediction differences between model versions
- **Confidence Calibration** — Analyze how confidence scores change over time

## Documentation

### Core Documentation
- [Architecture](docs/ARCHITECTURE.md) — System design and component interactions
- [API Reference](docs/API.md) — Complete API documentation for all services
- [Testing Guide](docs/TESTING.md) — Comprehensive testing and validation procedures
- [Design Decisions](docs/DECISIONS.md) — Technical decisions and trade-offs

### Implementation Phases
- [Phase 1: Infrastructure](docs/PHASE_1.md) — Redis, PostgreSQL, Prometheus, Grafana setup
- [Phase 2: Data Generator](docs/PHASE_2.md) — Synthetic event generation with drift
- [Phase 4: Drift Detection](docs/PHASE_4.md) — Statistical drift detection implementation
- [Phase 5: Monitoring & Alerting](docs/PHASE_5.md) — Alert rules and dashboards

### Service Documentation
- [Data Generator](data-generator/README.md) — Event generation service
- [Inference API](inference-api/README.md) — ML prediction service
- [Drift Service](drift-service/README.md) — Drift detection service
- [Replay Service](replay-service/README.md) — Event replay service

### Build Specification
- [Build Spec](docs/BUILD_SPEC.md) — Complete phased build workflow

## Screenshots

### Grafana Dashboard
*[Placeholder: Screenshot of ML Drift Monitoring dashboard showing real-time drift scores, feature distributions, and detection events over time]*

### Prometheus Alerts
*[Placeholder: Screenshot of Prometheus alerts page showing configured alert rules (HighDriftScore, PredictionThroughputDrop, HighInferenceLatency) with their current states]*

### Alert Firing
*[Placeholder: Screenshot of Alertmanager showing active firing alert with details including severity, labels, and notification status]*

## Technology Stack

**Backend & APIs:**
- Python 3.9+
- FastAPI (async web framework)
- scikit-learn (ML models)

**Event Streaming:**
- Redis Streams (event backbone)
- Consumer Groups (reliable processing)

**Data Storage:**
- PostgreSQL (event persistence)
- JSONB (flexible schema)

**Monitoring & Alerting:**
- Prometheus (metrics collection)
- Grafana (visualization)
- Alertmanager (alert routing)

**Infrastructure:**
- Podman (containerization)
- podman-compose (orchestration)

## Project Structure

```
ml-observability-platform/
├── data-generator/       # Synthetic event generator with drift
├── inference-api/        # ML inference service (FastAPI)
├── drift-service/        # Real-time drift detection
├── replay-service/       # Event replay for debugging
├── infra/                # Infrastructure configuration
│   ├── podman-compose.yml
│   ├── prometheus.yml
│   ├── alerts.yml
│   ├── alertmanager.yml
│   └── grafana/          # Dashboard provisioning
├── schemas/              # Event schemas (JSON Schema)
├── scripts/              # Demo and validation scripts
└── docs/                 # Comprehensive documentation
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

## License

MIT License - See [LICENSE](LICENSE) for details.
