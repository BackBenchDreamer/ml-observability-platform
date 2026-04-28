"""
PostgreSQL Database Layer for Event Persistence
Simple implementation for storing ML events
"""
import os
import logging
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import Json
from psycopg2 import pool

logger = logging.getLogger(__name__)


class EventDatabase:
    """Simple PostgreSQL database for event persistence"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        min_connections: int = 1,
        max_connections: int = 5
    ):
        """
        Initialize database connection pool
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
        """
        self.host = host or os.getenv('POSTGRES_HOST', 'localhost')
        self.port = port or int(os.getenv('POSTGRES_PORT', 5432))
        self.database = database or os.getenv('POSTGRES_DB', 'ml_observability')
        self.user = user or os.getenv('POSTGRES_USER', 'mlobs')
        self.password = password or os.getenv('POSTGRES_PASSWORD', 'mlobs_pass')
        
        self.connection_pool: Optional[pool.SimpleConnectionPool] = None
        self.min_connections = min_connections
        self.max_connections = max_connections
        
    def connect(self, max_retries: int = 5, retry_delay: int = 5) -> bool:
        """
        Create connection pool with retry logic
        
        Args:
            max_retries: Maximum connection attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            bool: True if connected successfully
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to PostgreSQL at {self.host}:{self.port} (attempt {attempt + 1}/{max_retries})")
                
                self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                    self.min_connections,
                    self.max_connections,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                
                # Test connection and create table
                conn = self.connection_pool.getconn()
                try:
                    self._create_table(conn)
                    conn.commit()
                    logger.info("Successfully connected to PostgreSQL and initialized schema")
                    return True
                finally:
                    self.connection_pool.putconn(conn)
                    
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached, giving up")
                    return False
        return False
    
    def _create_table(self, conn):
        """
        Create ml_events table if it doesn't exist
        
        Args:
            conn: Database connection
        """
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_events (
                    request_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP,
                    model_version TEXT,
                    features JSONB,
                    prediction JSONB,
                    metadata JSONB
                )
            """)
            # Create index on timestamp for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ml_events_timestamp 
                ON ml_events(timestamp DESC)
            """)
            # Create index on model_version for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ml_events_model_version 
                ON ml_events(model_version)
            """)
            logger.info("Database schema initialized")
        finally:
            cursor.close()
    
    def store_event(self, event: Dict[str, Any]) -> bool:
        """
        Store event in database
        
        Args:
            event: Event dictionary with request_id, timestamp, features, prediction, metadata
            
        Returns:
            bool: True if stored successfully
        """
        if not self.connection_pool:
            logger.warning("Database not connected, skipping event storage")
            return False
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO ml_events (request_id, timestamp, model_version, features, prediction, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (request_id) DO NOTHING
                """, (
                    event['request_id'],
                    event['timestamp'],
                    event.get('model_version', 'unknown'),
                    Json(event['features']),
                    Json(event['prediction']),
                    Json(event.get('metadata', {}))
                ))
                conn.commit()
                return True
            finally:
                cursor.close()
                
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def get_events(
        self,
        limit: int = 50,
        model_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events from database
        
        Args:
            limit: Maximum number of events to retrieve
            model_version: Optional model version filter
            
        Returns:
            List of event dictionaries
        """
        if not self.connection_pool:
            logger.warning("Database not connected")
            return []
        
        conn = None
        try:
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            try:
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
                        'request_id': row[0],
                        'timestamp': row[1].isoformat() if row[1] else None,
                        'model_version': row[2],
                        'features': row[3],
                        'prediction': row[4],
                        'metadata': row[5]
                    })
                return events
            finally:
                cursor.close()
                
        except Exception as e:
            logger.error(f"Failed to retrieve events: {e}")
            return []
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def close(self):
        """Close all connections in pool"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connections closed")

# Made with Bob
