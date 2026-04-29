@echo off
REM Docker ML Observability Platform - Startup Script for Windows

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo ML Observability Platform - Docker Startup Script
echo ================================================================
echo.

REM Check if Docker is installed
docker --version > nul 2>&1
if errorlevel 1 (
    echo [X] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

echo [OK] Docker version:
docker --version
echo [OK] Docker Compose version:
docker compose version
echo.

REM Navigate to infra directory
cd /d "%~dp0infra"

REM Build images
echo [*] Building Docker images...
docker compose build --progress=plain
if errorlevel 1 (
    echo [X] Build failed
    pause
    exit /b 1
)
echo.

REM Start services
echo [*] Starting services...
docker compose up -d
if errorlevel 1 (
    echo [X] Start failed
    pause
    exit /b 1
)
echo.

REM Wait for services
echo [*] Waiting for services to become healthy (60s)...
timeout /t 60 /nobreak
echo.

REM Check status
echo [*] Service Status:
docker compose ps
echo.

REM Validation checks
echo [*] Running validation checks...
echo.

REM Redis
echo -n | set /p temp="Redis connectivity... "
docker exec ml-obs-redis redis-cli ping > nul 2>&1
if errorlevel 1 (
    echo [X] FAILED
) else (
    for /f "tokens=*" %%a in ('docker exec ml-obs-redis redis-cli XLEN ml-events 2^>nul') do (
        echo [OK] ^^(%%a events^^)
    )
)

REM PostgreSQL
echo -n | set /p temp="PostgreSQL connectivity... "
docker exec ml-obs-postgres pg_isready -U mlobs -d ml_observability > nul 2>&1
if errorlevel 1 (
    echo [X] FAILED
) else (
    for /f "tokens=*" %%a in ('docker exec ml-obs-postgres psql -U mlobs -d ml_observability -tc "SELECT COUNT(*) FROM ml_events;" 2^>nul') do (
        set count=%%a
    )
    echo [OK] ^(!count! events^)
)

REM Prometheus
echo -n | set /p temp="Prometheus metrics... "
curl -s http://localhost:9090/api/v1/query?query=up > nul 2>&1
if errorlevel 1 (
    echo [X] FAILED
) else (
    echo [OK]
)

REM Inference API
echo -n | set /p temp="Inference API... "
curl -s http://localhost:8001/health | findstr "healthy" > nul 2>&1
if errorlevel 1 (
    echo [X] FAILED
) else (
    echo [OK]
)

echo.
echo ================================================================
echo [+] ML Observability Platform is ready!
echo ================================================================
echo.
echo Access Points:
echo   * Grafana Dashboard:  http://localhost:3000 (admin/admin)
echo   * Prometheus:         http://localhost:9090
echo   * Alertmanager:       http://localhost:9093
echo   * Inference API:      http://localhost:8001
echo   * Drift Service:      http://localhost:8000
echo   * Replay Service:     http://localhost:8002
echo   * Webhook Receiver:   http://localhost:5000
echo.
echo Commands:
echo   * View logs:          docker compose logs -f [service]
echo   * Stop services:      docker compose down
echo   * Full cleanup:       docker compose down -v
echo.
pause
