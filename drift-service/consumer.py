"""
Redis Stream Consumer for ML Events
Handles both data-generator and inference-api event formats
"""
import json
import logging
import time
from typing import Dict, Optional, Any
import redis

logger = logging.getLogger(__name__)


class RedisStreamConsumer:
    """Consumer for reading events from Redis Streams with consumer group support"""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        stream_name: str,
        consumer_group: str,
        consumer_name: str
    ):
        """
        Initialize Redis Stream Consumer
        
        Args:
            redis_client: Redis client instance
            stream_name: Name of the Redis stream to consume from
            consumer_group: Consumer group name
            consumer_name: Unique consumer name within the group
        """
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        
    def create_consumer_group(self) -> bool:
        """
        Create consumer group if it doesn't exist
        
        Returns:
            bool: True if group was created or already exists
        """
        try:
            self.redis_client.xgroup_create(
                name=self.stream_name,
                groupname=self.consumer_group,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group '{self.consumer_group}' for stream '{self.stream_name}'")
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group '{self.consumer_group}' already exists")
                return True
            else:
                logger.error(f"Error creating consumer group: {e}")
                raise
                
    def read_events(self, count: int = 1, block: int = 1000) -> list:
        """
        Read events from stream using consumer group
        
        Args:
            count: Maximum number of events to read
            block: Block time in milliseconds (0 for non-blocking)
            
        Returns:
            list: List of parsed event dictionaries
        """
        try:
            # Read from stream using consumer group
            # '>' means read only new messages not yet delivered to other consumers
            messages = self.redis_client.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.stream_name: '>'},
                count=count,
                block=block
            )
            
            if not messages:
                return []
            
            parsed_events = []
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    try:
                        parsed_event = self._parse_event(message_id, message_data)
                        if parsed_event:
                            parsed_events.append(parsed_event)
                            # Acknowledge the message
                            self.redis_client.xack(
                                self.stream_name,
                                self.consumer_group,
                                message_id
                            )
                    except Exception as e:
                        logger.error(f"Error parsing event {message_id}: {e}")
                        # Still acknowledge to avoid reprocessing bad messages
                        self.redis_client.xack(
                            self.stream_name,
                            self.consumer_group,
                            message_id
                        )
                        
            return parsed_events
            
        except Exception as e:
            logger.error(f"Error reading from stream: {e}")
            return []
            
    def _parse_event(self, message_id: bytes, message_data: Dict[bytes, bytes]) -> Optional[Dict[str, Any]]:
        """
        Parse event from Redis stream message
        Handles both data-generator format (single 'event' field) and 
        inference-api format (flattened structure)
        
        Args:
            message_id: Redis message ID
            message_data: Raw message data from Redis
            
        Returns:
            dict: Parsed event with request_id, timestamp, features, prediction
        """
        try:
            # Convert bytes keys to strings
            data = {k.decode('utf-8'): v.decode('utf-8') for k, v in message_data.items()}
            
            # Check if this is data-generator format (single 'event' field)
            if 'event' in data:
                event = json.loads(data['event'])
                return self._parse_data_generator_format(event, message_id)
            else:
                # Inference-API format (flattened structure)
                return self._parse_inference_api_format(data, message_id)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for message {message_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing message {message_id}: {e}")
            return None
            
    def _parse_data_generator_format(self, event: Dict, message_id: bytes) -> Dict[str, Any]:
        """
        Parse data-generator format event

        Args:
            event: Parsed event JSON
            message_id: Redis message ID

        Returns:
            dict: Standardized event format
        """
        features = event.get('features', {})
        features = {
            'feature_1': float(features.get('feature_1', 0.0)),
            'feature_2': float(features.get('feature_2', 0.0)),
            'feature_3': float(features.get('feature_3', 0.0))
        }

        prediction = event.get('prediction', {})
        prediction = {
            'label': int(prediction.get('label', 0)),
            'confidence': float(prediction.get('confidence', 0.0))
        }

        return {
            'message_id': message_id.decode('utf-8'),
            'request_id': event.get('request_id', message_id.decode('utf-8')),
            'timestamp': event.get('timestamp', ''),
            'model_version': event.get('model_version', 'unknown'),
            'features': features,
            'prediction': prediction,
            'metadata': event.get('metadata', {})
        }
        
    def _parse_inference_api_format(self, data: Dict[str, str], message_id: bytes) -> Dict[str, Any]:
        """
        Parse inference-api format event (flattened structure)
        
        Args:
            data: Flattened event data
            message_id: Redis message ID
            
        Returns:
            dict: Standardized event format
        """
        # Parse JSON string fields
        features_data = json.loads(data.get('features', '{}'))
        prediction_data = json.loads(data.get('prediction', '{}'))
        metadata_data = json.loads(data.get('metadata', '{}'))
        
        features = {
            'feature_1': float(features_data.get('feature_1', 0.0)),
            'feature_2': float(features_data.get('feature_2', 0.0)),
            'feature_3': float(features_data.get('feature_3', 0.0))
        }
        
        prediction = {
            'label': int(prediction_data.get('label', 0)),
            'confidence': float(prediction_data.get('confidence', 0.0))
        }
        
        return {
            'message_id': message_id.decode('utf-8'),
            'request_id': data.get('request_id', message_id.decode('utf-8')),
            'timestamp': data.get('timestamp', ''),
            'model_version': data.get('model_version', 'unknown'),
            'features': features,
            'prediction': prediction,
            'metadata': metadata_data
        }
        
    def read_pending_events(self, count: int = 10) -> list:
        """
        Read pending events that were delivered but not acknowledged
        
        Args:
            count: Maximum number of pending events to read
            
        Returns:
            list: List of parsed pending events
        """
        try:
            # Read pending messages for this consumer
            # '0' means read from the beginning of pending entries
            messages = self.redis_client.xreadgroup(
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                streams={self.stream_name: '0'},
                count=count
            )
            
            if not messages:
                return []
                
            parsed_events = []
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    try:
                        parsed_event = self._parse_event(message_id, message_data)
                        if parsed_event:
                            parsed_events.append(parsed_event)
                    except Exception as e:
                        logger.error(f"Error parsing pending event {message_id}: {e}")
                        
            return parsed_events
            
        except Exception as e:
            logger.error(f"Error reading pending events: {e}")
            return []

# Made with Bob
