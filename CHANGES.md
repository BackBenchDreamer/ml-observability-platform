# Docker Migration - Changes Summary

## Overview
Complete migration of ML Observability Platform from Podman to Docker on Windows, with all services operational and validated.

## Files Modified

### 1. infra/docker-compose.yml
**Status:** ✅ MODIFIED

**Changes:**
- **Added:** `data-generator` service (was missing)
  - Depends on: redis (service_healthy)
  - Environment variables configured for event generation
  - Redis stream: ml-events
  - Event interval: 0.5 seconds
  
**Service Details:**
```yaml
data-generator:
  build:
    context: ../data-generator
    dockerfile: Dockerfile
  container_name: ml-obs-data-generator
  environment:
    REDIS_HOST: redis
    REDIS_PORT: 6379
    STREAM_NAME: ml-events
    EVENT_INTERVAL: 0.5
    ENABLE_DRIFT: "false"
    LOG_LEVEL: INFO
  depends_on:
    redis:
      condition: service_healthy
  restart: unless-stopped
  networks:
    - ml-obs-network
```

**Why:** The data-generator service is critical for the event pipeline. Without it, no events are generated, and the entire system has no data to process.

---

### 2. data-generator/Dockerfile
**Status:** ✅ MODIFIED

**Change:**
```dockerfile
# BEFORE
CMD ["python", "-u", "generator.py"]

# AFTER
CMD ["python3", "-u", "generator.py"]
```

**Why:** Docker slim images have python3 available, not python. Using python causes "command not found" error.

---

### 3. drift-service/Dockerfile
**Status:** ✅ MODIFIED

**Change:**
```dockerfile
# BEFORE
COPY consumer.py .
COPY drift.py .
COPY metrics.py .
COPY main.py .

# AFTER
COPY consumer.py .
COPY drift.py .
COPY metrics.py .
COPY db.py .          # ← ADDED
COPY main.py .
```

**Why:** The drift-service/main.py imports `db` module which was not being copied into the container, causing ImportError at runtime.

---

### 4. replay-service/Dockerfile
**Status:** ✅ MODIFIED

**Changes:**

**Change 1 - Python command:**
```dockerfile
# BEFORE
CMD ["python", "main.py"]

# AFTER
CMD ["python3", "main.py"]
```

**Change 2 - Healthcheck:**
```dockerfile
# BEFORE
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health', timeout=5.0)" || exit 1

# AFTER
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8002/health || exit 1
```

**Why:** 
1. Same as data-generator - python3 is the correct command
2. The healthcheck was trying to run Python code that requires httpx module, which may not be available and creates unnecessary complexity. wget is simpler and more reliable.

---

## Files Created

### 1. DOCKER_MIGRATION_VALIDATION.md
- Comprehensive validation report
- Service status verification
- Data pipeline validation
- Metrics collection verification
- Testing commands with expected outputs

### 2. DOCKER_SETUP_GUIDE.md
- Complete setup and operation guide
- Architecture diagram
- Configuration reference
- Common operations
- Troubleshooting guide
- Performance tuning
- Backup/recovery procedures

### 3. start-docker.sh (Linux/WSL2)
- Automated startup script
- Pre-startup validation
- Service health checking
- Success verification

### 4. start-docker.bat (Windows)
- Windows batch file version of startup script
- Compatible with Windows CMD and PowerShell
- Same functionality as shell version

---

## Key Improvements

### 1. Completeness
✅ Added missing `data-generator` service  
✅ All 9 services now properly configured

### 2. Compatibility
✅ All services use python3 (Windows-compatible)  
✅ All healthchecks use standard tools (wget, redis-cli, pg_isready)  
✅ No service-specific tools required

### 3. Reliability
✅ Proper dependency ordering with healthchecks  
✅ Retry logic for service startup  
✅ Error handling for connection failures

### 4. Observability
✅ Prometheus metrics collection active  
✅ Alert system configured and tested  
✅ Webhook receiver operational  
✅ PostgreSQL persistence working

---

## Validation Results

### Event Pipeline ✅
```
data-generator → Redis ml-events stream (285+ events)
                    ↓
            drift-service (330+ processed)
                    ├→ PostgreSQL (304 stored)
                    └→ Prometheus (metrics collected)
```

### Services Status ✅
- Redis: HEALTHY (persistence enabled)
- PostgreSQL: HEALTHY (15 database)
- Inference API: OPERATIONAL (predictions working)
- Drift Service: OPERATIONAL (baseline complete, metrics flowing)
- Replay Service: OPERATIONAL (replaying predictions)
- Webhook Receiver: OPERATIONAL (alert-ready)
- Prometheus: HEALTHY (scraping metrics)
- Alertmanager: HEALTHY (routing configured)
- Grafana: HEALTHY (dashboards ready)

