"""
Replay Service - Model Comparison and Replay
Fetches historical events and replays them through inference API for comparison
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Replay Service",
    description="Replay historical events through inference API for model comparison",
    version="1.0.0"
)

# Configuration
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'ml_observability')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'mlobs')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'mlobs_pass')
INFERENCE_API_URL = os.getenv('INFERENCE_API_URL', 'http://localhost:8001')
MAX_BATCH_SIZE = 50


class ComparisonResult(BaseModel):
    """Model for comparison result"""
    request_id: str
    old_prediction: Dict[str, Any]
    new_prediction: Dict[str, Any]
    confidence_diff: float


class ReplayResponse(BaseModel):
    """Response model for replay endpoint"""
    replayed_count: int
    comparisons: List[ComparisonResult]
    model_version: Optional[str] = None

    model_config = {"protected_namespaces": ()}


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")


def fetch_events(limit: int = 50, model_version: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch events from database
    
    Args:
        limit: Maximum number of events to fetch (capped at MAX_BATCH_SIZE)
        model_version: Optional model version filter
        
    Returns:
        List of event dictionaries
    """
    limit = min(limit, MAX_BATCH_SIZE)
    conn = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if model_version:
            cursor.execute("""
                SELECT request_id, timestamp, model_version, features, prediction, metadata
                FROM ml_events
                WHERE model_version = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (model_version, limit))
        else:
            cursor.execute("""
                SELECT request_id, timestamp, model_version, features, prediction, metadata
                FROM ml_events
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))
        
        rows = cursor.fetchall()
        events = []
        for row in rows:
            events.append({
                'request_id': row['request_id'],
                'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None,
                'model_version': row['model_version'],
                'features': row['features'],
                'prediction': row['prediction'],
                'metadata': row['metadata']
            })
        
        cursor.close()
        return events
        
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")
    finally:
        if conn:
            conn.close()


async def replay_event(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replay event through inference API
    
    Args:
        features: Feature dictionary
        
    Returns:
        Prediction result from inference API
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{INFERENCE_API_URL}/predict",
                json=features
            )
            response.raise_for_status()
            result = response.json()
            return result['prediction']
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during replay: {e}")
        raise HTTPException(status_code=502, detail=f"Inference API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error during replay: {e}")
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Test database connection
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    # Test inference API connection
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{INFERENCE_API_URL}/health")
            inference_status = "connected" if response.status_code == 200 else "error"
    except:
        inference_status = "disconnected"
    
    return {
        "status": "healthy",
        "service": "replay-service",
        "database": db_status,
        "inference_api": inference_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/replay", response_model=ReplayResponse)
async def replay_events(
    model_version: Optional[str] = Query(None, description="Filter events by model version"),
    limit: int = Query(50, ge=1, le=MAX_BATCH_SIZE, description="Number of events to replay")
):
    """
    Replay historical events through inference API and compare predictions
    
    Args:
        model_version: Optional model version to filter events
        limit: Number of events to replay (max 50)
        
    Returns:
        Comparison results with old vs new predictions
    """
    logger.info(f"Replay request: model_version={model_version}, limit={limit}")
    
    # Fetch events from database
    events = fetch_events(limit=limit, model_version=model_version)
    
    if not events:
        return ReplayResponse(
            replayed_count=0,
            comparisons=[],
            model_version=model_version
        )
    
    # Replay events and compare predictions
    comparisons = []
    for event in events:
        try:
            # Get old prediction
            old_prediction = event['prediction']
            
            # Replay through inference API
            new_prediction = await replay_event(event['features'])
            
            # Calculate confidence difference
            old_confidence = old_prediction.get('confidence', 0.0)
            new_confidence = new_prediction.get('confidence', 0.0)
            confidence_diff = new_confidence - old_confidence
            
            comparisons.append(ComparisonResult(
                request_id=event['request_id'],
                old_prediction=old_prediction,
                new_prediction=new_prediction,
                confidence_diff=round(confidence_diff, 4)
            ))
            
        except Exception as e:
            logger.error(f"Failed to replay event {event['request_id']}: {e}")
            # Continue with other events
            continue
    
    logger.info(f"Replayed {len(comparisons)} events successfully")
    
    return ReplayResponse(
        replayed_count=len(comparisons),
        comparisons=comparisons,
        model_version=model_version
    )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ML Replay Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "replay": "/replay (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=False
    )

# Made with Bob