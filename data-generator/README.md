# Data Generator Service

Synthetic ML event generator for the ML Observability Platform. Generates events following the schema defined in `schemas/event_schema.json` and publishes them to Redis Streams.

## Features

- **Schema Compliance**: Generates events matching the exact schema structure
- **Normal Distribution**: Features generated using normal distribution (mean=0, std=1)
- **Drift Simulation**: Toggle drift mode to shift feature distribution (mean=5, std=1)
- **Redis Streams**: Publishes to Redis Streams using XADD command
- **Graceful Shutdown**: Handles SIGINT and SIGTERM signals properly
- **Connection Resilience**: Automatic retry logic for Redis connections

## Event Schema

Each generated event includes:
- `schema_version`: "1.0"
- `request_id`: UUID v4
- `timestamp`: ISO-8601 format (UTC)
- `model_version`: "v1.0.0"
- `features`: 
  - `feature_1`: float (normal distribution)
  - `feature_2`: float (normal distribution)
  - `feature_3`: float (normal distribution)
- `prediction`:
  - `label`: integer (0 or 1, random)
  - `confidence`: float (0.7-0.99, random)
- `metadata`:
  - `latency_ms`: float (10-100ms, random)
  - `environment`: "production"
  - `region`: string (random from us-east-1, us-west-2, eu-west-1)

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `ENABLE_DRIFT` | `false` | Enable drift mode (true/false) |
| `EVENT_INTERVAL` | `1.0` | Seconds between events |
| `STREAM_NAME` | `ml-events` | Redis stream name |

## Running Locally

### Prerequisites
- Python 3.11+
- Redis running (see `infra/docker-compose.yml` or `infra/podman-compose.yml`)

> **Note**: This service works with both Docker and Podman container runtimes.

### Install Dependencies
```bash
cd data-generator
python3 -m pip install -r requirements.txt
```

### Run Generator (Normal Mode)
```bash
python3 generator.py
```

### Run Generator (Drift Mode)
```bash
ENABLE_DRIFT=true python3 generator.py
```

### Custom Configuration
```bash
REDIS_HOST=localhost \
REDIS_PORT=6379 \
ENABLE_DRIFT=false \
EVENT_INTERVAL=0.5 \
python3 generator.py
```

## Running with Containers

### Build Image

**Docker:**
```bash
cd data-generator
docker build -t ml-data-generator .
```

**Podman:**
```bash
cd data-generator
podman build -t ml-data-generator .
```

### Run Container (Normal Mode)

**Docker:**
```bash
docker run --rm \
  --network ml-observability-platform_default \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  ml-data-generator
```

**Podman:**
```bash
podman run --rm \
  --network ml-observability-platform_default \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  ml-data-generator
```

### Run Container (Drift Mode)

**Docker:**
```bash
docker run --rm \
  --network ml-observability-platform_default \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e ENABLE_DRIFT=true \
  ml-data-generator
```

**Podman:**
```bash
podman run --rm \
  --network ml-observability-platform_default \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e ENABLE_DRIFT=true \
  ml-data-generator
```

## Drift Mode

When `ENABLE_DRIFT=true`:
- `feature_1` and `feature_2` distributions shift from mean=0 to mean=5
- Standard deviation remains at 1.0
- This simulates data drift for testing observability features
- A warning is logged when drift mode is active

## Verifying Events in Redis

### Using Redis CLI

**Docker:**
```bash
# Connect to Redis
docker exec -it ml-obs-redis redis-cli

# Read latest events from stream
XREAD COUNT 10 STREAMS ml-events 0

# Get stream info
XINFO STREAM ml-events

# Get stream length
XLEN ml-events
```

**Podman:**
```bash
# Connect to Redis
podman exec -it ml-obs-redis redis-cli

# Read latest events from stream
XREAD COUNT 10 STREAMS ml-events 0

# Get stream info
XINFO STREAM ml-events

# Get stream length
XLEN ml-events
```

### Using Python
```python
import redis
import json

client = redis.Redis(host='localhost', port=6379)

# Read last 10 events
events = client.xrevrange('ml-events', count=10)
for event_id, data in events:
    event = json.loads(data[b'event'])
    print(f"ID: {event_id}")
    print(f"Event: {json.dumps(event, indent=2)}")
```

## Logs

The generator logs:
- Connection status
- Configuration on startup
- Drift mode status
- Event generation rate (every 10 seconds)
- Errors and reconnection attempts

Example output:
```
2026-04-28 19:00:00 - __main__ - INFO - Starting ML Event Data Generator
2026-04-28 19:00:00 - __main__ - INFO - Configuration:
2026-04-28 19:00:00 - __main__ - INFO -   Redis: localhost:6379
2026-04-28 19:00:00 - __main__ - INFO -   Stream: ml-events
2026-04-28 19:00:00 - __main__ - INFO -   Event Interval: 1.0s
2026-04-28 19:00:00 - __main__ - INFO -   Drift Mode: DISABLED
2026-04-28 19:00:00 - __main__ - INFO - Successfully connected to Redis at localhost:6379
2026-04-28 19:00:10 - __main__ - INFO - Generated 10 events (rate: 1.00 events/sec)
```

## Troubleshooting

### Cannot connect to Redis
- Ensure Redis is running:
  - Docker: `docker ps | grep redis`
  - Podman: `podman ps | grep redis`
- Check Redis host/port configuration
- Verify network connectivity (use correct network if containerized)

### Import errors
- Install dependencies: `python3 -m pip install -r requirements.txt`
- Verify Python version: `python3 --version` (should be 3.11+)

### Events not appearing in stream
- Check Redis connection logs
- Verify stream name matches configuration
- Use `redis-cli` to manually check stream: `XLEN ml-events`

## Next Steps

After starting the generator:
1. Verify events are being published:
   - Docker: `docker exec -it ml-obs-redis redis-cli XLEN ml-events`
   - Podman: `podman exec -it ml-obs-redis redis-cli XLEN ml-events`
2. Implement the observer-engine service to consume these events
3. Test drift detection by toggling `ENABLE_DRIFT`
4. Monitor event generation rate and Redis stream growth
