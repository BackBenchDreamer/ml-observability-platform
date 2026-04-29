#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"

echo "[STEP] Checking prerequisites"
command -v podman >/dev/null 2>&1 || { echo "[ERROR] podman not found"; exit 1; }
command -v podman-compose >/dev/null 2>&1 || { echo "[ERROR] podman-compose not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl not found"; exit 1; }

echo "[STEP] Starting platform"
cd "$INFRA_DIR"
if [[ ! -f .env ]]; then
  cp "$ROOT_DIR/.env.example" .env
fi
podman-compose -f podman-compose.yml down >/dev/null 2>&1 || true
podman-compose -f podman-compose.yml up -d

echo "[STEP] Waiting for services"
sleep 30

echo "[STEP] Health checks"
curl -fsS http://localhost:8001/health >/dev/null
curl -fsS http://localhost:8000/health >/dev/null
curl -fsS http://localhost:8002/health >/dev/null
curl -fsS http://localhost:5001/health >/dev/null
curl -fsS http://localhost:9090/-/healthy >/dev/null
curl -fsS http://localhost:3000/api/health >/dev/null
echo "[OK] Services are healthy"

echo "[STEP] Generating baseline traffic (20s)"
(
  cd "$ROOT_DIR/data-generator"
  REDIS_HOST=localhost python3 generator.py &
  GEN_PID=$!
  sleep 20
  kill "$GEN_PID" >/dev/null 2>&1 || true
)

echo "[STEP] Generating drift traffic (20s)"
(
  cd "$ROOT_DIR/data-generator"
  REDIS_HOST=localhost ENABLE_DRIFT=true python3 generator.py &
  GEN_PID=$!
  sleep 20
  kill "$GEN_PID" >/dev/null 2>&1 || true
)

echo "[STEP] Drift metrics snapshot"
curl -s http://localhost:8000/metrics | grep -E "ml_drift_score|drift_detected_total|drift_psi_score" || true

echo "[STEP] Replay check"
curl -s -X POST "http://localhost:8002/replay?limit=5" | python3 -m json.tool || true

echo "[DONE] Demo complete"
echo "Grafana: http://localhost:3000"
echo "Prometheus: http://localhost:9090"
echo "Alertmanager: http://localhost:9093"
