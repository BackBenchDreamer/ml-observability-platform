# Docker Migration Guide - ML Observability Platform

This guide covers running the ML Observability Platform with Docker on Windows.

## Prerequisites

### System Requirements
- **OS:** Windows 10 Pro/Enterprise or Windows 11
- **CPU:** 4+ cores recommended
- **RAM:** 8GB minimum (12GB recommended)
- **Disk:** 10GB free space
- **Network:** Ports 5000, 5432, 6379, 8000-8002, 3000, 9090, 9093 available

### Software Requirements
- **Docker Desktop for Windows** (v29.0.0+)
- **WSL2** (Windows Subsystem for Linux 2) - required by Docker Desktop
- **Git** (optional, for version control)

### Installation Steps

1. **Install Docker Desktop**
   ```powershell
   # Using Windows Package Manager (winget)
   winget install -e --id Docker.DockerDesktop
   
   # Or download from: https://www.docker.com/products/docker-desktop
   ```

2. **Enable WSL2**
   ```powershell
   # In PowerShell (as Administrator)
   wsl --install -d Ubuntu-22.04
   ```

3. **Configure Docker Desktop**
   - Open Docker Desktop Settings
   - Go to Resources > WSL Integration
   - Enable "Ubuntu-22.04" (or your WSL2 distro)
   - Apply & Restart

4. **Verify Installation**
   ```bash
   docker --version
   docker compose version
   ```

---

## Quick Start

### Option 1: Using Start Script (Recommended)

**Windows (PowerShell):**
```powershell
cd c:\path\to\ml-observability-platform
.\start-docker.bat
```

**Windows (Git Bash/WSL2):**
```bash
cd /c/path/to/ml-observability-platform
bash start-docker.sh
```

The script will:
1. Build all Docker images
2. Start all services in background
3. Validate all components
4. Display access information

### Option 2: Manual Startup

```bash
# Navigate to infra directory
cd infra

# Build images (one-time)
docker compose build

# Start all services
docker compose up -d

# View startup progress
docker compose logs -f

# Check status
docker ps
```

---

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Docker Compose Network: ml-obs-network         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐                                        │
│  │  data-generator │◄─┐ (generates events)                 │
│  └────────┬────────┘  │                                    │
│           │           │                                    │
│           ▼           │                                    │
│  ┌──────────────────┐ │                                    │
│  │  Redis:6379      │ │ (event streaming)                  │
│  │ ml-events stream │ │                                    │
│  └────────┬─────────┘ │                                    │
│           │           │                                    │
│           ▼           │                                    │
│  ┌────────────────────────────────────┐                    │
│  │   Inference API:8001                │◄─┐ (predictions) │
│  │ (model: random-forest-v1 v1.0.0)   │  │               │
│  └────────┬───────────────────────────┘  │               │
│           │                               │               │
│           ├────────────┬──────────────────┼───┐           │
│           │            │                  │   │           │
│           ▼            ▼                  │   │           │
│  ┌───────────────┐  ┌──────────────┐     │   │           │
│  │ drift-service │  │ replay-service│    │   │           │
│  │ :8000 (metrics)  │ :8002 (replay)    │   │           │
│  └────────┬──────┘  └──────┬──────┘     │   │           │
│           │                │             │   │           │
│           ├────────────┬───┴─────────────┘   │           │
│           │            │                     │           │
│           ▼            ▼                     │           │
│  ┌──────────────────┐  ┌──────────────────┐ │           │
│  │ PostgreSQL:5432  │  │ Prometheus:9090  │ │           │
│  │ (persistence)    │  │ (metrics)        │ │           │
│  └──────────────────┘  └──────┬───────────┘ │           │
│                                │             │           │
│                                ▼             │           │
│                        ┌──────────────────┐  │           │
│                        │ Alertmanager     │  │           │
│                        │ :9093            │  │           │
│                        └────────┬─────────┘  │           │
│                                 │             │           │
│                                 ▼             │           │
│                        ┌──────────────────┐  │           │
│                        │ webhook-receiver │◄─┘           │
│                        │ :5000 (alerts)   │              │
│                        └──────────────────┘              │
│                                 │                        │
│                                 ▼                        │
│                        ┌──────────────────┐              │
│                        │ Grafana:3000     │              │
│                        │ (dashboards)     │              │
│                        └──────────────────┘              │
│                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

