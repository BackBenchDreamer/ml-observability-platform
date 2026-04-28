# ML Observability Platform

A production-grade ML observability and drift detection platform built with an event-driven, microservices architecture. This system ingests real-time ML inference events, detects data and prediction drift, exposes Prometheus metrics, and provides visualization through Grafana.

## Project Goals

- **Real-time Monitoring**: Ingest and analyze ML inference events in real-time
- **Drift Detection**: Detect data drift and prediction drift to maintain model quality
- **Observability**: Expose comprehensive metrics via Prometheus
- **Visualization**: Rich dashboards and alerting through Grafana
- **Replay Capability**: Support historical event replay for model comparison
- **Production-Ready**: Clean architecture, scalability, and developer experience

## Quick Start

### Prerequisites

- **Podman** (rootless container runtime)
- **podman-compose** (container orchestration)

Install on macOS:
```bash
brew install podman podman-compose
podman machine init
podman machine start
```

### Running the Platform

1. **Start all services:**
```bash
cd infra
podman-compose up -d
```

2. **Verify services are healthy:**
```bash
podman-compose ps
```

All services should show `healthy` status.

3. **Access the platform:**
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **Prometheus**: http://localhost:9090
   - **Redis**: localhost:6379
   - **PostgreSQL**: localhost:5432 (mlobs/mlobs_pass)

4. **Stop services:**
```bash
podman-compose down
```

## Project Structure

```
ml-observability-platform/
├── data-generator/          # [Phase 2] Synthetic event generator
├── observer-engine/         # [Phase 4] Core drift detection engine
├── replay-service/          # [Phase 6] Historical event replay
├── infra/                   # Infrastructure configuration
│   ├── docker-compose.yml   # Podman-compatible orchestration
│   ├── prometheus.yml       # Prometheus scrape config
│   └── grafana/
│       └── provisioning/
│           └── datasources/
│               └── prometheus.yml
├── schemas/
│   └── event_schema.json    # Strict event contract
└── docs/
    ├── PHASE_1.md           # Phase 1: Infrastructure setup
    ├── BUILD_SPEC.md        # Complete build specification
    ├── ARCHITECTURE.md      # Architecture decisions
    └── DECISIONS.md         # Technical decisions log
```

## Phase Documentation

### ✅ Phase 1: Infrastructure Setup (COMPLETED)
**[View detailed documentation →](docs/PHASE_1.md)**

Established foundational infrastructure with Redis, PostgreSQL, Prometheus, and Grafana. All services deployed with health checks, persistent volumes, and auto-provisioned configurations.

**Key Deliverables:**
- Docker Compose orchestration
- Event schema contract
- Service health monitoring
- Grafana datasource provisioning

### ✅ Phase 2: Data Generator (COMPLETED)
**[View detailed documentation →](data-generator/README.md)**

Synthetic event generator with drift simulation for testing observability pipelines.

**Key Features:**
- Normal distribution-based feature generation
- Configurable drift mode (mean shift: 0 → 5)
- Redis Streams publishing (`ml-events` stream)
- Schema-compliant event emission

**Quick Start:**
```bash
cd data-generator
python generator.py
# Enable drift: ENABLE_DRIFT=true python generator.py
```

**Verify Events:**
```bash
podman exec ml-obs-redis redis-cli XLEN ml-events
podman exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-events 0
```

See [`data-generator/README.md`](data-generator/README.md) for detailed instructions.

### 🔄 Phase 3: Inference API (PLANNED)
**Documentation:** `docs/PHASE_3.md` (to be created)

Build FastAPI service with ML model integration.

**Planned Features:**
- FastAPI REST endpoints
- RandomForest model integration
- Event publishing to Redis
- Request/response logging

### 🔄 Phase 4: Observer Engine (PLANNED)
**Documentation:** `docs/PHASE_4.md` (to be created)

Core drift detection engine consuming events from Redis.

**Planned Features:**
- Redis Streams consumer
- Drift detection algorithms (KS-test)
- Prometheus metrics exposure
- Real-time alerting

