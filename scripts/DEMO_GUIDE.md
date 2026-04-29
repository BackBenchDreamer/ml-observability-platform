# Demo Script Migration - Podman/Mac to Docker/Windows

## Overview

The demo script has been updated to work with **Docker on Windows** (previously Podman on Mac). Two versions are now available:

- **demo.sh** - For Linux/WSL2/Git Bash on Windows
- **demo.bat** - For Windows CMD/PowerShell

---

## Key Changes Made

### 1. Container Orchestration
| Old | New |
|-----|-----|
| `podman-compose` | `docker compose` |
| Podman-specific commands | Docker-compatible commands |

### 2. Port Mappings
The original script had incorrect port mappings. Now using correct ports from updated docker-compose.yml:

| Service | Old Port | New Port |
|---------|----------|----------|
| Inference API | 8000 | **8001** |
| Drift Service | 8001 | **8000** |
| Replay Service | 8002 | **8002** (unchanged) |
| Webhook Receiver | - | **5000** |
| Alertmanager | 9093 | **9093** |
| Prometheus | 9090 | **9090** |
| Grafana | 3000 | **3000** |

### 3. Data Generator
**Old Approach:**
- Ran custom DataGenerator class directly from Python
- Required separate Python process management

**New Approach:**
- Uses the running `data-generator` Docker container
- Enables drift by overriding docker-compose with `docker-compose.drift.yml`
- No separate Python process needed

### 4. File Paths
| Old | New |
|-----|-----|
| `/tmp/run_generator.py` | Creates temporary docker-compose override |
| `/tmp/run_generator_drift.py` | `infra/docker-compose.drift.yml` |
| Unix temp directory | Windows-compatible temp location |

### 5. Health Checks
**Old:**
- Used Podman container management
- Mac-specific paths

**New:**
- Uses `docker exec` for direct container commands
- Uses `docker logs` for container logs
- Windows-compatible commands

---

## What the Demo Does

### Phase 1: Startup (0-45s)
1. Validates Docker and curl are installed
2. Stops any existing containers
3. Builds Docker images
4. Starts 9 services with `docker compose up -d`
5. Waits for services to initialize

### Phase 2: Health Checks (45-75s)
- Checks Redis with `redis-cli ping`
- Checks PostgreSQL with `pg_isready`
- Checks HTTP services with `curl`
- Confirms all services are ready

### Phase 3: Baseline Monitoring (75-135s)
- Monitors data-generator in normal mode
- Shows Redis stream events
- Shows PostgreSQL stored events
- Tests inference API prediction
- Duration: 60 seconds

### Phase 4: Drift Enabled (135-225s)
- Creates docker-compose.drift.yml override
- Restarts data-generator with ENABLE_DRIFT=true
- Monitors drift detection metrics
- Shows drift_detected_total and ml_drift_score
- Duration: 90 seconds

### Phase 5: Validation (225-240s)
- Restores normal mode
- Tests replay API
- Checks webhook logs for alerts
- Displays final metrics

---

## Running the Demo

### On Windows (Git Bash / WSL2)
```bash
# From project root
bash scripts/demo.sh

# Or if using WSL2
./scripts/demo.sh
```

### On Windows (CMD / PowerShell)
```batch
REM From project root
scripts\demo.bat

REM Or from PowerShell
& '.\scripts\demo.bat'
```

### On Linux/Mac
```bash
bash scripts/demo.sh
```

---

## Demo Output

The script displays:

1. **Step indicators** - Shows current phase
2. **Service health** - Confirms all services are operational
3. **Baseline metrics** - Shows event flow
4. **Drift metrics** - Shows drift detection signals
5. **Replay results** - Shows prediction comparisons
6. **Summary** - Lists all access points and next steps

### Expected Output Example
```
[STEP] Starting ML Observability Platform with Docker...
[INFO] Building images...
[SUCCESS] Services started

[STEP] Checking service health...
[INFO] Checking Redis...
[SUCCESS] Redis is healthy
...
[SUCCESS] All services are healthy

[STEP] Monitoring data pipeline in normal mode...
[BASELINE - 10s]
  Redis stream events: 145
  PostgreSQL stored:   145

[STEP] Enabling drift mode...
[SUCCESS] Drift mode enabled

[DRIFT DETECTION - 10s]
  Redis stream events: 312
  PostgreSQL stored:   312
  Drift metrics:
    drift_detected_total{feature="feature_1"} 1.0
    ml_drift_score 0.35

[SUCCESS] Demo script completed successfully!
```

