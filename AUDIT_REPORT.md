# Code Audit & Testing Validation Report

## Executive Summary

**Confidence: HIGH**

The ML Observability Platform is mostly functional but has **7 critical and medium-priority issues** that must be addressed:

1. **CRITICAL**: Missing `/metrics` endpoint in inference-api (causes Prometheus scrape failures)
2. **CRITICAL**: Feature parsing mismatch - data-generator includes `is_premium_user` field which breaks drift detection
3. **MEDIUM**: Consumer event parsing doesn't handle data-generator format correctly (missing feature_3)
4. **MEDIUM**: Pydantic warning in replay-service about protected namespace
5. **MEDIUM**: Replay service uses GET instead of POST (HTTP 405 error visible in logs)
6. **LOW**: Event database schema mismatch with stream event structure
7. **LOW**: Missing error handling in API responses

---

## Issue Details

### 1. CRITICAL: Missing `/metrics` Endpoint in Inference API

**Location**: `inference-api/main.py`

**Problem**: 
- Prometheus scrapes `/metrics` endpoint but inference-api doesn't expose it
- Result: Prometheus shows inference-api as DOWN with HTTP 404 errors
- Impact: Observability is broken for inference service

**Evidence**:
```
GET /metrics HTTP/1.1" 404 Not Found  (repeated 30+ times in logs)
Prometheus status: inference-api 0/1 DOWN
```

**Fix Required**: Add Prometheus metrics endpoint
```python
from prometheus_client import generate_latest, REGISTRY

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )
```

---

### 2. CRITICAL: Feature Parsing Mismatch

**Location**: `consumer.py`, `data-generator/generator.py`

**Problem**:
- data-generator creates features with `is_premium_user` boolean field
- Consumer expects features dict with only feature_1, feature_2, feature_3 (floats)
- drift.py tries to convert `is_premium_user` to float, breaking comparison
- Result: Drift detection logic may fail on non-numeric fields

**Evidence**:
```json
// From Redis stream
"features": {"feature_1": 1.1545, "feature_2": -0.8064, "is_premium_user": true}
```

**Data Flow Issue**:
```
data-generator (3 features + 1 boolean) → Redis → consumer (expects only floats) → drift detection
```

**Fix Required**: 
- Option A: Remove `is_premium_user` from data-generator
- Option B: Filter it out in consumer parsing

---

### 3. MEDIUM: Consumer Event Parsing - Missing Feature_3

**Location**: `consumer.py` line 159-161

**Problem**:
- data-generator only generates feature_1 and feature_2
- Consumer tries to parse feature_3 which doesn't exist
- `float(event.get('feature_3', 0.0))` silently defaults to 0.0
- Result: All feature_3 values are 0.0, breaking drift detection

**Evidence**:
```python
# From data-generator - only generates 2 features
"feature_1": round(feature_1, 4),
"feature_2": round(feature_2, 4),
"is_premium_user": bool(np.random.choice([True, False]))

# But consumer expects 3
'feature_3': float(features_data.get('feature_3', 0.0))
```

**Impact**: Feature_3 drift detection always shows zero values (no variance)

---

### 4. MEDIUM: Pydantic Protected Namespace Warning

**Location**: `replay-service/main.py` line 52

**Problem**:
- Pydantic warns about `model_version` field in ReplayResponse model
- This is not an error but indicates potential future incompatibility

**Evidence**:
```
UserWarning: Field "model_version" has conflict with protected namespace "model_"
```

**Fix**: Add model config to suppress warning or rename field

---

### 5. MEDIUM: HTTP Method Mismatch in Replay Service

**Location**: `replay-service/main.py` line 183

**Problem**:
- API endpoint defined as POST: `@app.post("/replay", ...)`
- But logs show GET request: `GET /replay?limit=3 HTTP/1.1" 405`
- Client incorrectly uses GET instead of POST
- Result: External users may be confused about required HTTP method

**Evidence**:
```
2026-04-29 10:17:46 - INFO - GET /replay?limit=3 HTTP/1.1" 405 Method Not Allowed
2026-04-29 10:17:46 - INFO - POST /replay?limit=3 HTTP/1.1" 200 OK  (works)
```

**Note**: This is a client-side issue, not a service issue. Endpoint is correct.

---

### 6. LOW: Event Database Schema Mismatch

**Location**: `db.py` line 107-114

**Problem**:
- Database expects `timestamp` as TIMESTAMP type
- Consumer provides ISO 8601 string: `"2026-04-29T10:13:55.091870+00:00"`
- PostgreSQL may have issues with timezone-aware strings
- Schema should explicitly handle timezone

**Fix**: Update database schema:
```sql
CREATE TABLE IF NOT EXISTS ml_events (
    request_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE,  -- Add WITH TIME ZONE
    model_version TEXT,
    ...
)
```

---

### 7. LOW: API Error Responses

**Location**: Multiple files

**Problem**:
- Errors don't always include structured error codes
- Some exceptions may expose internal implementation details
- No rate limiting or request validation

**Impact**: Low severity, operational concern

---

## Runtime Verification Results

### Service Health Status
```
✓ redis:6379                 - Healthy
✓ postgres:5432              - Healthy  
✓ prometheus:9090            - Healthy
✓ drift-service:8000         - Healthy
✓ data-generator             - Running & generating events
✗ inference-api:8001         - Unhealthy (missing /metrics)
✓ replay-service:8002        - Healthy
✓ grafana:3000               - Healthy
```

### Data Flow Validation
```
✓ data-generator → Redis (events are being produced)
✓ Redis → drift-service (events are being consumed)
✓ drift-service → PostgreSQL (events being persisted)
✓ drift-service → Prometheus (metrics endpoint working at 8000)
✗ inference-api → Prometheus (404 error on /metrics)
✓ replay-service → inference-api (predictions replaying)
```

### Event Processing
```
Events in ml-events stream:  ~400+ events
Drift alerts published:      Working (alerts visible in logs)
Database storage:            Working
Metrics collection:          Partial (inference-api broken)
```

---

## Required Fixes (Priority Order)

### P1 (Critical)
1. Add `/metrics` endpoint to inference-api
2. Fix feature parsing in data-generator or consumer

### P2 (Medium)
3. Update database schema timestamp type
4. Add Pydantic model config to replay-service
5. Add prometheus-client dependency to inference-api

### P3 (Low)
6. Improve API error handling
7. Add request validation

---

## Testing Notes

- All services start successfully except inference-api (unhealthy due to /metrics)
- Event generation: ~2 events/sec consistently
- Drift detection: Working, alerts being published
- Data persistence: Working
- API endpoints: Mostly working except missing /metrics in inference-api

---

## Recommendations

1. **Immediate**: Deploy fix for `/metrics` endpoint (estimated: 5 minutes)
2. **Immediate**: Resolve feature field mismatch (estimated: 10 minutes)
3. **Before Production**: Add test suite to validate data flow
4. **Before Production**: Add integration tests for API endpoints

---

Generated: 2026-04-29 10:30 UTC
Confidence Level: **HIGH**
