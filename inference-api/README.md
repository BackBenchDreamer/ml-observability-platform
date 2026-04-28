# Inference API Service

FastAPI-based inference service that provides ML predictions and publishes events to Redis Streams for observability.

## Overview

This service:
- Exposes a REST API for ML model predictions
- Uses a simple RandomForest classifier for binary classification
- Publishes prediction events to Redis Stream (`ml-events`)
- Integrates with the ML observability platform

## Architecture

```
Client Request → FastAPI → ML Model → Prediction
                    ↓
              Redis Stream (ml-events)
```

## API Endpoints

### POST /predict

Make a prediction using the ML model.

**Request Body:**
```json
{
  "feature_1": 0.5,
  "feature_2": 1.2,
  "feature_3": 0.8
}
```

**Response:**
```json
{
  "request_id": "uuid-v4",
  "prediction": {
    "label": 0,
    "confidence": 0.92
  },
  "model_version": "1.0.0",
  "latency_ms": 45.2
}
```

**Example curl command:**
```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "inference-api",
  "redis": "connected",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### GET /

Root endpoint with API information.

### GET /docs

Interactive API documentation (Swagger UI).

## ML Model

- **Type:** RandomForest Classifier
- **Task:** Binary Classification
- **Features:** 3 numerical features (feature_1, feature_2, feature_3)
- **Training:** Simple dummy data (trained on startup)
- **Output:** Label (0 or 1) and confidence score (0.0-1.0)

The model is intentionally simple to focus on system integration rather than ML complexity.

## Redis Event Schema

Each prediction publishes an event to Redis Stream `ml-events` with the following structure:

```json
{
  "schema_version": "1.0",
  "request_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "model_version": "v1.0.0",
  "features": {
    "feature_1": 0.85,
    "feature_2": 1.2,
    "feature_3": 0.8
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

## Running the Service

### Option 1: Standalone (Development)

1. **Install dependencies:**
   ```bash
   cd inference-api
   python3 -m pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export REDIS_HOST=localhost
   export REDIS_PORT=6379
   export LOG_LEVEL=INFO
   ```

3. **Run the service:**
   ```bash
   python3 main.py
   ```

   The service will be available at `http://localhost:8001`

### Option 2: With Podman Compose (Production)

1. **Start all services:**
   ```bash
   cd infra
   podman-compose up -d
   ```

2. **Check service status:**
   ```bash
   podman-compose ps
   ```

3. **View logs:**
   ```bash
   podman-compose logs -f inference-api
   ```

## Verification Steps

### 1. Check Service Health

```bash
curl http://localhost:8001/health
```

Expected output:
```json
{
  "status": "healthy",
  "service": "inference-api",
  "redis": "connected",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 2. Make a Test Prediction

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'
```

### 3. Verify Event in Redis

Check that the prediction event was published to Redis:

```bash
podman exec -it ml-obs-redis redis-cli XREAD COUNT 5 STREAMS ml-events 0
```

You should see the prediction event with all fields from the schema.

### 4. Access API Documentation

Open in browser: `http://localhost:8001/docs`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `MODEL_VERSION` | `1.0.0` | Model version identifier |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | `production` | Environment name for metadata |

## Development

### Project Structure

```
inference-api/
├── main.py              # FastAPI application and endpoints
├── model.py             # ML model wrapper and training
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container definition
├── .env.example         # Environment variables template
└── README.md           # This file
```

### Adding New Features

1. **New endpoints:** Add to `main.py`
2. **Model changes:** Modify `model.py`
3. **Dependencies:** Update `requirements.txt`

### Testing

```bash
# Test prediction endpoint
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 1.0, "feature_2": -0.5, "feature_3": 0.3}'

# Test with different values
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": -1.0, "feature_2": -1.0, "feature_3": 0.0}'
```

## Troubleshooting

### Service won't start

1. Check Redis is running:
   ```bash
   podman ps | grep redis
   ```

2. Check logs:
   ```bash
   podman-compose logs inference-api
   ```

### Redis connection failed

1. Verify Redis host/port in environment variables
2. Check network connectivity:
   ```bash
   podman exec -it ml-obs-inference-api ping redis
   ```

### Model training errors

Check logs for sklearn/numpy errors. Ensure all dependencies are installed.

## Integration with Observability Platform

This service is part of the ML Observability Platform:

- **Phase 1:** Redis infrastructure (completed)
- **Phase 2:** Data generator (completed)
- **Phase 3:** Inference API (this service)
- **Phase 4:** Observer engine (processes events)
- **Phase 5:** Replay service (historical analysis)

Events published by this service are consumed by the observer-engine for real-time monitoring and alerting.

## License

See main project LICENSE file.