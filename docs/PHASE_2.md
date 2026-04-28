# Phase 2: Data Generator Service

**Status**: ✅ COMPLETED  
**Date**: 2026-04-28

## Overview

Phase 2 implemented the data-generator service for the ML observability platform. This phase focused on producing synthetic, schema-compliant ML inference events, simulating feature drift, and publishing events into Redis Streams for downstream observability and drift detection components.

## What Was Implemented

### Service Delivered

1. **Data Generator Service**
   - Synthetic event generator written in Python
   - Normal distribution-based feature generation
   - Drift simulation through configurable mean shift
   - Redis Streams publishing to `ml-events`
   - Schema-compliant event emission
   - Configurable runtime via environment variables

### Files Created

1. **`data-generator/generator.py`**
   - Core event generation logic
   - Synthetic feature construction
   - Drift toggle support
   - Redis Streams integration
   - Event payload assembly

2. **`data-generator/requirements.txt`**
   - Python dependencies for Redis integration and runtime support

3. **`data-generator/Dockerfile`**
   - Containerized execution for the generator service
   - Lightweight Python image setup
   - Ready for Podman/Docker-based workflows

4. **`data-generator/.env.example`**
   - Example environment configuration
   - Documents drift and Redis connection settings

5. **`data-generator/README.md`**
   - Service-specific setup and execution guide
   - Drift testing and verification instructions

6. **`docs/PHASE_2.md`**
   - This document

## Architecture Details

### Role in the Platform

The data generator acts as the first active producer in the platform. It creates ML inference-like events and publishes them into Redis Streams, allowing later services to consume, analyze, persist, and visualize the data.

### Data Flow

```text
Data Generator → Redis Stream (ml-events) → Observer Engine → Prometheus/Grafana
                                 ↓
                           Replay/Persistence
```

### Event Characteristics

Each generated event follows the shared schema and contains:

- **Schema version** for compatibility
- **Unique request ID** for traceability
- **Timestamp** for time-series analysis
- **Model version** metadata
- **Synthetic features** suitable for drift simulation
- **Prediction payload** with label and confidence
- **Operational metadata** such as latency and environment info

## Generator Design

### Synthetic Feature Generation

The generator creates numerical features using a normal distribution so that baseline and drifted distributions are easy to compare in downstream phases.

**Baseline behavior**:
- Features are centered around the default mean
- Values simulate stable production input characteristics

**Drift behavior**:
- Drift is enabled via environment configuration
- Mean shifts from `0` to `5`
- Downstream consumers can detect changes in distribution over time

### Drift Toggle Mechanism

Drift simulation is intentionally simple and explicit:

- **Drift disabled**: events use baseline mean
- **Drift enabled**: events use shifted mean
- Supports deterministic testing of drift detection logic in later phases

This allows the platform to be tested in both stable and abnormal conditions without requiring external data sources.

### Redis Streams Integration

The service publishes events to:

- **Stream name**: `ml-events`

Redis Streams was chosen because it supports:

- Ordered event ingestion
- Persistent stream entries
- Consumer groups for downstream processors
- Simple local development workflows

## Testing and Validation

### Generator Execution Test

The generator was executed successfully to confirm:

- Python dependencies install correctly
- The service starts without runtime errors
- Events are emitted continuously
- Redis accepts published stream entries

Example run:

```bash
cd data-generator
python generator.py
```

### Drift Mode Validation

Drift mode was verified by running the generator with drift enabled:

```bash
cd data-generator
ENABLE_DRIFT=true python generator.py
```

Validation goals:
- Generator still emits valid events
- Feature values reflect shifted mean distribution
- Events continue publishing to Redis successfully

### Redis Verification

Redis stream integration was verified using stream inspection commands:

```bash
podman exec ml-obs-redis redis-cli XLEN ml-events
podman exec ml-obs-redis redis-cli XREAD COUNT 1 STREAMS ml-events 0
```

Expected outcomes:
- `XLEN` returns a positive event count
- `XREAD` returns one or more valid stream entries
- Published payloads conform to the platform event schema

### Schema Compliance Verification

Generated events were verified to include the core required fields:

- `schema_version`
- `request_id`
- `timestamp`
- `model_version`
- `features`
- `prediction`
- `metadata`

