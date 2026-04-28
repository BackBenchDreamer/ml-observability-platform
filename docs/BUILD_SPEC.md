You are a senior backend + MLOps engineer. Help me design and scaffold a **production-grade ML Observability + Drift Detection Platform** using an event-driven, microservices architecture.

This is not a toy project. Optimize for:

* Clean system design
* Observability
* Scalability (within reason)
* Developer experience (DX)
* Strict engineering discipline (Git + documentation)

---

# NON-NEGOTIABLE WORKFLOW RULES (CRITICAL)

You MUST follow this loop for EVERY phase:

### For EACH phase:

1. Implement feature (code + config)
2. Generate:

   * Clean commit message
   * Exact git commands
3. Update documentation
4. Then proceed

---

## GIT RULES (MANDATORY)

After EVERY meaningful change:

Commit format:

```
<type>: <short description>

- What was added
- Why it was added
- Key technical decisions
```

Commands:

```bash
git add .
git commit -m "..."
git push origin main
```

Rules:

* No batching features
* No skipping commits
* Every phase = at least 1 commit

---

## DOCUMENTATION RULES (MANDATORY)

After EVERY phase:

Update README.md with:

* What was implemented
* How to run
* System flow updates

Also include ONE of:

* Architecture notes
* API contract
* Design decisions

Keep it:

* Concise
* Technical
* Structured

---

# SYSTEM GOAL

Build a system that:

1. Ingests real-time ML inference events
2. Detects data drift + prediction drift
3. Exposes Prometheus metrics
4. Visualizes via Grafana
5. Triggers alerts (webhook)
6. Supports replay of historical events

---

# ARCHITECTURE (STRICT)

Microservices:

1. **data-generator**

   * Simulates production traffic
   * Generates normal distribution data
   * Has drift toggle (mean shift, null injection, skew)
   * Pushes events → Redis Streams

2. **inference-api**

   * FastAPI
   * Runs simple model (RandomForest)
   * Publishes full event → Redis

3. **observer-engine (CORE)**

   * Consumes Redis Stream
   * Computes:

     * Data drift (start with mean shift, upgrade to KS-test)
     * Prediction distribution
   * Exposes Prometheus metrics

4. **replay-service**

   * Reads stored events (PostgreSQL)
   * Replays through inference-api
   * Returns prediction comparison

5. **infra**

   * Redis
   * Prometheus
   * Grafana
   * PostgreSQL

---

# EVENT SCHEMA (STRICT CONTRACT)

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

All services MUST strictly follow schemas/event_schema.json. Do not redefine or modify schema inline.

---

# PROMETHEUS METRICS

Implement using `prometheus_client`:

* Gauge: `ml_drift_score{model_version}`
* Counter: `total_predictions`
* Histogram: `inference_latency`

Expose `/metrics` endpoint.

---

# GRAFANA

Dashboards:

* Drift score over time
* Prediction distribution
* Latency

Alert:

* Trigger when drift > threshold for X minutes
* Send webhook (Discord/Slack)

---

# DRIFT LOGIC

Phase 1 — Infra
* Podman setup
* Redis, Prometheus, Grafana, Postgres
* Health check: Grafana shows something

Phase 2 — Data Generator
* Synthetic events
* Drift toggle (mean shift)
* Push to Redis Stream

Phase 3 — Inference API
* Model inference
* Event publishing

Phase 4 — Observer Engine (Core)
* Consume stream
* Compute drift
* Expose Prometheus metrics

Phase 5 — Monitoring + Alerts
* Grafana dashboards
* Alerting (webhook)

Phase 6 — Replay System (Differentiator)
* Store events
* Replay endpoint
* Model comparison

---

# REPLAY SYSTEM

Endpoint:
POST /replay?model_version=v2

Returns:

* Old prediction
* New prediction
* Confidence difference

---

# CONTAINERIZATION (IMPORTANT: PODMAN ONLY)

DO NOT use Docker.

Use:

* `podman-compose` (preferred)
  OR
* compatible podman-compose syntax

Requirements:

* Generate `podman-compose.yml` that works with Podman
* Ensure:

  * No Docker-specific features that break Podman
  * Rootless-compatible configs
  * Proper networking

Provide run command:

```bash
podman-compose up
```

---

# INFRA REQUIREMENTS

Generate:

1. podman-compose.yml (Podman compatible)
2. prometheus.yml
3. Grafana provisioning (basic)
4. Volume persistence (Postgres, Prometheus)

---

# PROJECT STRUCTURE

ml-observability-platform/
├── data-generator/
├── inference-api/
├── observer-engine/
├── replay-service/
├── infra/
│   ├── podman-compose.yml
│   ├── prometheus.yml
│   └── grafana/
└── README.md

---

# EXECUTION STRATEGY

Phase 1: Infra (Podman + Redis + Prometheus + Grafana + Postgres)
Phase 2: Data generator + Redis stream
Phase 3: Inference API
Phase 4: Observer engine + metrics
Phase 5: Grafana dashboards + alerts
Phase 6: Replay system

---

# CONSTRAINTS

* Keep MVP minimal but real
* Use Redis Streams (not Kafka)
* Avoid UI-heavy work
* Focus on backend + infra
* Do NOT overengineer

---

# IMPORTANT

DO NOT:

* Skip commits
* Skip documentation
* Combine phases
* Jump ahead

ALWAYS:
Implement → Commit → Document → Proceed

---

# START

Begin with:
Phase 1 → Infrastructure Setup

Provide:

1. podman-compose.yml (Podman-compatible)
2. prometheus.yml
3. Instructions to run with podman-compose
4. Commit message + git commands
5. README update

If any ambiguity exists, ask before proceeding.
