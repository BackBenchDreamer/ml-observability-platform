# ML Observability Platform

Production-style ML observability system for streaming inference events, detecting drift, and replaying historical predictions.

## Runtime Compatibility

This platform seamlessly supports both **Docker** and **Podman** container runtimes without requiring manual configuration.

### Automatic Detection
- Runtime is automatically detected when you run any script
- No environment variables or configuration files needed
- Works with Docker Compose V2 (`docker compose`), legacy Docker Compose (`docker-compose`), and Podman Compose (`podman-compose`)

### Usage
Simply run the provided scripts - they will automatically use the correct runtime:
```bash
./scripts/demo.sh
./scripts/rebuild-all-services.sh
```

The system uses a runtime abstraction layer ([`scripts/runtime.sh`](scripts/runtime.sh)) that detects your container runtime and configures all commands accordingly.

## Quick start

Prerequisites:
- Docker or Podman
- Docker Compose or Podman Compose
- python3

```bash
cd infra
cp ..\.env.example .env
# The compose command will be auto-detected (docker compose, docker-compose, or podman-compose)
./scripts/demo.sh
```

Run end-to-end demo:

```bash
./scripts/demo.sh
```

## System flow

```text
Data Generator -> Inference API -> Redis Stream (ml-events) -> Drift Service
                                                     |              |
                                                     v              v
                                                PostgreSQL       Prometheus -> Alertmanager -> Webhook
                                                     |
                                                     v
                                                Replay Service
```

## What is implemented

- Real-time event ingestion through Redis Streams.
- Drift detection with baseline + sliding-window analysis (PSI and KS test).
- Prometheus metrics and alert rules.
- Grafana dashboards (drift, prediction distribution, system health).
- Historical replay against current inference model.

## Manual validation

```bash
# generate baseline events
cd data-generator
REDIS_HOST=localhost python3 generator.py

# generate drifted events
REDIS_HOST=localhost ENABLE_DRIFT=true python3 generator.py
```

```bash
# replay last 10 events
curl -X POST "http://localhost:8002/replay?limit=10"
```

## Core docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/API.md](docs/API.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/BUILD_SPEC.md](docs/BUILD_SPEC.md)

## Repository structure

```text
ml-observability-platform/
├── README.md
├── LICENSE
├── docs/
├── data-generator/
├── inference-api/
├── drift-service/
├── replay-service/
├── infra/
├── schemas/
└── scripts/
```

## License

GPL-3.0. See [LICENSE](LICENSE).