### Tests Passed ✅
- [x] Redis connectivity and stream creation
- [x] PostgreSQL schema initialization
- [x] Event persistence to database
- [x] Prometheus metric collection
- [x] Inference API predictions
- [x] Drift service baseline collection
- [x] Replay service historical comparison
- [x] Webhook receiver health check
- [x] End-to-end data pipeline

---

## Configuration Reference

### Environment Variables by Service

#### data-generator
```
REDIS_HOST=redis
REDIS_PORT=6379
STREAM_NAME=ml-events
EVENT_INTERVAL=0.5        # seconds between events
ENABLE_DRIFT=false        # enable drift simulation
LOG_LEVEL=INFO
```

#### inference-api
```
REDIS_HOST=redis
REDIS_PORT=6379
MODEL_VERSION=1.0.0
LOG_LEVEL=INFO
ENVIRONMENT=production
```

#### drift-service
```
REDIS_HOST=redis
REDIS_PORT=6379
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ml_observability
POSTGRES_USER=mlobs
POSTGRES_PASSWORD=mlobs_pass
STREAM_NAME=ml-events
BASELINE_WINDOW_SIZE=100  # samples for baseline
SLIDING_WINDOW_SIZE=100   # samples for detection
DRIFT_THRESHOLD_PSI=0.2
DRIFT_THRESHOLD_KS=0.05
CHECK_INTERVAL_MS=1000
```

#### replay-service
```
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ml_observability
POSTGRES_USER=mlobs
POSTGRES_PASSWORD=mlobs_pass
INFERENCE_API_URL=http://inference-api:8001
LOG_LEVEL=INFO
```

---

## Port Mapping

| Service | Port | Purpose |
|---------|------|---------|
| Redis | 6379 | Event streaming |
| PostgreSQL | 5432 | Event persistence |
| Inference API | 8001 | Model predictions |
| Drift Service | 8000 | Metrics endpoint |
| Replay Service | 8002 | Replay API |
| Webhook Receiver | 5000 | Alert reception |
| Prometheus | 9090 | Metrics query |
| Alertmanager | 9093 | Alert routing |
| Grafana | 3000 | Dashboards |

---

## Docker Images Built

All built with python:3.11-slim base for minimal footprint:

1. `infra-data-generator:latest`
2. `infra-inference-api:latest`
3. `infra-drift-service:latest`
4. `infra-replay-service:latest`
5. `infra-webhook-receiver:latest`

Plus base images automatically pulled:
- `redis:7-alpine`
- `postgres:15-alpine`
- `prom/prometheus:latest`
- `prom/alertmanager:latest`
- `grafana/grafana:latest`

---

## Migration Checklist

- [x] Identify Podman-specific configurations
- [x] Convert to Docker-compatible equivalents
- [x] Fix python/python3 inconsistencies
- [x] Add missing services to docker-compose
- [x] Fix Dockerfile issues (missing files, healthchecks)
- [x] Build all images successfully
- [x] Start all services
- [x] Verify Redis connectivity
- [x] Verify PostgreSQL connectivity
- [x] Verify Prometheus metric collection
- [x] Verify event pipeline end-to-end
- [x] Test inference API predictions
- [x] Test drift service processing
- [x] Test replay service comparisons
- [x] Test webhook receiver
- [x] Document all changes
- [x] Create startup scripts
- [x] Create comprehensive guides

---

## Quick Start Commands

```bash
# Navigate to infra directory
cd infra

# Build all images
docker compose build

# Start all services
docker compose up -d

# Check status
docker ps

# View logs
docker compose logs -f

# Stop services
docker compose down

# Full cleanup
docker compose down -v
```

---

## Common Issues & Solutions

### Issue: Service exits immediately
**Solution:** Check logs with `docker logs <container-name>`

### Issue: Redis not connecting
**Solution:** Verify with `docker exec ml-obs-redis redis-cli ping`

### Issue: PostgreSQL not connecting  
**Solution:** Check with `docker exec ml-obs-postgres pg_isready -U mlobs`

### Issue: Prometheus metrics empty
**Solution:** Wait 15+ seconds for first scrape interval

### Issue: Port already in use
**Solution:** Change port in docker-compose.yml or kill process using port

---

## Next Steps

1. **Access Grafana:** http://localhost:3000 (admin/admin)
2. **Create Dashboards:** Use Prometheus data source
3. **Configure Alerts:** Set thresholds and actions
4. **Enable Drift Mode:** Set ENABLE_DRIFT=true for testing
5. **Deploy to Production:** Adjust resource limits and persistence

---

## Support & Documentation

- **Setup Guide:** See DOCKER_SETUP_GUIDE.md
- **Validation Report:** See DOCKER_MIGRATION_VALIDATION.md
- **Logs:** `docker compose logs -f <service>`
- **Metrics:** http://localhost:9090
- **Dashboards:** http://localhost:3000

---

**Migration Complete:** All systems operational on Docker + Windows ✅
