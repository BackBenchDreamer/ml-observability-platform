# Replay Service

FastAPI service for replaying historical ML events through the inference API to compare model predictions.

## Features

- Fetch historical events from PostgreSQL database
- Replay events through inference API
- Compare old vs new predictions
- Calculate confidence differences
- Support filtering by model version
- Batch processing (max 50 events)

## API Endpoints

### POST /replay

Replay historical events and compare predictions.

**Query Parameters:**
- `model_version` (optional): Filter events by model version
- `limit` (optional, default=50, max=50): Number of events to replay

**Response:**
```json
{
  "replayed_count": 10,
  "model_version": "v1.0.0",
  "comparisons": [
    {
      "request_id": "uuid",
      "old_prediction": {"label": 0, "confidence": 0.85},
      "new_prediction": {"label": 0, "confidence": 0.87},
      "confidence_diff": 0.02
    }
  ]
}
```

### GET /health

Health check endpoint.

### GET /

Service information.

## Configuration

Environment variables (see `.env.example`):

- `POSTGRES_HOST`: PostgreSQL host (default: localhost)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_DB`: Database name (default: ml_observability)
- `POSTGRES_USER`: Database user (default: mlobs)
- `POSTGRES_PASSWORD`: Database password
- `INFERENCE_API_URL`: Inference API URL (default: http://localhost:8001)
- `LOG_LEVEL`: Logging level (default: INFO)

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run service
python main.py
```

Service runs on port 8002.

## Running with Docker/Podman

```bash
# Build image
podman build -t replay-service .

# Run container
podman run -p 8002:8002 \
  -e POSTGRES_HOST=postgres \
  -e INFERENCE_API_URL=http://inference-api:8001 \
  replay-service
```

## Usage Example

```bash
# Replay last 50 events
curl -X POST "http://localhost:8002/replay?limit=50"

# Replay events for specific model version
curl -X POST "http://localhost:8002/replay?model_version=v1.0.0&limit=20"
```

## Dependencies

- FastAPI: Web framework
- httpx: Async HTTP client for inference API calls
- psycopg2-binary: PostgreSQL database adapter
- uvicorn: ASGI server

## Notes

- Maximum batch size is capped at 50 events to prevent overload
- Events are fetched in descending timestamp order (most recent first)
- Failed replays are logged but don't stop the batch processing
- Database connection is tested on each request (no connection pooling in this simple implementation)