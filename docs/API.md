# API Documentation

## Overview

This document provides comprehensive API documentation for the ML Observability Platform. The system consists of four main services that expose REST APIs:

1. **Inference API** (Port 8001) - ML model predictions with event streaming
2. **Replay Service** (Port 8002) - Historical prediction comparison
3. **Webhook Receiver** (Port 5001) - Alertmanager webhook integration
4. **Drift Service** (Port 8000) - Health checks and Prometheus metrics

All services follow REST conventions and return JSON responses. Error responses include appropriate HTTP status codes and descriptive error messages.

---

## Inference API

**Base URL:** `http://localhost:8001`

The Inference API provides ML model predictions and publishes events to Redis streams for monitoring and drift detection.

### POST /predict

**Description:**
Make predictions using the loaded ML model. Each prediction generates a unique request ID and publishes an event to the Redis stream for downstream processing.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "feature_1": 0.5,
  "feature_2": 1.2,
  "feature_3": 0.8
}
```

**Request Schema:**
- `feature_1` (float, required): First feature value
- `feature_2` (float, required): Second feature value  
- `feature_3` (float, optional): Third feature value (defaults to 0.0)

**Response (200 OK):**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "prediction": {
    "label": 1,
    "confidence": 0.85
  },
  "model_version": "v1.0.0",
  "latency_ms": 12.34
}
```

**Response Schema:**
- `request_id` (string): Unique UUID for the prediction request
- `prediction` (object): Prediction result
  - `label` (integer): Predicted class label (0 or 1)
  - `confidence` (float): Prediction confidence score (0.0 to 1.0)
- `model_version` (string): Version of the model used
- `latency_ms` (float): Processing time in milliseconds

**Error Responses:**

**400 Bad Request:**
```json
{
  "detail": [
    {
      "loc": ["body", "feature_1"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Prediction failed: Model not loaded"
}
```

**Example:**
```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "feature_1": 0.5,
    "feature_2": 1.2,
    "feature_3": 0.8
  }'
```

### GET /health

**Description:**
Health check endpoint that returns service status and Redis connection state.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "inference-api",
  "redis": "connected",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Response Schema:**
- `status` (string): Service health status ("healthy")
- `service` (string): Service identifier
- `redis` (string): Redis connection status ("connected" or "disconnected")
- `timestamp` (string): Current timestamp in ISO 8601 format

**Example:**
```bash
curl http://localhost:8001/health
```

### GET /

**Description:**
Root endpoint providing API information and available endpoints.

**Response (200 OK):**
```json
{
  "service": "ML Inference API",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "predict": "/predict (POST)",
    "docs": "/docs"
  }
}
```

**Example:**
```bash
curl http://localhost:8001/
```

---

## Replay Service

**Base URL:** `http://localhost:8002`

The Replay Service fetches historical events from the database and replays them through the Inference API to compare predictions between different model versions.

### POST /replay

**Description:**
Replay historical events through the current inference API and compare predictions. Useful for A/B testing and model performance analysis.

**Query Parameters:**
- `model_version` (string, optional): Filter events by specific model version
- `limit` (integer, optional): Number of events to replay (1-50, default: 50)

**Request:**
```
POST /replay?model_version=v1.0.0&limit=10
```

**Response (200 OK):**
```json
{
  "replayed_count": 10,
  "comparisons": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "old_prediction": {
        "label": 1,
        "confidence": 0.85
      },
      "new_prediction": {
        "label": 1,
        "confidence": 0.87
      },
      "confidence_diff": 0.02
    }
  ],
  "model_version": "v1.0.0"
}
```

**Response Schema:**
- `replayed_count` (integer): Number of events successfully replayed
- `comparisons` (array): Array of comparison results
  - `request_id` (string): Original request ID
  - `old_prediction` (object): Historical prediction from database
  - `new_prediction` (object): New prediction from current model
  - `confidence_diff` (float): Difference in confidence scores (new - old)
- `model_version` (string): Model version filter used (if any)