Edit `infra/docker-compose.yml` to modify service behavior:

#### data-generator
```yaml
environment:
  REDIS_HOST: redis              # Redis hostname
  REDIS_PORT: 6379              # Redis port
  STREAM_NAME: ml-events        # Event stream name
  EVENT_INTERVAL: 0.5           # Events per second (default: 0.5)
  ENABLE_DRIFT: "false"         # Enable drift simulation
  LOG_LEVEL: INFO               # Logging level
```

#### inference-api
```yaml
environment:
  REDIS_HOST: redis             # Redis hostname
  REDIS_PORT: 6379              # Redis port
  MODEL_VERSION: 1.0.0          # Model version
  LOG_LEVEL: INFO               # Logging level
  ENVIRONMENT: production       # Environment name
```

#### drift-service
```yaml
environment:
  REDIS_HOST: redis             # Redis hostname
  STREAM_NAME: ml-events        # Event stream to consume
  BASELINE_WINDOW_SIZE: 100     # Baseline sample count
  SLIDING_WINDOW_SIZE: 100      # Sliding window size
  DRIFT_THRESHOLD_PSI: 0.2      # PSI threshold
  DRIFT_THRESHOLD_KS: 0.05      # KS-test threshold
  CHECK_INTERVAL_MS: 1000       # Check interval (ms)
```

#### PostgreSQL
```yaml
environment:
  POSTGRES_DB: ml_observability
  POSTGRES_USER: mlobs
  POSTGRES_PASSWORD: mlobs_pass
```

### Volumes

Persistent data is stored in Docker volumes:
```
redis-data       → Redis persistence
postgres-data    → PostgreSQL database
prometheus-data  → Prometheus time-series data
grafana-data     → Grafana configuration/dashboards
```

### Port Mappings

| Service | Container Port | Host Port | Protocol |
|---------|-----------------|-----------|----------|
| Redis | 6379 | 6379 | TCP |
| PostgreSQL | 5432 | 5432 | TCP |
| Inference API | 8001 | 8001 | HTTP |
| Drift Service | 8000 | 8000 | HTTP |
| Replay Service | 8002 | 8002 | HTTP |
| Webhook Receiver | 5000 | 5000 | HTTP |
| Prometheus | 9090 | 9090 | HTTP |
| Alertmanager | 9093 | 9093 | HTTP |
| Grafana | 3000 | 3000 | HTTP |

---

## Common Operations

### View Service Logs

```bash
# All services
docker compose logs

# Specific service (follow mode)
docker compose logs -f <service-name>

# Last 50 lines
docker compose logs --tail=50 <service-name>

# Specific service examples
docker compose logs -f data-generator
docker compose logs -f inference-api
docker compose logs -f drift-service
docker compose logs -f replay-service
```

### Stop Services

```bash
# Stop all services (keeps data)
docker compose down

# Stop and remove volumes (destroys data)
docker compose down -v

# Stop specific service
docker compose stop <service-name>
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart <service-name>
```

### Rebuild Images

```bash
# Rebuild specific service
docker compose build <service-name>

# Rebuild all services
docker compose build --no-cache
```

### Monitor Resource Usage

```bash
# Real-time stats
docker stats

# Stats for specific services
docker stats ml-obs-redis ml-obs-postgres ml-obs-drift-service
```

### Access Service Internals

