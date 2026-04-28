"""
Drift Detection Service - Main Orchestrator
Monitors ML events from Redis Stream and detects data/prediction drift
"""
import os
import sys
import json
import time
import signal
import logging
import threading
from datetime import datetime
from typing import Optional
import redis
from fastapi import FastAPI, Response
import uvicorn

from consumer import RedisStreamConsumer
from drift import DriftDetector
from metrics import get_metrics_manager, MetricsManager
from db import EventDatabase

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_flag = threading.Event()

# FastAPI app
app = FastAPI(title="Drift Detection Service")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "drift-detection",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    metrics_manager = get_metrics_manager()
    return Response(
        content=metrics_manager.get_metrics(),
        media_type=metrics_manager.get_content_type()
    )


class DriftService:
    """Main drift detection service orchestrator"""
    
    def __init__(self):
        """Initialize drift service"""
        # Load configuration from environment
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.stream_name = os.getenv('STREAM_NAME', 'ml-events')
        self.alert_stream_name = os.getenv('ALERT_STREAM_NAME', 'ml-alerts')
        self.consumer_group = os.getenv('CONSUMER_GROUP', 'drift-detector')
        self.consumer_name = os.getenv('CONSUMER_NAME', 'drift-worker-1')
        self.baseline_window_size = int(os.getenv('BASELINE_WINDOW_SIZE', 100))
        self.sliding_window_size = int(os.getenv('SLIDING_WINDOW_SIZE', 100))
        self.drift_threshold_psi = float(os.getenv('DRIFT_THRESHOLD_PSI', 0.2))
        self.drift_threshold_ks = float(os.getenv('DRIFT_THRESHOLD_KS', 0.05))
        self.check_interval_ms = int(os.getenv('CHECK_INTERVAL_MS', 1000))
        
        # Initialize components
        self.redis_client: Optional[redis.Redis] = None
        self.consumer: Optional[RedisStreamConsumer] = None
        self.drift_detector: Optional[DriftDetector] = None
        self.metrics_manager: MetricsManager = get_metrics_manager()
        self.event_db: Optional[EventDatabase] = None
        
        logger.info(f"Drift service initialized with config:")
        logger.info(f"  Redis: {self.redis_host}:{self.redis_port}")
        logger.info(f"  Stream: {self.stream_name}")
        logger.info(f"  Alert Stream: {self.alert_stream_name}")
        logger.info(f"  Consumer Group: {self.consumer_group}")
        logger.info(f"  Baseline Window: {self.baseline_window_size}")
        logger.info(f"  Sliding Window: {self.sliding_window_size}")
        logger.info(f"  PSI Threshold: {self.drift_threshold_psi}")
        logger.info(f"  KS Threshold: {self.drift_threshold_ks}")
        
    def connect_redis(self, max_retries: int = 5, retry_delay: int = 5) -> bool:
        """
        Connect to Redis with retry logic
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if connected successfully
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to Redis at {self.redis_host}:{self.redis_port} (attempt {attempt + 1}/{max_retries})")
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=False
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Successfully connected to Redis")
                return True
            except redis.ConnectionError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached, giving up")
                    return False
        return False
        
    def initialize_consumer(self) -> bool:
        """
        Initialize Redis Stream consumer and create consumer group
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            self.consumer = RedisStreamConsumer(
                redis_client=self.redis_client,
                stream_name=self.stream_name,
                consumer_group=self.consumer_group,
                consumer_name=self.consumer_name
            )
            
            # Create consumer group
            self.consumer.create_consumer_group()
            logger.info("Consumer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize consumer: {e}")
            return False
            
    def initialize_database(self) -> bool:
        """
        Initialize PostgreSQL database connection
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            self.event_db = EventDatabase()
            if self.event_db.connect():
                logger.info("Database initialized successfully")
                return True
            else:
                logger.warning("Failed to connect to database, event persistence disabled")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def initialize_drift_detector(self):
        """Initialize drift detector"""
        self.drift_detector = DriftDetector(
            baseline_window_size=self.baseline_window_size,
            sliding_window_size=self.sliding_window_size,
            psi_threshold=self.drift_threshold_psi,
            ks_threshold=self.drift_threshold_ks
        )
        logger.info("Drift detector initialized")
        
    def publish_alert(self, alert_data: dict) -> bool:
        """
        Publish alert to Redis stream
        
        Args:
            alert_data: Alert data dictionary
            
        Returns:
            bool: True if published successfully
        """
        try:
            alert_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Publish to alert stream
            self.redis_client.xadd(
                self.alert_stream_name,
                {'alert': json.dumps(alert_data)}
            )
            
            self.metrics_manager.record_alert_published()
            logger.info(f"Published alert: {alert_data['drift_type']} for {alert_data['feature']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")
            return False
            
    def process_event(self, event: dict):
        """
        Process a single event
        
        Args:
            event: Parsed event dictionary
        """
        start_time = time.time()
        
        try:
            # Persist event to database
            if self.event_db:
                self.event_db.store_event(event)
            
            features = event['features']
            prediction = event['prediction']
            
            # Record prediction count (Phase 5 metric)
            self.metrics_manager.record_prediction()
            
            # Record inference latency if available in metadata (Phase 5 metric)
            metadata = event.get('metadata', {})
            if 'latency_ms' in metadata:
                latency_seconds = metadata['latency_ms'] / 1000.0
                self.metrics_manager.record_inference_latency(latency_seconds)
            
            # Check if baseline is complete
            if not self.drift_detector.is_baseline_ready():
                # Collect baseline samples
                baseline_complete = self.drift_detector.add_baseline_sample(features)
                self.drift_detector.add_baseline_prediction(prediction)
                
                # Update metrics
                baseline_stats = self.drift_detector.get_baseline_stats()
                self.metrics_manager.update_baseline_status(
                    baseline_stats['feature_counts'].get('feature_1', 0),
                    baseline_complete
                )
                
                if baseline_complete:
                    logger.info("Baseline collection complete, starting drift detection")
            else:
                # Add to sliding window
                self.drift_detector.add_sliding_sample(features)
                self.drift_detector.add_sliding_prediction(prediction)
                
                # Update sliding window metrics
                sliding_stats = self.drift_detector.get_sliding_stats()
                self.metrics_manager.update_sliding_window_status(
                    sliding_stats['feature_counts'].get('feature_1', 0)
                )
                
                # Detect drift if sliding window is ready
                if self.drift_detector.is_sliding_window_ready():
                    # Track max drift score for unified ml_drift_score metric
                    max_drift_score = 0.0
                    
                    # Check each feature for drift
                    for feature_name in ['feature_1', 'feature_2', 'feature_3']:
                        drift_result = self.drift_detector.detect_feature_drift(feature_name)
                        
                        if drift_result:
                            # Update metrics
                            self.metrics_manager.update_drift_scores(
                                feature_name,
                                drift_result['psi_score'],
                                drift_result['ks_statistic'],
                                drift_result['p_value']
                            )
                            
                            # Track max drift score (Phase 5 metric)
                            max_drift_score = max(max_drift_score, drift_result['psi_score'])
                            
                            # Publish alert if drift detected
                            if drift_result['drift_detected']:
                                # Determine drift type
                                drift_type = []
                                if drift_result['psi_score'] > self.drift_threshold_psi:
                                    drift_type.append('psi')
                                    self.metrics_manager.record_drift_detected(feature_name, 'psi')
                                if drift_result['p_value'] < self.drift_threshold_ks:
                                    drift_type.append('ks_test')
                                    self.metrics_manager.record_drift_detected(feature_name, 'ks_test')
                                
                                alert_data = {
                                    'drift_type': '+'.join(drift_type),
                                    'feature': feature_name,
                                    'score': drift_result['psi_score'],
                                    'details': {
                                        'ks_statistic': drift_result['ks_statistic'],
                                        'p_value': drift_result['p_value'],
                                        'psi_score': drift_result['psi_score'],
                                        'baseline_mean': drift_result['baseline_mean'],
                                        'baseline_std': drift_result['baseline_std'],
                                        'sliding_mean': drift_result['sliding_mean'],
                                        'sliding_std': drift_result['sliding_std']
                                    }
                                }
                                self.publish_alert(alert_data)
                    
                    # Check prediction drift
                    prediction_drift = self.drift_detector.detect_prediction_drift()
                    if prediction_drift:
                        # Update prediction distribution metrics
                        self.metrics_manager.update_prediction_distribution(
                            prediction_drift['sliding_distribution']
                        )
                        
                        if prediction_drift['drift_detected']:
                            self.metrics_manager.record_drift_detected('prediction', 'prediction')
                            
                            alert_data = {
                                'drift_type': 'prediction',
                                'feature': 'prediction',
                                'score': prediction_drift['psi_score'],
                                'details': {
                                    'psi_score': prediction_drift['psi_score'],
                                    'p_value': prediction_drift['p_value'],
                                    'baseline_distribution': prediction_drift['baseline_distribution'],
                                    'sliding_distribution': prediction_drift['sliding_distribution']
                                }
                            }
                            self.publish_alert(alert_data)
                    
                    # Update unified ml_drift_score (Phase 5 metric)
                    # Use max of feature drift scores as the unified metric
                    self.metrics_manager.update_ml_drift_score(max_drift_score)
            
            # Record processing time
            duration = time.time() - start_time
            self.metrics_manager.record_processing_time(duration)
            self.metrics_manager.record_event_processed()
            
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            
    def run(self):
        """Main service loop"""
        logger.info("Starting drift detection service")
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, exiting")
            sys.exit(1)
            
        # Initialize consumer
        if not self.initialize_consumer():
            logger.error("Failed to initialize consumer, exiting")
            sys.exit(1)
            
        # Initialize database (non-blocking, continues even if fails)
        self.initialize_database()
        
        # Initialize drift detector
        self.initialize_drift_detector()
        
        logger.info("Service started, processing events...")
        
        # Main processing loop
        while not shutdown_flag.is_set():
            try:
                # Read events from stream
                events = self.consumer.read_events(count=10, block=self.check_interval_ms)
                
                # Process each event
                for event in events:
                    if shutdown_flag.is_set():
                        break
                    self.process_event(event)
                    
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(1)
                
        logger.info("Shutting down drift detection service")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown")
    shutdown_flag.set()


def run_fastapi_server(port: int):
    """
    Run FastAPI server in background
    
    Args:
        port: Port to run server on
    """
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        logger.error(f"FastAPI server error: {e}")


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get metrics port
    metrics_port = int(os.getenv('METRICS_PORT', 8000))
    
    # Start FastAPI server in background thread
    logger.info(f"Starting FastAPI server on port {metrics_port}")
    server_thread = threading.Thread(
        target=run_fastapi_server,
        args=(metrics_port,),
        daemon=True
    )
    server_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    # Create and run drift service
    service = DriftService()
    service.run()
    
    logger.info("Service stopped")


if __name__ == "__main__":
    main()

# Made with Bob