**Error Responses:**

**400 Bad Request:**
```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 50",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to fetch events: Database connection failed"
}
```

**502 Bad Gateway:**
```json
{
  "detail": "Inference API error: Connection timeout"
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Database connection failed"
}
```

**Example:**
```bash
# Replay last 10 events from any model version
curl -X POST "http://localhost:8002/replay?limit=10"

# Replay events from specific model version
curl -X POST "http://localhost:8002/replay?model_version=v1.0.0&limit=25"
```

### GET /health

**Description:**
Health check endpoint that verifies database and inference API connectivity.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "replay-service",
  "database": "connected",
  "inference_api": "connected",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Response Schema:**
- `status` (string): Service health status ("healthy")
- `service` (string): Service identifier
- `database` (string): Database connection status ("connected" or "disconnected")
- `inference_api` (string): Inference API connection status ("connected", "error", or "disconnected")
- `timestamp` (string): Current timestamp in ISO 8601 format

**Example:**
```bash
curl http://localhost:8002/health
```

### GET /

**Description:**
Root endpoint providing API information and available endpoints.

**Response (200 OK):**
```json
{
  "service": "ML Replay Service",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "replay": "/replay (POST)",
    "docs": "/docs"
  }
}
```

**Example:**
```bash
curl http://localhost:8002/
```

---

## Webhook Receiver

**Base URL:** `http://localhost:5001`

The Webhook Receiver processes alerts from Alertmanager and logs them for monitoring purposes.

### POST /alert

**Description:**
Receive and process alerts from Prometheus Alertmanager. Logs alert details and returns acknowledgment.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "alerts": [
    {
      "labels": {
        "alertname": "HighDriftDetected",
        "severity": "warning",
        "feature": "feature_1"
      },
      "annotations": {
        "summary": "High drift detected on feature_1",
        "description": "PSI score of 0.25 exceeds threshold of 0.2"
      },
      "status": "firing",
      "startsAt": "2024-01-15T10:30:00.000Z",
      "endsAt": "0001-01-01T00:00:00Z"
    }
  ]
}
```

**Request Schema:**
- `alerts` (array): Array of alert objects
  - `labels` (object): Alert labels
    - `alertname` (string): Name of the alert
    - `severity` (string): Alert severity level
    - Additional custom labels
  - `annotations` (object): Alert annotations
    - `summary` (string): Brief alert summary
    - `description` (string): Detailed alert description
  - `status` (string): Alert status ("firing" or "resolved")
  - `startsAt` (string): Alert start time in ISO 8601 format
  - `endsAt` (string): Alert end time in ISO 8601 format

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Alert received"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "status": "error",
  "message": "JSON decode error: Expecting value"
}
```

**Example:**
```bash
curl -X POST http://localhost:5001/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "labels": {
          "alertname": "HighDriftDetected",
          "severity": "warning"
        },
        "annotations": {
          "summary": "Drift detected",
          "description": "Feature drift threshold exceeded"
        },
        "status": "firing",
        "startsAt": "2024-01-15T10:30:00.000Z"
      }
    ]
  }'
```

### GET /health

**Description:**
Health check endpoint for container monitoring.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "webhook-receiver"
}
```

**Example:**
```bash
curl http://localhost:5001/health
```

### GET /

**Description:**
Root endpoint with service information.

**Response (200 OK):**
```json
{
  "service": "Alert Webhook Receiver",
  "version": "1.0.0",
  "endpoints": {
    "alert": "/alert (POST)",
    "health": "/health (GET)"
  }
}
```

**Example:**
```bash
curl http://localhost:5001/
```

---

## Drift Service

**Base URL:** `http://localhost:8000`

The Drift Service provides health checks and Prometheus metrics for monitoring drift detection performance.

### GET /health

**Description:**
Health check endpoint for the drift detection service.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "drift-detection",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**Response Schema:**
- `status` (string): Service health status ("healthy")
- `service` (string): Service identifier
- `timestamp` (string): Current timestamp in ISO 8601 format

