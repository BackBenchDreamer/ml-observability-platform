@echo off
REM ML Observability Platform - Demo Script for Windows
REM Updated for Docker on Windows
REM Original: Podman on Mac | Modified: Docker on Windows

setlocal enabledelayedexpansion

REM Color codes (simulated with different echo styles)
REM We'll use simple text markers instead since Windows batch doesn't have ANSI colors by default

echo.
echo ================================================================
echo      ML Observability Platform - Docker Demo (Windows)
echo ================================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Please install Docker Desktop.
    pause
    exit /b 1
)

REM Check if curl is installed
curl --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] curl not found. Please install it first.
    pause
    exit /b 1
)

echo [SUCCESS] Docker and curl are available
echo.

REM 1. Start system
echo [STEP] Starting ML Observability Platform with Docker...
cd infra

echo [INFO] Stopping any existing containers...
docker compose down 2>nul

echo [INFO] Building images...
docker compose build --quiet 2>nul

echo [INFO] Starting services (docker compose up -d)...
docker compose up -d
if errorlevel 1 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)

cd ..
echo [SUCCESS] Services started
echo.

REM 2. Wait for services to initialize
echo [STEP] Waiting for services to initialize (45 seconds)...
timeout /t 45 /nobreak
echo.

REM 3. Check service health
echo [STEP] Checking service health...
echo.

REM Check Redis
echo [INFO] Checking Redis...
docker exec ml-obs-redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis is not responding
    pause
    exit /b 1
)
echo [SUCCESS] Redis is healthy

REM Check PostgreSQL
echo [INFO] Checking PostgreSQL...
docker exec ml-obs-postgres pg_isready -U mlobs -d ml_observability >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL is not responding
    pause
    exit /b 1
)
echo [SUCCESS] PostgreSQL is healthy

REM Check Prometheus
echo [INFO] Checking Prometheus...
curl -s http://localhost:9090/-/healthy >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Prometheus is not responding
    pause
    exit /b 1
)
echo [SUCCESS] Prometheus is healthy

REM Check Grafana
echo [INFO] Checking Grafana...
curl -s http://localhost:3000/api/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Grafana is not responding
    pause
    exit /b 1
)
echo [SUCCESS] Grafana is healthy

REM Check Inference API (port 8001)
echo [INFO] Checking Inference API...
setlocal enabledelayedexpansion
for /l %%i in (1,1,10) do (
    curl -s http://localhost:8001/health >nul 2>&1
    if not errorlevel 1 (
        echo [SUCCESS] Inference API is healthy
        goto inference_ok
    )
    if %%i lss 10 (
        timeout /t 3 /nobreak >nul
    )
)
echo [ERROR] Inference API is not responding
pause
exit /b 1

:inference_ok

REM Check Drift Service (port 8000)
echo [INFO] Checking Drift Service...
for /l %%i in (1,1,10) do (
    curl -s http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        echo [SUCCESS] Drift Service is healthy
        goto drift_ok
    )
    if %%i lss 10 (
        timeout /t 3 /nobreak >nul
    )
)
echo [ERROR] Drift Service is not responding
pause
exit /b 1

:drift_ok

REM Check Replay Service (port 8002)
echo [INFO] Checking Replay Service...
curl -s http://localhost:8002/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Replay Service is not responding
    pause
    exit /b 1
)
echo [SUCCESS] Replay Service is healthy

REM Check Webhook Receiver (port 5000)
echo [INFO] Checking Webhook Receiver...
curl -s http://localhost:5000/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Webhook Receiver is not responding
    pause
    exit /b 1
)
echo [SUCCESS] Webhook Receiver is healthy

echo [SUCCESS] All services are healthy
echo.

REM 4. Monitor data generation in normal mode
echo [STEP] Monitoring data pipeline in normal mode...
echo [INFO] The data-generator service is running continuously in Docker
echo [INFO] Collecting baseline metrics for 60 seconds...
echo.

for /l %%i in (1,1,6) do (
    echo.
    echo [BASELINE - %%i0s]

    for /f %%a in ('docker exec ml-obs-redis redis-cli XLEN ml-events 2^>nul') do set REDIS_COUNT=%%a
    for /f %%b in ('docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2^>nul') do set PG_COUNT=%%b

    echo   Redis stream events: !REDIS_COUNT!
    echo   PostgreSQL stored:   !PG_COUNT!

    if %%i lss 6 (
        timeout /t 10 /nobreak >nul
    )
)

echo.
echo [SUCCESS] Baseline metrics collected
echo.

REM 5. Check current inference metrics
echo [STEP] Checking current inference metrics...
echo [INFO] Testing inference API prediction...
echo.

curl -s -X POST http://localhost:8001/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"feature_1\": 0.5, \"feature_2\": 1.2, \"feature_3\": 0.8}" | python3 -m json.tool 2>nul

