# Phase 1: Infrastructure Setup

**Status**: ✅ COMPLETED  
**Date**: 2026-04-28

## Overview

Phase 1 established the foundational infrastructure for the ML observability platform. This phase focused on deploying and configuring the core services required for event streaming, persistence, metrics collection, and visualization.

## What Was Implemented

### Services Deployed

1. **Redis (7-alpine)**
   - Event streaming backbone using Redis Streams
   - Port: 6379
   - Health check: `redis-cli ping`
   - Persistent volume: `redis-data`

2. **PostgreSQL (15-alpine)**
   - Event storage and persistence for replay capability
   - Port: 5432
   - Database: `mlobs`
   - User: `mlobs` / Password: `mlobs_pass`
   - Health check: `pg_isready`
   - Persistent volume: `postgres-data`

3. **Prometheus (latest)**
   - Metrics collection and time-series storage
   - Port: 9090
   - Scrape interval: 15s
   - Health check: HTTP endpoint
   - Persistent volume: `prometheus-data`

4. **Grafana (latest)**
   - Visualization and alerting UI
   - Port: 3000
   - Default credentials: admin/admin
   - Health check: HTTP endpoint
   - Persistent volume: `grafana-data`
   - Auto-provisioned Prometheus datasource

### Configuration Files Created

1. **`infra/podman-compose.yml`**
   - Podman-compatible orchestration
   - All services with health checks
   - Persistent volumes for data retention
   - Isolated network (`ml-obs-network`)
   - Rootless-compatible configuration

2. **`infra/prometheus.yml`**
   - Prometheus scrape configuration
   - Global scrape interval: 15s
   - Evaluation interval: 15s
   - Ready for future service targets

3. **`infra/grafana/provisioning/datasources/prometheus.yml`**
   - Auto-provisioned Prometheus datasource
   - No manual configuration required
   - Immediate dashboard creation capability

4. **`schemas/event_schema.json`**
   - Strict event contract for all services
   - Version 1.0
   - Defines structure for ML inference events

## Architecture Details

### System Architecture

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

### Network Architecture

- **Network**: `ml-obs-network` (bridge mode)
- **Isolation**: All services communicate within isolated network
- **Port Mapping**: Services exposed to host for development access
- **DNS**: Container names used for inter-service communication

### Data Flow (Future Phases)

```
Event Generator → Redis Streams → Observer Engine → Prometheus
                       ↓
                  PostgreSQL (persistence)
                       ↓
                  Replay Service
```

## Services and Their Roles

### Redis - Event Streaming Backbone

**Purpose**: Real-time event streaming using Redis Streams

**Key Features**:
- Consumer groups for multiple subscribers
- Event persistence with configurable retention
- High throughput, low latency
- Atomic operations for event publishing

**Configuration**:
- Image: `redis:7-alpine`
- Port: 6379
- Volume: `redis-data:/data`
- Health check: Every 10s with 3 retries

**Future Usage**:
- Data generator publishes events to stream
- Observer engine consumes events for drift detection
- Multiple consumers can process same stream

### PostgreSQL - Event Persistence

**Purpose**: Long-term storage for event replay and analysis

**Key Features**:
- ACID compliance for data integrity
- Efficient indexing for time-series queries
- Support for JSON data types
- Reliable backup and recovery

**Configuration**:
- Image: `postgres:15-alpine`
- Port: 5432
- Database: `mlobs`
- Volume: `postgres-data:/var/lib/postgresql/data`
- Health check: `pg_isready` every 10s

**Future Usage**:
- Store all inference events for replay
- Enable model comparison across versions
- Historical analysis and debugging

### Prometheus - Metrics Collection

**Purpose**: Time-series metrics storage and querying

**Key Features**:
- Pull-based metrics collection
- Powerful query language (PromQL)
- Built-in alerting capabilities
- Efficient storage compression

**Configuration**:
- Image: `prom/prometheus:latest`
- Port: 9090
- Scrape interval: 15s
- Volume: `prometheus-data:/prometheus`
- Config: `/etc/prometheus/prometheus.yml`

