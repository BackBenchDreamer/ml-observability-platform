# Phase 5: Monitoring and Alerting System

**Status**: ✅ COMPLETED  
**Date**: 2026-04-28

## Overview

Phase 5 transformed the ML observability platform from passive monitoring into an active alerting system with automated notifications. This phase focused on implementing Prometheus alert rules, Alertmanager for alert routing, webhook receivers for notifications, and comprehensive Grafana dashboards for visualization.

## Objective

Build a complete monitoring and alerting pipeline that:
- Evaluates alert conditions based on drift metrics
- Routes alerts through Alertmanager
- Delivers notifications via webhook receiver
- Provides pre-built Grafana dashboards for visualization
- Enables proactive incident response

## What Was Implemented

### 1. Prometheus Alert Rules

**File**: [`infra/alerts.yml`](../infra/alerts.yml)

Three critical alert rules for ML observability:

#### HighDriftScore
- **Condition**: `ml_drift_score > 0.2` for 2 minutes
- **Severity**: warning
- **Purpose**: Detects significant data drift in ML features
- **Action**: Triggers investigation of data quality issues

#### PredictionThroughputDrop
- **Condition**: `rate(ml_predictions_total[1m]) == 0` for 2 minutes
- **Severity**: critical
- **Purpose**: Detects complete prediction service failure
- **Action**: Immediate investigation required

#### HighInferenceLatency
- **Condition**: P95 latency > 1 second for 2 minutes
- **Severity**: warning
- **Purpose**: Detects performance degradation
- **Action**: Investigate resource constraints or model issues

### 2. Alertmanager Configuration

**File**: [`infra/alertmanager.yml`](../infra/alertmanager.yml)

**Key Features**:
- Alert grouping by severity and service
- Webhook receiver integration
- Configurable notification channels
- Alert deduplication
- Silence management

**Configuration**:
- Route: All alerts to webhook receiver
- Group by: `alertname`, `severity`
- Group wait: 10 seconds
- Group interval: 10 seconds
- Repeat interval: 1 hour

### 3. Webhook Receiver

**File**: [`infra/webhook_receiver.py`](../infra/webhook_receiver.py)

**Purpose**: Receives and logs alert notifications from Alertmanager

**Key Features**:
- FastAPI-based webhook endpoint
- JSON alert payload parsing
- Structured logging of alerts
- Health check endpoint
- Extensible for integration with:
  - Slack
  - Email
  - PagerDuty
  - Custom notification systems

**Endpoints**:
- `POST /webhook` - Receives alerts from Alertmanager
- `GET /health` - Health check

### 4. Grafana Dashboards

Three pre-configured dashboards for comprehensive monitoring:

#### ML Drift Monitoring Dashboard
**File**: [`infra/grafana/provisioning/dashboards/drift-monitoring.json`](../infra/grafana/provisioning/dashboards/drift-monitoring.json)

**URL**: http://localhost:3000/d/ml-drift-monitor

**Panels**:
- Real-time drift scores per feature
- Drift detection events over time
- PSI (Population Stability Index) scores
- KS test statistics and p-values
- Alert firing status

**Use Cases**:
- Monitor data quality in real-time
- Identify which features are drifting
- Track drift severity trends
- Correlate drift with model performance

#### Prediction Distribution Dashboard
**File**: [`infra/grafana/provisioning/dashboards/prediction-distribution.json`](../infra/grafana/provisioning/dashboards/prediction-distribution.json)

**URL**: http://localhost:3000/d/prediction-dist

**Panels**:
- Prediction label distribution
- Prediction confidence scores
- Prediction rate over time
- Label balance trends
- Prediction drift indicators

**Use Cases**:
- Monitor prediction patterns
- Detect concept drift
- Track model behavior changes
- Identify prediction bias

#### System Health Dashboard
**File**: [`infra/grafana/provisioning/dashboards/system-health.json`](../infra/grafana/provisioning/dashboards/system-health.json)

**URL**: http://localhost:3000/d/system-health

**Panels**:
- Service health status
- Inference latency (P50, P95, P99)
- Prediction throughput
- Event processing rate
- Alert firing frequency
- Resource utilization

**Use Cases**:
- Monitor overall system health
- Track performance metrics
- Identify bottlenecks
- Capacity planning

## Architecture

