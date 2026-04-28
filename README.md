# ML Observability Platform

A phased, event-driven ML observability platform for generating inference events, detecting drift, exposing metrics, and visualizing system behavior.

## Current Status

- ✅ Phase 1 complete — Infrastructure setup
- ✅ Phase 2 complete — Data generator service
- 🔄 Phase 3 next — Inference API

Detailed implementation notes are documented per phase:

- [Phase 1 Documentation](docs/PHASE_1.md)
- [Phase 2 Documentation](docs/PHASE_2.md)
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

### Start Infrastructure

```bash
cd infra
podman-compose up -d
podman-compose ps
```

Wait until all services report `healthy`.

### Access Services

- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Redis: `localhost:6379`
- PostgreSQL: `localhost:5432`

Default local development credentials:

- Grafana: `admin` / `admin`
- PostgreSQL: `mlobs` / `mlobs_pass`

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

## Project Structure

```text
ml-observability-platform/
├── data-generator/
├── observer-engine/
├── replay-service/
├── infra/
├── schemas/
└── docs/
```

## Documentation Index

- [`docs/PHASE_1.md`](docs/PHASE_1.md) — Infrastructure setup
- [`docs/PHASE_2.md`](docs/PHASE_2.md) — Data generator implementation
- [`data-generator/README.md`](data-generator/README.md) — Service-level generator usage
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