**Future Metrics**:
- `ml_drift_score`: Data drift detection scores
- `ml_predictions_total`: Total prediction count
- `ml_inference_latency_seconds`: Inference latency histogram
- `ml_feature_distribution`: Feature statistics

### Grafana - Visualization and Alerting

**Purpose**: Dashboard creation and alert management

**Key Features**:
- Rich visualization library
- Alert rule configuration
- Webhook notifications
- Auto-provisioned datasources

**Configuration**:
- Image: `grafana/grafana:latest`
- Port: 3000
- Default credentials: admin/admin
- Volume: `grafana-data:/var/lib/grafana`
- Provisioned datasource: Prometheus

**Future Dashboards**:
- Real-time drift monitoring
- Prediction distribution analysis
- Latency and throughput metrics
- Model performance comparison

## Testing and Validation

### Health Check Verification

All services were tested for health status:

```bash
podman-compose ps
```

Expected output:
```
NAME                    STATUS      PORTS
ml-obs-grafana          healthy     0.0.0.0:3000->3000/tcp
ml-obs-postgres         healthy     0.0.0.0:5432->5432/tcp
ml-obs-prometheus       healthy     0.0.0.0:9090->9090/tcp
ml-obs-redis            healthy     0.0.0.0:6379->6379/tcp
```

### Service Connectivity Tests

1. **Redis**:
   ```bash
   podman exec ml-obs-redis redis-cli ping
   # Expected: PONG
   ```

2. **PostgreSQL**:
   ```bash
   podman exec ml-obs-postgres pg_isready -U mlobs
   # Expected: accepting connections
   ```

3. **Prometheus**:
   - Access: http://localhost:9090
   - Verify: Targets page shows configuration

4. **Grafana**:
   - Access: http://localhost:3000
   - Login: admin/admin
   - Verify: Prometheus datasource auto-configured

### Volume Persistence Tests

Verified data persistence across container restarts:

```bash
# Stop services
podman-compose down

# Restart services
podman-compose up -d

# Verify data retained
podman-compose ps
```

## How to Run

### Prerequisites

- **Podman** (rootless container runtime)
- **podman-compose** (container orchestration)

Install on macOS:
```bash
brew install podman podman-compose
podman machine init
podman machine start
```

### Starting the Infrastructure

1. **Navigate to infrastructure directory**:
   ```bash
   cd infra
   ```

2. **Start all services**:
   ```bash
   podman-compose up -d
   ```

3. **Verify all services are healthy**:
   ```bash
   podman-compose ps
   ```
   
   Wait until all services show `healthy` status (may take 30-60 seconds).

4. **View logs** (optional):
   ```bash
   # All services
   podman-compose logs -f
   
   # Specific service
   podman-compose logs -f redis
   ```

### Accessing Services

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  - Change password on first login

- **Prometheus**: http://localhost:9090
  - No authentication required
  - Access metrics and targets

- **Redis**: `localhost:6379`
  - Use Redis CLI or client libraries
  - No password required (development setup)

- **PostgreSQL**: `localhost:5432`
  - Database: `mlobs`
  - Username: `mlobs`
  - Password: `mlobs_pass`

### Stopping Services

**Stop without removing volumes**:
```bash
podman-compose down
```

**Stop and remove all data**:
```bash
podman-compose down -v
```

**Restart specific service**:
```bash
podman-compose restart redis
```

## Technical Decisions

### Why Podman Over Docker?

- **Rootless containers**: Better security, no daemon running as root
- **Daemonless architecture**: No background service required
- **Docker-compatible**: Drop-in replacement for Docker CLI
- **Native systemd integration**: Better for production deployments

### Why Redis Streams?

- **Event ordering**: Guaranteed order within stream
- **Consumer groups**: Multiple consumers can process same stream
- **Persistence**: Events retained until explicitly deleted
- **Performance**: High throughput with low latency
- **Simplicity**: Easier than Kafka for this use case

### Why PostgreSQL for Event Storage?