### Alert Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Alert Pipeline Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐                                                │
│  │ Drift Service│                                                │
│  │   :8000      │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         │ /metrics (every 15s)                                   │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │  Prometheus  │                                                │
│  │   :9090      │                                                │
│  │              │                                                │
│  │ ┌──────────┐ │                                                │
│  │ │  Alert   │ │                                                │
│  │ │  Rules   │ │ Evaluate every 15s:                           │
│  │ │          │ │ - HighDriftScore                              │
│  │ │          │ │ - PredictionThroughputDrop                    │
│  │ │          │ │ - HighInferenceLatency                        │
│  │ └──────────┘ │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         │ Alert fires                                            │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │ Alertmanager │                                                │
│  │   :9093      │                                                │
│  │              │                                                │
│  │ ┌──────────┐ │                                                │
│  │ │ Grouping │ │ - Group by severity                           │
│  │ │ Routing  │ │ - Deduplicate                                 │
│  │ │ Silencing│ │ - Route to receivers                          │
│  │ └──────────┘ │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         │ POST /webhook                                          │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │   Webhook    │                                                │
│  │   Receiver   │                                                │
│  │   :5001      │                                                │
│  │              │                                                │
│  │ ┌──────────┐ │                                                │
│  │ │  Log     │ │ - Parse alert payload                         │
│  │ │  Alert   │ │ - Log to stdout                               │
│  │ │  Details │ │ - (Future: Slack, Email, PagerDuty)          │
│  │ └──────────┘ │                                                │
│  └──────────────┘                                                │
│                                                                   │
│  ┌──────────────┐                                                │
│  │   Grafana    │                                                │
│  │   :3000      │                                                │
│  │              │                                                │
│  │ Dashboards:  │                                                │
│  │ - Drift Monitoring                                            │
│  │ - Prediction Distribution                                     │
│  │ - System Health                                               │
│  └──────────────┘                                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Metrics Collection
   ├─ Drift service exposes /metrics endpoint
   ├─ Prometheus scrapes metrics every 15 seconds
   └─ Metrics stored in time-series database

2. Alert Evaluation
   ├─ Prometheus evaluates alert rules every 15 seconds
   ├─ Compares metrics against thresholds
   └─ Fires alerts when conditions met for duration

3. Alert Routing
   ├─ Alertmanager receives fired alerts
   ├─ Groups alerts by severity and service
   ├─ Deduplicates identical alerts
   └─ Routes to configured receivers

4. Notification Delivery
   ├─ Webhook receiver receives POST request
   ├─ Parses alert payload
   ├─ Logs alert details
   └─ (Future: Send to Slack, Email, PagerDuty)

5. Visualization
   ├─ Grafana queries Prometheus
   ├─ Displays metrics in dashboards
   ├─ Shows alert status
   └─ Enables drill-down analysis
```

## Alert Rules Details

### HighDriftScore Alert

**Purpose**: Detect significant data drift in ML features

**Trigger Condition**:
```yaml
expr: ml_drift_score > 0.2
for: 2m
```

**Meaning**:
- PSI score exceeds 0.2 (industry threshold for significant drift)
- Condition persists for 2 minutes (avoids false positives)

**When It Fires**:
- Feature distributions shift significantly from baseline
- Data quality issues in production
- Upstream data pipeline changes

**Response Actions**:
1. Check data-generator drift mode status
2. Investigate upstream data sources
3. Review recent data pipeline changes
4. Consider model retraining if drift persists

**Example Alert Payload**:
```json
{
  "status": "firing",
  "labels": {
    "alertname": "HighDriftScore",
    "severity": "warning",
    "feature": "feature_1"
  },
  "annotations": {
    "summary": "High drift score detected",
    "description": "Drift score for feature_1 is 0.25"
  }
}
```

### PredictionThroughputDrop Alert

**Purpose**: Detect complete prediction service failure

**Trigger Condition**:
```yaml
expr: rate(ml_predictions_total[1m]) == 0
for: 2m
```

**Meaning**:
- No predictions made in the last minute
- Condition persists for 2 minutes

**When It Fires**:
- Inference API is down
- Data generator stopped
- Network connectivity issues
- Service crash or hang

**Response Actions**:
1. Check inference API health: `curl http://localhost:8001/health`
2. Check data generator status
3. Review service logs: `podman logs -f ml-obs-inference-api`
4. Restart services if necessary

**Example Alert Payload**:
```json
{
  "status": "firing",
  "labels": {
    "alertname": "PredictionThroughputDrop",
    "severity": "critical"
  },
  "annotations": {
    "summary": "Prediction throughput dropped to zero",
    "description": "No predictions in the last 2 minutes"
  }
}
```

### HighInferenceLatency Alert

