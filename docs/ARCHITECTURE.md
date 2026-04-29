# ML Observability Platform Architecture

## Overview

The platform uses an event-driven microservice architecture for inference monitoring and drift detection.

```text
data-generator -> inference-api -> Redis stream (ml-events) -> drift-service
                                         |                         |
                                         v                         v
                                    PostgreSQL               Prometheus -> Alertmanager -> webhook-receiver
                                         |
                                         v
                                    replay-service
```

## Components

| Component | Port | Responsibility |
|---|---:|---|
| inference-api | 8001 | Serve predictions and publish schema-compliant events |
| drift-service | 8000 | Consume events, detect drift, publish alerts, expose metrics |
| replay-service | 8002 | Query historical events and compare old/new predictions |
| Redis | 6379 | Event backbone (`ml-events`, `ml-alerts`) |
| PostgreSQL | 5432 | Persist events for replay and analysis |
| Prometheus | 9090 | Scrape metrics and evaluate alert rules |
| Alertmanager | 9093 | Route alerts |
| webhook-receiver | 5001 | Receive alert notifications |
| Grafana | 3000 | Visualize drift, predictions, and health |

## Event contract

All services use `schemas/event_schema.json` (`schema_version`, `request_id`, `timestamp`, `model_version`, `features`, `prediction`, `metadata`).

## Drift detection model

- Baseline window: first 100 events.
- Sliding window: most recent 100 events.
- Feature drift criteria:
  - PSI > 0.2, or
  - KS p-value < 0.05.
- Prediction drift is also tracked from label distribution changes.

## Alerting pipeline

1. `drift-service` emits drift metrics and publishes alert events.
2. Prometheus evaluates alert rules from `infra/alerts.yml`.
3. Alertmanager routes alerts to webhook receiver.
4. Grafana dashboards visualize alert and drift behavior.

## Dashboards

Three provisioned dashboards are retained:

1. Drift monitoring
2. Prediction distribution
3. System health

## Infrastructure

- Primary orchestration file: `infra/podman-compose.yml`
- Runtime settings are env-driven via `.env` files derived from `.env.example`
