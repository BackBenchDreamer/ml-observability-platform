#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
source "$ROOT_DIR/scripts/runtime.sh"

echo "[STEP] Checking prerequisites"
command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl not found"; exit 1; }
echo "[STEP] Using runtime: $CONTAINER_RUNTIME ($COMPOSE_CMD, $COMPOSE_FILE)"

echo "[STEP] Starting platform"
if [[ ! -f "$INFRA_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$INFRA_DIR/.env"
fi
$COMPOSE_CMD -f "$INFRA_DIR/$COMPOSE_FILE" down >/dev/null 2>&1 || true
$COMPOSE_CMD -f "$INFRA_DIR/$COMPOSE_FILE" up -d

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

echo "[STEP] Redis stream depth"
$EXEC_CMD exec ml-obs-redis redis-cli XLEN ml-events || true

echo "[STEP] Replay check"
curl -s -X POST "http://localhost:8002/replay?limit=5" | python3 -m json.tool || true

echo "[DONE] Demo complete"
echo "Grafana: http://localhost:3000"
echo "Prometheus: http://localhost:9090"
echo "Alertmanager: http://localhost:9093"