```bash
# Execute command in container
docker exec <container-name> <command>

# Redis CLI
docker exec ml-obs-redis redis-cli

# PostgreSQL psql
docker exec ml-obs-postgres psql -U mlobs -d ml_observability

# Python shell in any service
docker exec -it ml-obs-drift-service python3
```

---

## Testing & Validation

### Test Inference API

```bash
# Single prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'

# Response:
# {
#   "request_id": "...",
#   "prediction": {"label": 1, "confidence": 0.988},
#   "model_version": "1.0.0",
#   "latency_ms": 2.37
# }
```

### Test Replay Service

```bash
# Replay 5 recent events
curl -X POST "http://localhost:8002/replay?limit=5"

# Response includes:
# - replayed_count: number of events replayed
# - comparisons: list of old vs new predictions
# - confidence_diff: difference in model confidence
```

### Test Webhook Receiver

```bash
# Send test alert
curl -X POST http://localhost:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {"alertname": "TestDrift", "severity": "warning"},
      "annotations": {"summary": "Test alert", "description": "Testing webhook"},
      "status": "firing",
      "startsAt": "2026-04-29T10:00:00Z"
    }]
  }'
```

### Monitor Data Pipeline

```bash
# Check Redis stream length
docker exec ml-obs-redis redis-cli XLEN ml-events

# Check events in PostgreSQL
docker exec ml-obs-postgres psql -U mlobs -d ml_observability \
  -c "SELECT COUNT(*) as event_count FROM ml_events;"

# Check drift metrics
curl -s http://localhost:8000/metrics | grep drift_

# Query Prometheus
curl -s "http://localhost:9090/api/v1/query?query=drift_events_processed_total"
```

---

## Enable Drift Detection Testing

To test drift alerting:

1. **Edit `infra/docker-compose.yml`**
   ```yaml
   data-generator:
     environment:
       ENABLE_DRIFT: "true"  # Enable drift mode
   ```

2. **Rebuild and restart**
   ```bash
   docker compose up -d --build
   ```

3. **Monitor for alerts**
   ```bash
   # Watch drift-service logs
   docker logs -f ml-obs-drift-service
   
   # Watch for metrics
   curl -s http://localhost:8000/metrics | grep drift_detected
   
   # Check alerts in Prometheus
   curl -s "http://localhost:9090/api/v1/query?query=drift_detected_total"
   ```

4. **Check alert in webhook-receiver**
   ```bash
   docker logs -f ml-obs-webhook-receiver
   # Will show alerts as they're received
   ```

---

## Access Observability Dashboards

### Grafana (http://localhost:3000)
- **Username:** admin
- **Password:** admin
- **Data Source:** Prometheus (pre-configured)
- Create custom dashboards using available metrics

### Prometheus (http://localhost:9090)
- Query available metrics
- View alert rules
- Check scrape targets

### Alertmanager (http://localhost:9093)
- View active alerts
- Check routing configuration
- View silence groups

---

## Troubleshooting

### Services Won't Start

**Problem:** Services show "unhealthy" or "exited"

**Solution:**
```bash
# Check logs
docker compose logs <service-name>

# Common issues:
# 1. Port already in use
netstat -ano | findstr :8001
# Kill process: taskkill /PID <PID> /F

# 2. Docker Desktop not running
# - Restart Docker Desktop

# 3. WSL2 out of memory
# - Increase WSL memory in Docker settings

# 4. Volume permissions
# - Run Docker as Administrator
```

### Redis Connection Failed

**Problem:** Services can't connect to Redis

**Solution:**
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
docker exec ml-obs-redis redis-cli ping
# Should return: PONG

# Restart Redis
docker compose restart redis
```

### PostgreSQL Connection Failed

**Problem:** Drift service can't connect to database

**Solution:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec ml-obs-postgres pg_isready -U mlobs
# Should return: accepting connections

# Check database exists
docker exec ml-obs-postgres psql -U mlobs -l | grep ml_observability

# Restart PostgreSQL
docker compose restart postgres
```

