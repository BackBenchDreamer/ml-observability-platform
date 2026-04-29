# Quick Reference - Docker ML Observability Platform

## Start the System

```bash
cd infra
docker compose up -d
docker compose logs -f
```

## Check Status

```bash
# View all services
docker ps

# View specific service status
docker compose ps

# Check specific service logs
docker logs ml-obs-redis
docker logs ml-obs-inference-api
docker logs ml-obs-drift-service
docker logs ml-obs-postgres
```

## Verify Pipeline

```bash
# Redis events
docker exec ml-obs-redis redis-cli XLEN ml-events

# PostgreSQL events
docker exec ml-obs-postgres psql -U mlobs -d ml_observability \
  -c "SELECT COUNT(*) FROM ml_events;"

# Drift metrics
curl -s http://localhost:8000/metrics | grep drift_

# Prometheus query
curl -s "http://localhost:9090/api/v1/query?query=drift_events_processed_total"
```

## Test Predictions

```bash
# Make prediction
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}'

# Replay service
curl -X POST "http://localhost:8002/replay?limit=5"

# Test webhook
curl http://localhost:5000/health
```

## Access Web UIs

```
Grafana:       http://localhost:3000      (admin/admin)
Prometheus:    http://localhost:9090
Alertmanager:  http://localhost:9093
Inference API: http://localhost:8001
Drift Service: http://localhost:8000/metrics
```

## Stop & Cleanup

```bash
# Stop services (keep data)
docker compose down

# Stop and remove volumes (delete all data)
docker compose down -v

# Restart services
docker compose restart

# Rebuild images
docker compose build --no-cache
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | `lsof -i :8001` or change port in docker-compose.yml |
| Services won't start | Check logs: `docker logs <service>` |
| Redis not connecting | Verify: `docker exec ml-obs-redis redis-cli ping` |
| PostgreSQL error | Check: `docker exec ml-obs-postgres pg_isready -U mlobs` |
| Empty metrics | Wait 15+ seconds for first Prometheus scrape |
| Permission denied | Run Docker as Administrator (Windows) |

## Enable Drift Mode

1. Edit `infra/docker-compose.yml`
2. Change `ENABLE_DRIFT: "false"` → `ENABLE_DRIFT: "true"`
3. Run: `docker compose up -d --build`
4. Monitor: `docker logs -f ml-obs-drift-service`

## Resource Monitoring

```bash
# Real-time stats
docker stats

# Stats for specific services
docker stats ml-obs-redis ml-obs-postgres ml-obs-drift-service

# Detailed info about container
docker inspect ml-obs-drift-service
```

## Database Operations

```bash
# Connect to PostgreSQL
docker exec -it ml-obs-postgres psql -U mlobs -d ml_observability

# List tables
\dt

# Query events
SELECT COUNT(*) FROM ml_events;
SELECT request_id, timestamp, model_version FROM ml_events LIMIT 5;

# Export data
docker exec ml-obs-postgres pg_dump -U mlobs ml_observability > backup.sql

# Check table structure
\d ml_events
```

## Redis Operations

```bash
# Connect to Redis CLI
docker exec -it ml-obs-redis redis-cli

# Check stream
XLEN ml-events

# View stream entries
XRANGE ml-events - +

# Get consumer group info
XINFO GROUPS ml-events
```

## Docker Compose Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f [service]

# Execute command
docker compose exec <service> <command>

# Restart service
docker compose restart <service>

# Rebuild image
docker compose build <service>

# Pull latest images
docker compose pull

# View configuration
docker compose config

# Validate configuration
docker compose config --quiet
```

## Troubleshooting Quick Links

- **Setup Issues:** See DOCKER_SETUP_GUIDE.md
- **Validation:** See DOCKER_MIGRATION_VALIDATION.md
- **Changes Made:** See CHANGES.md
- **Final Report:** See FINAL_REPORT.md

---

**Last Updated:** 2026-04-29  
**Status:** ✅ All systems operational