### 🔄 Phase 5: Monitoring & Alerts (PLANNED)
**Documentation:** `docs/PHASE_5.md` (to be created)

Create comprehensive dashboards and alerting rules.

**Planned Features:**
- Grafana dashboards (drift, predictions, latency)
- Alert rule configuration
- Webhook notifications
- Performance monitoring

### 🔄 Phase 6: Replay System (PLANNED)
**Documentation:** `docs/PHASE_6.md` (to be created)

Historical event replay for model comparison.

**Planned Features:**
- PostgreSQL event storage
- Replay API endpoints
- Model version comparison
- Prediction difference analysis

## Event Schema Overview

All services adhere to a strict event contract defined in `schemas/event_schema.json`:

```json
{
  "schema_version": "1.0",
  "request_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "model_version": "v1.0.0",
  "features": {
    "feature_1": 0.85,
    "feature_2": 1.2,
    "is_premium_user": true
  },
  "prediction": {
    "label": 0,
    "confidence": 0.92
  },
  "metadata": {
    "latency_ms": 45.2,
    "environment": "production",
    "region": "local"
  }
}
```

**Key Design Principles:**
- **Versioned schema**: Enables evolution and backward compatibility
- **Unique identifiers**: UUID v4 for distributed tracing
- **Temporal data**: ISO-8601 timestamps for time-series analysis
- **Model versioning**: Semantic versioning for comparison and replay
- **Flexible features**: Support for mixed data types
- **Structured predictions**: Classification labels with confidence scores
- **Operational metadata**: Performance and environment tracking

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────┐  ┌────────────┐  ┌────────────┐          │
│  │  Redis   │  │ PostgreSQL │  │ Prometheus │          │
│  │  :6379   │  │   :5432    │  │   :9090    │          │
│  └──────────┘  └────────────┘  └────────────┘          │
│       │              │                 │                 │
│       └──────────────┴─────────────────┘                │
│                      │                                   │
│                ┌─────▼──────┐                           │
│                │  Grafana   │                           │
│                │   :3000    │                           │
│                └────────────┘                           │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

**Core Services:**
- **Redis**: Event streaming via Redis Streams
- **PostgreSQL**: Event persistence and replay storage
- **Prometheus**: Metrics collection and time-series storage
- **Grafana**: Dashboards and alerting UI

## Development Workflow

This project follows strict engineering discipline:

1. **Phased Development**: Each phase is self-contained with clear deliverables
2. **Git Commits**: Every phase requires at least one commit
3. **Documentation**: Detailed phase documentation in `docs/PHASE_*.md`
4. **Testing**: Health checks and validation at each step
5. **Clean Code**: Structured, maintainable, production-ready code

### Workflow Steps

1. Complete phase implementation
2. Test all functionality
3. Create phase documentation (`docs/PHASE_X.md`)
4. Update README with phase status
5. Commit changes with descriptive message
6. Move to next phase

## Technical Stack

- **Container Runtime**: Podman (rootless, daemonless)
- **Orchestration**: podman-compose
- **Event Streaming**: Redis Streams
- **Database**: PostgreSQL 15
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Languages**: Python (future phases)
- **API Framework**: FastAPI (future phases)

## Key Technical Decisions

- **Podman over Docker**: Rootless containers for better security
- **Redis Streams**: Efficient event streaming with consumer groups
- **PostgreSQL**: Reliable persistence for event replay
- **Prometheus + Grafana**: Industry-standard observability stack
- **Event-Driven Architecture**: Decoupled microservices for scalability
- **Strict Schema Contract**: Ensures data consistency across services

For detailed technical decisions, see [DECISIONS.md](docs/DECISIONS.md).

## Contributing

This is a structured learning project following a phased approach. Each phase builds upon the previous one, ensuring a solid foundation for production-grade ML observability.

## License

See [LICENSE](LICENSE) file for details.

---

**Current Status**: Phase 2 Complete ✅
**Next Phase**: Phase 3 - Inference API
**Last Updated**: 2026-04-28