### Prometheus Not Scraping Metrics

**Problem:** Metrics showing as empty in Prometheus

**Solution:**
```bash
# Wait 15+ seconds (default scrape interval)
# Check targets in Prometheus: http://localhost:9090/targets

# Check drift-service is exposing metrics
curl http://localhost:8000/metrics | head -20

# Check prometheus.yml configuration
cat infra/prometheus.yml

# Restart Prometheus
docker compose restart prometheus
```

### High Memory/CPU Usage

**Problem:** Docker containers using excessive resources

**Solution:**
```bash
# Check resource usage
docker stats

# Limit service resources by editing docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M

# Reduce drift detection window sizes
BASELINE_WINDOW_SIZE: 50    # Default: 100
SLIDING_WINDOW_SIZE: 50     # Default: 100
```

---

## Performance Tuning

### For High Throughput

```yaml
# Increase event generation rate
data-generator:
  environment:
    EVENT_INTERVAL: 0.1  # 10 events/sec instead of 2

# Increase drift service window sizes
drift-service:
  environment:
    BASELINE_WINDOW_SIZE: 500
    SLIDING_WINDOW_SIZE: 500
```

### For Low Resource Systems

```yaml
# Decrease event generation
data-generator:
  environment:
    EVENT_INTERVAL: 2.0  # 1 event per 2 seconds

# Smaller windows
drift-service:
  environment:
    BASELINE_WINDOW_SIZE: 50
    SLIDING_WINDOW_SIZE: 50
    CHECK_INTERVAL_MS: 5000  # Check every 5 seconds

# Reduce Prometheus scrape frequency
# (edit prometheus.yml):
global:
  scrape_interval: 30s  # Default: 15s
```

---

## Backup & Recovery

### Backup Data

```bash
# Backup PostgreSQL
docker exec ml-obs-postgres pg_dump -U mlobs ml_observability > backup.sql

# Backup Redis
docker exec ml-obs-redis redis-cli BGSAVE
docker cp ml-obs-redis:/data/dump.rdb ./dump.rdb

# Backup Prometheus data
docker exec ml-obs-prometheus tar czf /tmp/prometheus-data.tar.gz /prometheus
docker cp ml-obs-prometheus:/tmp/prometheus-data.tar.gz ./prometheus-data.tar.gz
```

### Restore Data

```bash
# Restore PostgreSQL
docker compose exec -T postgres psql -U mlobs ml_observability < backup.sql

# Restore Redis
docker cp dump.rdb ml-obs-redis:/data/dump.rdb
docker exec ml-obs-redis redis-cli BGSAVE
```

---

## Clean Up & Reset

### Remove Containers (Keep Data)
```bash
docker compose down
```

### Full Reset (Remove Everything)
```bash
# Stop and remove containers, networks, volumes
docker compose down -v

# Remove built images (optional)
docker rmi infra-data-generator infra-inference-api infra-drift-service \
  infra-replay-service infra-webhook-receiver
```

### Clean Docker System
```bash
# Remove unused images, containers, networks
docker system prune

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a --volumes
```

---

## Getting Help

### Check Documentation
- Service logs: `docker compose logs -f <service>`
- Prometheus metrics: http://localhost:9090
- Grafana dashboards: http://localhost:3000

### Common Commands Reference

```bash
# Status
docker compose ps
docker ps -a

# Logs
docker compose logs
docker compose logs -f <service>
docker logs <container-id>

# Control
docker compose up -d
docker compose down
docker compose restart
docker compose build

# Access
docker exec -it <container> bash
docker exec <container> <command>

# Resources
docker stats
docker system df
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs with `docker compose logs -f <service>`
3. Check Docker Desktop settings (Resources, WSL Integration)
4. Verify network connectivity and port availability
5. Consult individual service documentation

---

**ML Observability Platform v1.0** | Docker Edition  
Last Updated: 2026-04-29
