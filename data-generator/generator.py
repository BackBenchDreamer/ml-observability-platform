#!/usr/bin/env python3
"""
ML Event Data Generator
Generates synthetic ML inference events and publishes to Redis Streams.
Supports drift simulation for testing observability features.
"""

import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import numpy as np
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
ENABLE_DRIFT = os.getenv('ENABLE_DRIFT', 'false').lower() == 'true'
EVENT_INTERVAL = float(os.getenv('EVENT_INTERVAL', 1.0))
STREAM_NAME = os.getenv('STREAM_NAME', 'ml-events')

# Drift configuration
NORMAL_MEAN = 0.0
NORMAL_STD = 1.0
DRIFT_MEAN = 5.0  # Significant shift to simulate drift
DRIFT_STD = 1.0

# Global flag for graceful shutdown
shutdown_flag = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True


def generate_features(drift_mode: bool) -> Dict[str, Any]:
    """
    Generate synthetic feature data using normal distribution.
    
    Args:
        drift_mode: If True, apply drift by shifting mean significantly
        
    Returns:
        Dictionary containing feature values
    """
    if drift_mode:
        # Drift mode: shift mean to simulate data drift
        feature_1 = float(np.random.normal(DRIFT_MEAN, DRIFT_STD))
        feature_2 = float(np.random.normal(DRIFT_MEAN, DRIFT_STD))
    else:
        # Normal mode: standard normal distribution
        feature_1 = float(np.random.normal(NORMAL_MEAN, NORMAL_STD))
        feature_2 = float(np.random.normal(NORMAL_MEAN, NORMAL_STD))
    
    return {
        "feature_1": round(feature_1, 4),
        "feature_2": round(feature_2, 4),
        "is_premium_user": bool(np.random.choice([True, False]))
    }


def generate_prediction() -> Dict[str, Any]:
    """
    Generate mock prediction values.
    
    Returns:
        Dictionary containing prediction label and confidence
    """
    return {
        "label": int(np.random.choice([0, 1])),
        "confidence": round(float(np.random.uniform(0.7, 0.99)), 4)
    }


def generate_metadata() -> Dict[str, Any]:
    """
    Generate mock metadata values.
    
    Returns:
        Dictionary containing metadata fields
    """
    return {
        "latency_ms": round(float(np.random.uniform(10.0, 100.0)), 2),
        "environment": "production",
        "region": np.random.choice(["us-east-1", "us-west-2", "eu-west-1"])
    }


def generate_event(drift_mode: bool) -> Dict[str, Any]:
    """
    Generate a complete ML event following the schema.
    
    Args:
        drift_mode: If True, generate features with drift
        
    Returns:
        Complete event dictionary
    """
    return {
        "schema_version": "1.0",
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1.0.0",
        "features": generate_features(drift_mode),
        "prediction": generate_prediction(),
        "metadata": generate_metadata()
    }


def connect_redis(max_retries: int = 5, retry_delay: int = 2) -> redis.Redis:
    """
    Connect to Redis with retry logic.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Redis client instance
        
    Raises:
        redis.ConnectionError: If connection fails after all retries
    """
    for attempt in range(1, max_retries + 1):
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=False,  # We'll handle JSON encoding
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            client.ping()
            logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return client
        except redis.ConnectionError as e:
            if attempt < max_retries:
                logger.warning(f"Redis connection attempt {attempt}/{max_retries} failed: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts")
                raise


def publish_event(redis_client: redis.Redis, event: Dict[str, Any]) -> str:
    """
    Publish event to Redis Stream.
    
    Args:
        redis_client: Redis client instance
        event: Event dictionary to publish
        
    Returns:
        Stream entry ID
    """
    event_json = json.dumps(event)
    # Use XADD to add to stream with auto-generated ID
    entry_id = redis_client.xadd(
        STREAM_NAME,
        {'event': event_json}
    )
    return entry_id.decode('utf-8') if isinstance(entry_id, bytes) else entry_id


def main():
    """Main event generation loop."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting ML Event Data Generator")
    logger.info(f"Configuration:")
    logger.info(f"  Redis: {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"  Stream: {STREAM_NAME}")
    logger.info(f"  Event Interval: {EVENT_INTERVAL}s")
    logger.info(f"  Drift Mode: {'ENABLED' if ENABLE_DRIFT else 'DISABLED'}")
    
    if ENABLE_DRIFT:
        logger.warning(f"⚠️  DRIFT MODE ACTIVE - Features will have mean={DRIFT_MEAN} instead of {NORMAL_MEAN}")
    
    # Connect to Redis
    try:
        redis_client = connect_redis()
    except redis.ConnectionError:
        logger.error("Cannot start generator without Redis connection")
        sys.exit(1)
    
    # Event generation loop
    event_count = 0
    last_log_time = time.time()
    log_interval = 10  # Log stats every 10 seconds
    
    try:
        while not shutdown_flag:
            try:
                # Generate and publish event
                event = generate_event(ENABLE_DRIFT)
                entry_id = publish_event(redis_client, event)
                event_count += 1
                
                # Periodic logging
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    rate = event_count / (current_time - last_log_time)
                    logger.info(f"Generated {event_count} events (rate: {rate:.2f} events/sec)")
                    event_count = 0
                    last_log_time = current_time
                
                # Wait before next event
                time.sleep(EVENT_INTERVAL)
                
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                logger.info("Attempting to reconnect...")
                try:
                    redis_client = connect_redis()
                except redis.ConnectionError:
                    logger.error("Reconnection failed, exiting...")
                    break
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                time.sleep(1)  # Brief pause before continuing
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        logger.info("Shutting down generator...")
        try:
            redis_client.close()
        except:
            pass
        logger.info("Generator stopped")


if __name__ == "__main__":
    main()

# Made with Bob