echo.

REM 6. Enable drift mode
echo [STEP] Enabling drift mode...
echo [INFO] Restarting data-generator with ENABLE_DRIFT=true...
echo.

REM Create drift override file
(
    echo version: '3.8'
    echo services:
    echo   data-generator:
    echo     environment:
    echo       ENABLE_DRIFT: "true"
) > infra\docker-compose.drift.yml

docker compose -f infra/docker-compose.yml -f infra/docker-compose.drift.yml up -d data-generator
echo [SUCCESS] Drift mode enabled
echo.

REM 7. Monitor drift detection
echo [STEP] Monitoring drift detection ^(90 seconds^)...
echo [INFO] Watching metrics for drift signals...
echo.

for /l %%i in (1,1,9) do (
    echo.
    echo [DRIFT DETECTION - %%i0s]

    for /f %%a in ('docker exec ml-obs-redis redis-cli XLEN ml-events 2^>nul') do set REDIS_COUNT=%%a
    for /f %%b in ('docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2^>nul') do set PG_COUNT=%%b

    echo   Redis stream events: !REDIS_COUNT!
    echo   PostgreSQL stored:   !PG_COUNT!
    echo   Drift metrics:

    curl -s http://localhost:8000/metrics 2>nul | findstr "drift_detected_total ml_drift_score" | findstr /v "#" >nul
    if not errorlevel 1 (
        curl -s http://localhost:8000/metrics 2>nul | findstr "drift_detected_total ml_drift_score" | findstr /v "#"
    ) else (
        echo     No drift detected yet
    )

    if %%i lss 9 (
        timeout /t 10 /nobreak >nul
    )
)

echo.
echo [SUCCESS] Drift detection period complete
echo.

REM 8. Disable drift mode
echo [STEP] Restoring normal mode...
echo [INFO] Removing drift override configuration...
echo.

del infra\docker-compose.drift.yml 2>nul
docker compose -f infra/docker-compose.yml up -d data-generator

echo [SUCCESS] Normal mode restored
echo.

REM 9. Call replay API
echo [STEP] Calling replay service to compare predictions...
echo [INFO] Replaying last 10 predictions...
echo.

echo [REPLAY RESULTS]
curl -s -X POST "http://localhost:8002/replay?limit=10" | python3 -m json.tool 2>nul

echo.

REM 10. Check alerts
echo [STEP] Checking alerts received...
echo [INFO] Recent webhook-receiver logs...
echo.

docker logs ml-obs-webhook-receiver 2>&1 | findstr /i "alert drift" | findstr /v "^$"
if errorlevel 1 (
    echo (No alerts received yet - alerts require drift threshold to be exceeded)
)

echo.

REM 11. Print summary
echo.
echo ================================================================
echo                    DEMO SUMMARY
echo ================================================================
echo.

echo [SERVICES RUNNING]
echo   * Prometheus:         http://localhost:9090
echo   * Grafana:            http://localhost:3000 (admin/admin)
echo   * Inference API:      http://localhost:8001
echo   * Drift Service:      http://localhost:8000
echo   * Replay Service:     http://localhost:8002
echo   * Webhook Receiver:   http://localhost:5000
echo   * Alertmanager:       http://localhost:9093

echo.
echo [WHAT HAPPENED]
echo   1. ^/ Started all services with docker compose
echo   2. ^/ Verified service health
echo   3. ^/ Monitored baseline traffic from data-generator
echo   4. ^/ Enabled drift mode in data-generator
echo   5. ^/ Drift detection system analyzed distribution shift
echo   6. ^/ Replay service compared predictions
echo   7. ^/ Webhook receiver monitored for alerts

for /f %%a in ('docker exec ml-obs-redis redis-cli XLEN ml-events 2^>nul') do set FINAL_REDIS=%%a
for /f %%b in ('docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2^>nul') do set FINAL_PG=%%b

echo.
echo [FINAL METRICS]
echo   * Total events generated: !FINAL_REDIS!
echo   * Events persisted:       !FINAL_PG!

echo.
echo [NEXT STEPS]
echo   * View dashboards in Grafana: http://localhost:3000
echo   * Check Prometheus metrics: http://localhost:9090
echo   * Review alerts in Alertmanager: http://localhost:9093
echo   * Query drift metrics: curl http://localhost:8000/metrics ^| findstr drift_
echo   * Test replay API: curl -X POST http://localhost:8002/replay?limit=5
echo   * View logs: docker compose logs -f [service]

echo.
echo [TO STOP THE SYSTEM]
echo   cd infra ^&^& docker compose down

echo.
echo [TO CLEAN UP EVERYTHING]
echo   cd infra ^&^& docker compose down -v

echo.
echo ================================================================
echo.

echo [SUCCESS] Demo script completed successfully!
echo.
pause