- **ACID compliance**: Data integrity for replay
- **JSON support**: Native handling of event schema
- **Time-series optimization**: Efficient indexing for temporal queries
- **Reliability**: Battle-tested for production workloads
- **Query flexibility**: Complex analysis capabilities

### Why Prometheus + Grafana?

- **Industry standard**: Widely adopted observability stack
- **Pull-based metrics**: Services don't need to know about Prometheus
- **PromQL**: Powerful query language for metrics
- **Grafana integration**: Seamless visualization
- **Alerting**: Built-in alert manager

### Configuration Choices

1. **Health Checks**: All services have health checks for reliability
2. **Persistent Volumes**: Data survives container restarts
3. **Network Isolation**: Services communicate on dedicated network
4. **Auto-provisioning**: Grafana datasource configured automatically
5. **Alpine Images**: Smaller image sizes, faster pulls

## Event Schema Contract

The event schema (`schemas/event_schema.json`) defines the strict contract that all services must follow:

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

### Schema Design Rationale

**`schema_version`**: Enables schema evolution and backward compatibility

**`request_id`**: UUID v4 for distributed tracing and event correlation

**`timestamp`**: ISO-8601 format for:
- Temporal analysis
- Time-series aggregation
- Drift detection over time windows

**`model_version`**: Semantic versioning for:
- Model comparison
- A/B testing
- Replay with specific versions

**`features`**: Flexible object for:
- Any number of features
- Mixed data types (numeric, boolean, string)
- Drift detection input

**`prediction`**: Structured output for:
- Classification (label)
- Confidence scoring
- Prediction drift analysis

**`metadata`**: Operational metrics for:
- Performance monitoring (latency)
- Environment tracking
- Regional analysis

## Challenges and Solutions

### Challenge 1: Podman Compatibility

**Issue**: Docker Compose syntax not fully compatible with Podman

**Solution**: 
- Used `podman-compose` instead of `docker-compose`
- Avoided Docker-specific features
- Tested all configurations with Podman

### Challenge 2: Health Check Timing

**Issue**: Services starting before dependencies ready

**Solution**:
- Implemented health checks for all services
- Set appropriate intervals and retries
- Used `depends_on` with health conditions

### Challenge 3: Volume Permissions

**Issue**: Rootless Podman volume permission issues

**Solution**:
- Used named volumes instead of bind mounts
- Let Podman manage volume permissions
- Avoided host filesystem dependencies

## Lessons Learned

1. **Health checks are critical**: Don't rely on service startup alone
2. **Named volumes are simpler**: Easier than managing bind mount permissions
3. **Auto-provisioning saves time**: Grafana datasource configuration automated
4. **Test incrementally**: Start services one at a time to isolate issues
5. **Document access credentials**: Essential for team collaboration

## Next Steps (Phase 2)

With infrastructure in place, Phase 2 will implement:

1. **Data Generator Service**:
   - Synthetic event generation
   - Configurable drift injection
   - Redis Streams publishing

2. **Event Schema Validation**:
   - Ensure all events match schema
   - Reject malformed events

3. **Initial Metrics**:
   - Event generation rate
   - Schema validation errors

## Files Created/Modified

### Created
- `infra/podman-compose.yml` - Service orchestration
- `infra/prometheus.yml` - Prometheus configuration
- `infra/grafana/provisioning/datasources/prometheus.yml` - Grafana datasource
- `schemas/event_schema.json` - Event contract
- `docs/PHASE_1.md` - This document

### Modified
- `README.md` - Updated with Phase 1 completion status

## Verification Checklist

- [x] All services start successfully
- [x] All services pass health checks
- [x] Grafana accessible at http://localhost:3000
- [x] Prometheus accessible at http://localhost:9090
- [x] Redis accepts connections
- [x] PostgreSQL accepts connections
- [x] Grafana has Prometheus datasource configured
- [x] Data persists across container restarts
- [x] Services communicate on isolated network
- [x] Event schema documented and validated

---

**Phase 1 Complete** ✅  
**Infrastructure Ready for Phase 2** 🚀