**Purpose**: Detect performance degradation in inference service

**Trigger Condition**:
```yaml
expr: histogram_quantile(0.95, rate(ml_inference_latency_seconds_bucket[5m])) > 1
for: 2m
```

**Meaning**:
- 95th percentile latency exceeds 1 second
- Condition persists for 2 minutes

**When It Fires**:
- Model inference is slow
- Resource constraints (CPU, memory)
- Network latency issues
- Database connection problems

**Response Actions**:
1. Check system resources: CPU, memory usage
2. Review inference API logs
3. Check database connection pool
4. Consider scaling inference service

**Example Alert Payload**:
```json
{
  "status": "firing",
  "labels": {
    "alertname": "HighInferenceLatency",
    "severity": "warning"
  },
  "annotations": {
    "summary": "High inference latency detected",
    "description": "P95 latency is 1.2 seconds"
  }
}
```

## Testing the Alerting System

### Prerequisites

Start all services:
```bash
cd infra
podman-compose up -d
```

Verify all services are healthy:
```bash
podman-compose ps
```

### Test 1: Trigger HighDriftScore Alert

**Step 1: Generate baseline events**:
```bash
cd data-generator
python3 generator.py
# Let run for 30 seconds, then Ctrl+C
```

**Step 2: Enable drift mode**:
```bash
ENABLE_DRIFT=true python3 generator.py
# Let run for 2+ minutes
```

**Step 3: Check Prometheus alerts**:
- Open http://localhost:9090/alerts
- Look for `HighDriftScore` alert in "Firing" state

**Step 4: Check Alertmanager**:
- Open http://localhost:9093
- View active alerts and grouping

**Step 5: Check webhook logs**:
```bash
podman logs -f webhook-receiver
```

Expected output:
```
INFO: Received alert: HighDriftScore
INFO: Alert status: firing
INFO: Severity: warning
INFO: Description: Drift score for feature_1 is 0.25
```

### Test 2: Trigger PredictionThroughputDrop Alert

**Step 1: Start data generator**:
```bash
cd data-generator
python3 generator.py
```

**Step 2: Stop data generator**:
```bash
# Press Ctrl+C to stop
```

**Step 3: Wait 2+ minutes**:
```bash
# Alert will fire after 2 minutes of zero throughput
```

**Step 4: Check alerts**:
- Prometheus: http://localhost:9090/alerts
- Alertmanager: http://localhost:9093
- Webhook logs: `podman logs -f webhook-receiver`

### Test 3: View Grafana Dashboards

**Access Grafana**:
- URL: http://localhost:3000
- Login: admin/admin

**View Dashboards**:
1. **ML Drift Monitoring**: http://localhost:3000/d/ml-drift-monitor
   - Check drift scores
   - View alert status
   - Analyze drift trends

2. **Prediction Distribution**: http://localhost:3000/d/prediction-dist
   - Monitor prediction patterns
   - Check label distribution
   - Track prediction rate

3. **System Health**: http://localhost:3000/d/system-health
   - View service health
   - Check latency metrics
   - Monitor throughput

## Configuration

### Prometheus Alert Rules

**File**: `infra/alerts.yml`

**Customize thresholds**:
```yaml
# More sensitive drift detection
- alert: HighDriftScore
  expr: ml_drift_score > 0.15  # Lower threshold
  for: 1m                       # Shorter duration

# Less sensitive latency alert
- alert: HighInferenceLatency
  expr: histogram_quantile(0.95, rate(ml_inference_latency_seconds_bucket[5m])) > 2
  for: 5m                       # Longer duration
```

### Alertmanager Configuration

**File**: `infra/alertmanager.yml`

**Add Slack notifications**:
```yaml
receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://webhook-receiver:5001/webhook'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#ml-alerts'
        title: 'ML Observability Alert'
```

**Add email notifications**:
```yaml
receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://webhook-receiver:5001/webhook'
    email_configs:
      - to: 'team@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
```

### Webhook Receiver

**File**: `infra/webhook_receiver.py`

**Extend for Slack integration**:
```python
import requests

def send_to_slack(alert):
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    payload = {
        'text': f"Alert: {alert['labels']['alertname']}",
        'attachments': [{
            'color': 'danger' if alert['labels']['severity'] == 'critical' else 'warning',
            'fields': [
                {'title': 'Status', 'value': alert['status'], 'short': True},
                {'title': 'Severity', 'value': alert['labels']['severity'], 'short': True}
            ]
        }]
    }
    requests.post(webhook_url, json=payload)
```

