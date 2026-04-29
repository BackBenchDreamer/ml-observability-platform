import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import Counter, Histogram, REGISTRY, generate_latest
from pydantic import BaseModel, Field

from model import get_model

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Inference API",
    description="Inference service with Redis event streaming",
    version="1.0.0",
)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_STREAM = os.getenv("REDIS_STREAM", "ml-events")

redis_client = None

predictions_total = Counter(
    "inference_predictions_total",
    "Total number of predictions made",
)

prediction_latency = Histogram(
    "inference_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=[0.001, 0.01, 0.1, 0.5, 1.0],
)

redis_publish_errors = Counter(
    "inference_redis_publish_errors_total",
    "Total number of Redis publish errors",
)


class PredictionRequest(BaseModel):
    feature_1: float = Field(..., description="First feature value")
    feature_2: float = Field(..., description="Second feature value")
    feature_3: float = Field(default=0.0, description="Third feature value")

    class Config:
        json_schema_extra = {
            "example": {"feature_1": 0.5, "feature_2": 1.2, "feature_3": 0.8}
        }


class PredictionResponse(BaseModel):
    request_id: str
    prediction: Dict[str, Any]
    model_version: str
    latency_ms: float


def get_redis_client():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            redis_client.ping()
            logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
        except redis.RedisError as error:
            logger.error("Redis connection failed: %s", error)
            redis_client = None
    return redis_client


def publish_event_to_redis(event_data: Dict[str, Any]) -> bool:
    client = get_redis_client()
    if client is None:
        redis_publish_errors.inc()
        return False

    try:
        client.xadd(REDIS_STREAM, {"event": json.dumps(event_data)})
        return True
    except redis.RedisError as error:
        redis_publish_errors.inc()
        logger.error("Failed publishing event to Redis: %s", error)
        return False


@app.on_event("startup")
async def startup_event():
    logger.info("Starting inference API")
    get_model()
    get_redis_client()


@app.get("/health")
async def health_check():
    redis_status = "connected" if get_redis_client() is not None else "disconnected"
    return {
        "status": "healthy",
        "service": "inference-api",
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        model = get_model()
        features = {
            "feature_1": request.feature_1,
            "feature_2": request.feature_2,
            "feature_3": request.feature_3,
        }

        prediction = model.predict(features)
        duration = time.time() - start_time
        latency_ms = round(duration * 1000, 2)

        event_data = {
            "schema_version": "1.0",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_version": model.model_version,
            "features": features,
            "prediction": prediction,
            "metadata": {
                "latency_ms": latency_ms,
                "environment": os.getenv("ENVIRONMENT", "production"),
                "region": "local",
            },
        }

        publish_event_to_redis(event_data)
        predictions_total.inc()
        prediction_latency.observe(duration)

        return PredictionResponse(
            request_id=request_id,
            prediction=prediction,
            model_version=model.model_version,
            latency_ms=latency_ms,
        )
    except Exception as error:
        logger.error("Prediction failed: %s", error)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {error}")


@app.get("/")
async def root():
    return {
        "service": "ML Inference API",
        "version": "1.0.0",
        "endpoints": {"health": "/health", "predict": "/predict (POST)", "docs": "/docs"},
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, log_level="info", reload=False)
