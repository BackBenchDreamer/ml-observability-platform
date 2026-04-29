#!/usr/bin/env python3
import json
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import numpy as np
import redis

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
ENABLE_DRIFT = os.getenv("ENABLE_DRIFT", "false").lower() == "true"
EVENT_INTERVAL = float(os.getenv("EVENT_INTERVAL", 1.0))
STREAM_NAME = os.getenv("STREAM_NAME", "ml-events")

NORMAL_MEAN = 0.0
NORMAL_STD = 1.0
DRIFT_MEAN = 5.0
DRIFT_STD = 1.0

shutdown_flag = False


def signal_handler(signum, _frame):
    global shutdown_flag
    logger.info("Received signal %s; shutting down", signum)
    shutdown_flag = True


def generate_features(drift_mode: bool) -> Dict[str, Any]:
    mean = DRIFT_MEAN if drift_mode else NORMAL_MEAN
    std = DRIFT_STD if drift_mode else NORMAL_STD
    return {
        "feature_1": round(float(np.random.normal(mean, std)), 4),
        "feature_2": round(float(np.random.normal(mean, std)), 4),
        "feature_3": round(float(np.random.normal(mean, std)), 4),
    }


def generate_prediction() -> Dict[str, Any]:
    return {
        "label": int(np.random.choice([0, 1])),
        "confidence": round(float(np.random.uniform(0.7, 0.99)), 4),
    }


def generate_metadata() -> Dict[str, Any]:
    return {
        "latency_ms": round(float(np.random.uniform(10.0, 100.0)), 2),
        "environment": "production",
        "region": np.random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
    }


def generate_event(drift_mode: bool) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1.0.0",
        "features": generate_features(drift_mode),
        "prediction": generate_prediction(),
        "metadata": generate_metadata(),
    }


def connect_redis(max_retries: int = 5, retry_delay: int = 2) -> redis.Redis:
    for attempt in range(1, max_retries + 1):
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            client.ping()
            logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
            return client
        except redis.ConnectionError as error:
            if attempt == max_retries:
                raise
            logger.warning("Redis connection attempt %s/%s failed: %s", attempt, max_retries, error)
            time.sleep(retry_delay)


def publish_event(redis_client: redis.Redis, event: Dict[str, Any]) -> str:
    event_json = json.dumps(event)
    entry_id = redis_client.xadd(STREAM_NAME, {"event": event_json})
    return entry_id.decode("utf-8") if isinstance(entry_id, bytes) else entry_id


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(
        "Starting generator (redis=%s:%s stream=%s interval=%.2fs drift=%s)",
        REDIS_HOST,
        REDIS_PORT,
        STREAM_NAME,
        EVENT_INTERVAL,
        ENABLE_DRIFT,
    )

    try:
        redis_client = connect_redis()
    except redis.ConnectionError:
        logger.error("Unable to connect to Redis")
        sys.exit(1)

    emitted = 0
    window_start = time.time()
    report_interval_seconds = 10

    while not shutdown_flag:
        try:
            publish_event(redis_client, generate_event(ENABLE_DRIFT))
            emitted += 1

            now = time.time()
            elapsed = now - window_start
            if elapsed >= report_interval_seconds:
                logger.info("Published %s events in %.1fs", emitted, elapsed)
                emitted = 0
                window_start = now

            time.sleep(EVENT_INTERVAL)
        except redis.ConnectionError as error:
            logger.warning("Redis publish failed: %s; reconnecting", error)
            try:
                redis_client = connect_redis()
            except redis.ConnectionError:
                logger.error("Redis reconnection failed")
                break
        except redis.RedisError as error:
            logger.error("Redis error: %s", error)
            break

    try:
        redis_client.close()
    except redis.RedisError:
        pass
    logger.info("Generator stopped")


if __name__ == "__main__":
    main()