## Monitoring

### Prometheus Queries

**Check alert status**:
```promql
ALERTS{alertname="HighDriftScore"}
```

**Alert firing rate**:
```promql
rate(ALERTS{alertstate="firing"}[5m])
```

**Drift score trends**:
```promql
ml_drift_score
```

**Prediction throughput**:
```promql
rate(ml_predictions_total[1m])
```

**Inference latency P95**:
```promql
histogram_quantile(0.95, rate(ml_inference_latency_seconds_bucket[5m]))
```

### Service Health Checks

**Prometheus**:
```bash
curl http://localhost:9090/-/healthy
```

**Alertmanager**:
```bash
curl http://localhost:9093/-/healthy
```

**Webhook receiver**:
```bash
curl http://localhost:5001/health
```

**Grafana**:
```bash
curl http://localhost:3000/api/health
```

### View Logs

**Prometheus**:
```bash
podman logs -f ml-obs-prometheus
```

**Alertmanager**:
```bash
podman logs -f ml-obs-alertmanager
```

**Webhook receiver**:
```bash
podman logs -f webhook-receiver
```

**Grafana**:
```bash
podman logs -f ml-obs-grafana
```

## Troubleshooting

### Issue 1: Alerts Not Firing

**Symptoms**: No alerts in Prometheus or Alertmanager

**Diagnosis**:
1. Check if Prometheus is scraping drift-service:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Verify metrics are available:
   ```bash
   curl http://localhost:8000/metrics | grep ml_drift_score
   ```

3. Check alert rule syntax:
   ```bash
   podman logs ml-obs-prometheus | grep -i error
   ```

**Solutions**:
- Ensure drift-service is running and healthy
- Verify Prometheus scrape configuration
- Check alert rule syntax in `alerts.yml`
- Restart Prometheus: `podman-compose restart prometheus`

### Issue 2: Webhook Not Receiving Alerts

**Symptoms**: Alerts firing but webhook receiver not logging

**Diagnosis**:
1. Check Alertmanager configuration:
   ```bash
   curl http://localhost:9093/api/v1/status
   ```

2. Verify webhook receiver is running:
   ```bash
   curl http://localhost:5001/health
   ```

3. Check Alertmanager logs:
   ```bash
   podman logs ml-obs-alertmanager
   ```

**Solutions**:
- Verify webhook URL in `alertmanager.yml`
- Ensure webhook receiver is accessible from Alertmanager
- Check network connectivity between containers
- Restart Alertmanager: `podman-compose restart alertmanager`

### Issue 3: Grafana Dashboards Not Loading

**Symptoms**: Dashboards show "No data" or fail to load

**Diagnosis**:
1. Check Prometheus datasource:
   - Grafana → Configuration → Data Sources
   - Test connection to Prometheus

2. Verify Prometheus has data:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=ml_drift_score'
   ```

3. Check Grafana logs:
   ```bash
   podman logs ml-obs-grafana
   ```

**Solutions**:
- Verify Prometheus datasource URL: `http://prometheus:9090`
- Ensure metrics are being collected
- Check dashboard JSON syntax
- Restart Grafana: `podman-compose restart grafana`

### Issue 4: Services Not Starting

**Symptoms**: Podman compose fails to start services

**Diagnosis**:
```bash
podman-compose ps
podman-compose logs
```

**Solutions**:
- Check port conflicts: `lsof -i :9090,9093,5001`
- Verify volume permissions
- Check container logs for errors
- Restart Podman machine: `podman machine restart`

## Performance

### Resource Usage

- **Prometheus**: ~200-300 MB memory, <5% CPU
- **Alertmanager**: ~50-100 MB memory, <2% CPU
- **Webhook Receiver**: ~30-50 MB memory, <1% CPU
- **Grafana**: ~150-200 MB memory, <5% CPU

### Optimization Tips

1. **Reduce scrape frequency** for lower resource usage:
   ```yaml
   scrape_interval: 30s  # Instead of 15s
   ```

2. **Adjust alert evaluation interval**:
   ```yaml
   evaluation_interval: 30s  # Instead of 15s
   ```

3. **Limit Prometheus retention**:
   ```yaml
   --storage.tsdb.retention.time=7d  # Instead of 15d
   ```

4. **Optimize Grafana refresh rate**:
   - Dashboard settings → Time options → Refresh: 30s

## Technical Decisions

### Why Prometheus for Alerting?

