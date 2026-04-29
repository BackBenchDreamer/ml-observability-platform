# Testing Guide

## Prerequisites

- Podman
- podman-compose
- python3
- curl

## Start system

```bash
cd infra
cp ..\.env.example .env
podman-compose -f podman-compose.yml up -d
podman-compose -f podman-compose.yml ps
```

## Health checks

```bash
curl http://localhost:8001/health
curl http://localhost:8000/health
curl http://localhost:8002/health
curl http://localhost:5001/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

## Baseline + drift validation

```bash
cd data-generator
REDIS_HOST=localhost python3 generator.py
```

Run for baseline collection, then stop and run drift mode:

```bash
cd data-generator
REDIS_HOST=localhost ENABLE_DRIFT=true python3 generator.py
```

Check drift metrics:

```bash
curl http://localhost:8000/metrics
```

Key metrics:
- `ml_drift_score`
- `drift_detected_total`
- `drift_psi_score`
- `drift_ks_statistic`

## Alert pipeline validation

```bash
curl http://localhost:9090/alerts
podman-compose -f infra/podman-compose.yml logs webhook-receiver
```

Expected behavior:
- Drift alerts appear in Prometheus/Alertmanager.
- Webhook receiver logs alert payloads.

## Replay validation

```bash
curl -X POST "http://localhost:8002/replay?limit=10"
curl -X POST "http://localhost:8002/replay?model_version=v1.0.0&limit=20"
```

Expected response fields:
- `replayed_count`
- `comparisons[].old_prediction`
- `comparisons[].new_prediction`
- `comparisons[].confidence_diff`

## Failure checks

Use targeted restarts to validate recovery:

```bash
podman-compose -f infra/podman-compose.yml restart redis
podman-compose -f infra/podman-compose.yml restart postgres
podman-compose -f infra/podman-compose.yml restart inference-api
podman-compose -f infra/podman-compose.yml restart drift-service
```

After each restart:
- confirm `/health` endpoints recover
- verify event processing and replay still work

## Demo

```bash
./scripts/demo.sh
```

## Stop system

```bash
cd infra
podman-compose -f podman-compose.yml down
```