---

## Accessing Results

### Web Dashboards
```
Grafana:       http://localhost:3000          (admin/admin)
Prometheus:    http://localhost:9090
Alertmanager:  http://localhost:9093
```

### Command Line
```bash
# View logs from specific service
docker logs ml-obs-data-generator
docker logs ml-obs-drift-service

# Query metrics
curl http://localhost:8000/metrics | grep drift_

# Test API endpoints
curl http://localhost:8001/health
curl -X POST http://localhost:8002/replay?limit=5

# Check database
docker exec ml-obs-postgres psql -U mlobs -d ml_observability \
  -c "SELECT COUNT(*) FROM ml_events;"
```

---

## Differences: demo.sh vs demo.bat

### demo.sh (Bash)
- **Uses:** Color-coded output with ANSI codes
- **Works on:** Linux, Mac, WSL2, Git Bash on Windows
- **Features:** Pipes, background processes, advanced bash features
- **Advantages:** More readable output, proper error handling

### demo.bat (Batch)
- **Uses:** Plain text with markers ([INFO], [SUCCESS], etc.)
- **Works on:** Windows CMD, PowerShell
- **Features:** Native Windows commands only
- **Advantages:** No dependencies, runs natively on Windows

---

## Troubleshooting

### "Docker not found"
```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker compose version
```

### "curl not found" (Windows)
```powershell
# Option 1: Install via winget
winget install -e --id cURL.cURL

# Option 2: Use curl from Git Bash
"C:\Program Files\Git\mingw64\bin\curl.exe" http://localhost:3000
```

### Services not responding after 45 seconds
```bash
# Check if services are actually running
docker ps

# View startup logs
docker compose logs

# Wait longer and try again
sleep 60
docker ps
```

### "Inference API is not responding"
```bash
# Check if service started correctly
docker logs ml-obs-inference-api

# Verify port is not in use
lsof -i :8001  # Linux/Mac
netstat -ano | findstr :8001  # Windows
```

### Demo crashes on demo.bat
```batch
REM Make sure you're running from project root
cd c:\path\to\ml-observability-platform

REM Run with explicit path
call scripts\demo.bat

REM Or use WSL2 bash instead
bash scripts/demo.sh
```

---

## What Changed from Original

### Original (Podman + Mac)
```bash
# Used podman-compose
podman-compose down
podman-compose up -d

# Used DataGenerator class
python3 /tmp/run_generator.py

# Mac-specific paths and setup
```

### Updated (Docker + Windows)
```bash
# Uses docker compose
docker compose down
docker compose build --quiet
docker compose up -d

# Uses Docker service
docker compose -f docker-compose.yml -f docker-compose.drift.yml up -d data-generator

# Windows-compatible setup
```

---

## Performance Notes

### Demo Runtime
- **Total time:** ~5 minutes
- **Baseline phase:** 1 minute
- **Drift phase:** 1.5 minutes
- **Overhead:** ~1.5 minutes (startup, checks, output)

### Resource Usage
- **CPU:** ~2-3 cores during processing
- **Memory:** ~1.5-2GB
- **Network:** ~50MB data transferred
- **Disk:** ~500MB (temporary files)

---

## Next Steps After Demo

1. **Access Grafana:** http://localhost:3000
   - Create custom dashboards
   - Set alert thresholds
   - Configure notifications

2. **Review Prometheus Metrics:** http://localhost:9090
   - Query available metrics
   - Create alert rules
   - Check scrape status

3. **Check Data Persistence:** 
   - Query PostgreSQL events
   - Verify Redis stream
   - Review Prometheus TSDB

4. **Test APIs Directly:**
   - `/predict` endpoint for predictions
   - `/replay` endpoint for comparisons
   - `/health` endpoints for status

---

## Cleanup

### Stop Services (Keep Data)
```bash
cd infra
docker compose down
```

### Stop Services & Remove Data
```bash
cd infra
docker compose down -v
```

### Remove Images
```bash
docker rmi infra-data-generator infra-inference-api \
  infra-drift-service infra-replay-service infra-webhook-receiver
```

---

## Support

For issues or questions:
- Check `DOCKER_SETUP_GUIDE.md` for detailed configuration
- Review `DOCKER_MIGRATION_VALIDATION.md` for validation procedures
- Check service logs: `docker compose logs -f <service>`
- Verify Docker is running: `docker ps`

---

**Updated:** 2026-04-29  
**Platform:** Windows + Docker  
**Scripts:** demo.sh (Bash) & demo.bat (Batch)