- **Native integration**: Built-in alert evaluation
- **PromQL**: Powerful query language for complex conditions
- **Time-series aware**: Understands metric trends
- **Industry standard**: Widely adopted and supported

### Why Alertmanager?

- **Separation of concerns**: Decouples alerting from monitoring
- **Advanced routing**: Flexible alert routing and grouping
- **Deduplication**: Prevents alert storms
- **Silence management**: Temporary alert suppression

### Why Webhook Receiver?

- **Flexibility**: Easy to extend for any notification system
- **Simplicity**: Minimal dependencies
- **Debugging**: Logs all alerts for troubleshooting
- **Extensibility**: Foundation for Slack, email, PagerDuty

### Why Pre-built Grafana Dashboards?

- **Immediate value**: No manual dashboard creation
- **Best practices**: Industry-standard visualizations
- **Consistency**: Standardized monitoring across teams
- **Onboarding**: Faster team adoption

## Lessons Learned

1. **Alert thresholds matter**: Too sensitive = alert fatigue, too lenient = missed issues
2. **Alert duration is critical**: Prevents false positives from transient spikes
3. **Grouping reduces noise**: Group related alerts to avoid overwhelming teams
4. **Webhook logging is essential**: Enables debugging of alert delivery
5. **Pre-built dashboards accelerate adoption**: Teams can start monitoring immediately
6. **Health checks are crucial**: Ensure monitoring system itself is healthy

## Future Enhancements

### Short-term

1. **Slack Integration**:
   - Direct Slack notifications
   - Rich message formatting
   - Alert acknowledgment

2. **Email Notifications**:
   - SMTP integration
   - HTML email templates
   - Alert digest emails

3. **PagerDuty Integration**:
   - Incident creation
   - On-call routing
   - Escalation policies

### Long-term

1. **Advanced Alert Rules**:
   - Anomaly detection alerts
   - Predictive alerts (forecast drift)
   - Multi-metric composite alerts

2. **Alert Analytics**:
   - Alert frequency analysis
   - Mean time to resolution (MTTR)
   - Alert effectiveness metrics

3. **Automated Remediation**:
   - Auto-scaling on high latency
   - Automatic model rollback on drift
   - Self-healing workflows

4. **Custom Dashboards**:
   - Team-specific dashboards
   - Executive summary dashboards
   - Cost monitoring dashboards

## Files Created/Modified

### Created

- `infra/alerts.yml` - Prometheus alert rules
- `infra/alertmanager.yml` - Alertmanager configuration
- `infra/webhook_receiver.py` - Webhook receiver implementation
- `infra/webhook_requirements.txt` - Webhook receiver dependencies
- `infra/Dockerfile.webhook` - Webhook receiver container
- `infra/grafana/provisioning/dashboards/drift-monitoring.json` - Drift monitoring dashboard
- `infra/grafana/provisioning/dashboards/prediction-distribution.json` - Prediction distribution dashboard
- `infra/grafana/provisioning/dashboards/system-health.json` - System health dashboard
- `infra/grafana/provisioning/dashboards/dashboards.yml` - Dashboard provisioning config
- `docs/PHASE_5.md` - This document

### Modified

- `infra/podman-compose.yml` - Added Alertmanager and webhook receiver services
- `infra/prometheus.yml` - Added alert rules file configuration
- `README.md` - Updated with Phase 5 completion status

## Verification Checklist

- [x] Prometheus alert rules configured
- [x] Alertmanager service running
- [x] Webhook receiver service running
- [x] Alerts fire on drift detection
- [x] Alerts fire on throughput drop
- [x] Alerts fire on high latency
- [x] Alertmanager receives alerts
- [x] Webhook receiver logs alerts
- [x] Grafana dashboards provisioned
- [x] ML Drift Monitoring dashboard functional
- [x] Prediction Distribution dashboard functional
- [x] System Health dashboard functional
- [x] All services integrated in Podman Compose
- [x] Health checks pass for all services
- [x] Documentation complete

## Related Documentation

- [Phase 1 Documentation](PHASE_1.md) - Infrastructure setup
- [Phase 2 Documentation](PHASE_2.md) - Data generator
- [Phase 4 Documentation](PHASE_4.md) - Drift detection service
- [Drift Service README](../drift-service/README.md) - Drift service details
- [Build Specification](BUILD_SPEC.md) - Complete build workflow
- [Architecture](ARCHITECTURE.md) - System architecture

---

**Phase 5 Complete** ✅  
**ML Observability Platform with Active Alerting** 🚀

**Made with Bob** 🤖