**Example:**
```bash
curl http://localhost:8000/health
```

### GET /metrics

**Description:**
Prometheus metrics endpoint exposing drift detection and system metrics.

**Response (200 OK):**
```
# HELP ml_events_processed_total Total number of ML events processed
# TYPE ml_events_processed_total counter
ml_events_processed_total 1250

# HELP ml_drift_score Current drift score (0.0 to 1.0)
# TYPE ml_drift_score gauge
ml_drift_score 0.15

# HELP ml_predictions_total Total number of predictions made
# TYPE ml_predictions_total counter
ml_predictions_total 1250

# HELP ml_inference_latency_seconds Inference latency in seconds
# TYPE ml_inference_latency_seconds histogram
ml_inference_latency_seconds_bucket{le="0.01"} 850
ml_inference_latency_seconds_bucket{le="0.05"} 1200
ml_inference_latency_seconds_bucket{le="0.1"} 1240
ml_inference_latency_seconds_bucket{le="+Inf"} 1250
ml_inference_latency_seconds_sum 15.75
ml_inference_latency_seconds_count 1250

# HELP ml_drift_detected_total Total number of drift alerts generated
# TYPE ml_drift_detected_total counter
ml_drift_detected_total{feature="feature_1",method="psi"} 3
ml_drift_detected_total{feature="feature_2",method="ks_test"} 1
```

**Response Headers:**
```
Content-Type: text/plain; version=0.0.4; charset=utf-8
```

**Metrics Exposed:**
- `ml_events_processed_total`: Counter of processed ML events
- `ml_drift_score`: Current unified drift score (0.0 to 1.0)
- `ml_predictions_total`: Counter of total predictions made
- `ml_inference_latency_seconds`: Histogram of inference latencies
- `ml_drift_detected_total`: Counter of drift alerts by feature and method
- `ml_baseline_samples`: Gauge of baseline samples collected
- `ml_sliding_window_samples`: Gauge of sliding window samples
- `ml_alerts_published_total`: Counter of published alerts
- `ml_processing_duration_seconds`: Histogram of event processing times

**Example:**
```bash
curl http://localhost:8000/metrics
```

---

## Common Error Handling

All services follow consistent error handling patterns:

### HTTP Status Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid request parameters or body
- **500 Internal Server Error**: Server-side processing error
- **502 Bad Gateway**: Upstream service error (Replay Service only)
- **503 Service Unavailable**: Service dependency unavailable

### Error Response Format

```json
{
  "detail": "Error description"
}
```

For validation errors (400 Bad Request):
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Authentication

Currently, all APIs are publicly accessible without authentication. In production environments, consider implementing:

- API key authentication
- JWT token validation
- Rate limiting
- IP whitelisting

---

## Rate Limiting

No rate limiting is currently implemented. For production use, consider:

- Request rate limits per IP/API key
- Burst protection
- Queue management for high-volume scenarios

---

## Monitoring and Observability

All services provide:

- Health check endpoints for container orchestration
- Structured logging with configurable levels
- Prometheus metrics (Drift Service)
- Request/response correlation via request IDs
- Error tracking and alerting integration

---

## Development and Testing

### Interactive API Documentation

Each FastAPI service provides interactive documentation:

- Inference API: `http://localhost:8001/docs`
- Replay Service: `http://localhost:8002/docs`
- Webhook Receiver: `http://localhost:5001/docs`

### Testing Examples

Complete testing workflow:

```bash
# 1. Check all services are healthy
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:5001/health
curl http://localhost:8000/health

# 2. Make a prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'

# 3. Replay historical events
curl -X POST "http://localhost:8002/replay?limit=5"

# 4. Send test alert
curl -X POST http://localhost:5001/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {"alertname": "TestAlert", "severity": "info"},
      "annotations": {"summary": "Test alert"},
      "status": "firing",
      "startsAt": "2024-01-15T10:30:00.000Z"
    }]
  }'

# 5. Check metrics
curl http://localhost:8000/metrics