This ensures downstream services can rely on a consistent contract.

## How to Run

### Prerequisites

- Phase 1 infrastructure running
- Python 3 installed locally, or Podman/Docker for containerized execution
- Redis available at the configured host and port

### Local Python Execution

1. Navigate to the service directory:
   ```bash
   cd data-generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment file if needed:
   ```bash
   cp .env.example .env
   ```

4. Run the generator:
   ```bash
   python generator.py
   ```

### Run with Drift Enabled

```bash
cd data-generator
ENABLE_DRIFT=true python generator.py
```

### Container Execution

Build the image:

```bash
cd data-generator
podman build -t data-generator .
```

Run the container:

```bash
podman run --rm --env-file .env data-generator
```

## Configuration

Typical runtime configuration includes:

- **Redis host**: target Redis instance hostname
- **Redis port**: target Redis port
- **Stream name**: defaults to `ml-events`
- **Drift toggle**: enable or disable shifted distribution generation
- **Generation interval**: controls event emission pace

See [`data-generator/.env.example`](../data-generator/.env.example) for the full example configuration.

## Technical Decisions

### Why Synthetic Data?

- No dependency on external datasets
- Fast iteration during development
- Predictable distributions for testing
- Easy drift simulation for observability workflows

### Why Normal Distribution?

- Simple and well-understood statistical behavior
- Easy baseline vs drift comparison
- Useful for later drift detection algorithms

### Why a Mean Shift of 0 → 5?

- Clear, intentional drift signal
- Large enough to be observable
- Simple to explain and validate during testing

### Why Redis Streams for Publishing?

- Aligns with Phase 1 infrastructure
- Supports event-driven architecture
- Enables future consumers without changing the producer
- Simple local verification using Redis CLI

## Challenges and Solutions

### Challenge 1: Simulating Drift Reliably

**Issue**: Need a controllable and observable drift pattern for future phases.

**Solution**:
- Used a configurable drift toggle
- Implemented a deterministic mean shift approach
- Kept the simulation simple for easier downstream validation

### Challenge 2: Maintaining Schema Compliance

**Issue**: Generated events must match the shared contract used across the platform.

**Solution**:
- Structured event payloads around the shared schema
- Included all required top-level fields
- Verified output through Redis stream inspection

### Challenge 3: Supporting Multiple Execution Modes

**Issue**: The generator should run both locally and in containers.

**Solution**:
- Added a `requirements.txt` for local Python runs
- Added a `Dockerfile` for containerized execution
- Added `.env.example` for consistent configuration

## Lessons Learned

1. Synthetic generators are valuable for bootstrapping distributed systems
2. Simple drift controls are sufficient for initial observability testing
3. Shared schemas reduce integration ambiguity across phases
4. Redis Streams provides an excellent local-first event backbone
5. Service-specific documentation improves onboarding and repeatability

## Next Steps (Phase 3)

With the data generator in place, Phase 3 will implement:

1. **Inference API**
   - FastAPI service for online inference
   - Model loading and prediction handling
   - Event publication for each request

2. **Expanded Event Production**
   - Additional model versions
   - More realistic prediction payloads
   - Stronger integration with downstream services

3. **Service-to-Service Flow**
   - API emits events
   - Observer engine consumes and analyzes them
   - Metrics become visible in Prometheus and Grafana

## Files Created/Modified

### Created
- `data-generator/generator.py` - Event generator implementation
- `data-generator/requirements.txt` - Python dependencies
- `data-generator/Dockerfile` - Container build configuration
- `data-generator/.env.example` - Example runtime configuration
- `data-generator/README.md` - Service usage documentation
- `docs/PHASE_2.md` - This document

### Modified
- `README.md` - Updated for Phase 2 completion and documentation links

## Verification Checklist

- [x] Generator runs successfully
- [x] Drift mode can be enabled
- [x] Events publish to Redis Streams
- [x] Stream name is `ml-events`
- [x] Events follow the shared schema contract
- [x] Local Python execution documented
- [x] Container execution documented
- [x] Environment configuration documented
- [x] README updated for Phase 2

---

**Phase 2 Complete** ✅  
**Data Generator Ready for Phase 3** 🚀