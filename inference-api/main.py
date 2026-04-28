"""
Inference API Service
FastAPI application for ML model predictions with Redis event streaming
"""
import os
import uuid
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis
import uvicorn

from model import get_model

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Inference API",
    description="Inference service with Redis event streaming",
    version="1.0.0"
)

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_STREAM = "ml-events"

# Initialize Redis client
redis_client = None


def get_redis_client():
    """Get or create Redis client"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5
            )
            redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            redis_client = None
    return redis_client


# Pydantic models for request/response
class PredictionRequest(BaseModel):
    """Request model for predictions"""
    feature_1: float = Field(..., description="First feature value")
    feature_2: float = Field(..., description="Second feature value")
    feature_3: float = Field(default=0.0, description="Third feature value")
    
    class Config:
        json_schema_extra = {
            "example": {
                "feature_1": 0.5,
                "feature_2": 1.2,
                "feature_3": 0.8
            }
        }


class PredictionResponse(BaseModel):
    """Response model for predictions"""
    request_id: str
    prediction: Dict[str, Any]
    model_version: str
    latency_ms: float


def publish_event_to_redis(event_data: dict) -> bool:
    """
    Publish prediction event to Redis Stream
    
    Args:
        event_data: Event data matching event_schema.json
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        if client is None:
            logger.warning("Redis client not available, skipping event publish")
            return False
        
        # Convert event data to flat string dict for Redis
        event_dict = {
            "request_id": event_data["request_id"],
            "timestamp": event_data["timestamp"],
            "model_version": event_data["model_version"],
            "features": json.dumps(event_data["features"]),
            "prediction": json.dumps(event_data["prediction"]),
            "metadata": json.dumps(event_data["metadata"])
        }
        
        # Add to Redis Stream
        message_id = client.xadd(REDIS_STREAM, event_dict)
        logger.info(f"Published event to Redis Stream: {message_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish event to Redis: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    """Initialize model and Redis connection on startup"""
    logger.info("Starting Inference API service...")
    
    # Load model
    try:
        model = get_model()
        logger.info(f"Model loaded: {model.model_id} v{model.model_version}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    
    # Test Redis connection
    get_redis_client()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if get_redis_client() is not None else "disconnected"
    
    return {
        "status": "healthy",
        "service": "inference-api",
        "redis": redis_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Make prediction and publish event to Redis
    
    Args:
        request: Prediction request with features
        
    Returns:
        Prediction response with label and confidence
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Get model
        model = get_model()
        
        # Prepare features
        features = {
            "feature_1": request.feature_1,
            "feature_2": request.feature_2,
            "feature_3": request.feature_3
        }
        
        # Make prediction
        prediction = model.predict(features)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Prepare event data matching event_schema.json
        event_data = {
            "schema_version": "1.0",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_version": model.model_version,
            "features": features,
            "prediction": prediction,
            "metadata": {
                "latency_ms": round(latency_ms, 2),
                "environment": os.getenv("ENVIRONMENT", "production"),
                "region": "local"
            }
        }
        
        # Publish to Redis Stream
        publish_event_to_redis(event_data)
        
        # Return response
        return PredictionResponse(
            request_id=request_id,
            prediction=prediction,
            model_version=model.model_version,
            latency_ms=round(latency_ms, 2)
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ML Inference API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )

# Made with Bob
