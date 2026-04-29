"""
Integration tests for the ML Observability Platform data flow
Tests: Event generation → Redis → Consumer → Drift Detection → Alerts
"""
import json
import time
import pytest
import redis
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'drift-service'))

from drift_service.consumer import RedisStreamConsumer
from drift_service.drift import DriftDetector


@pytest.fixture
def redis_client():
    """Create Redis client for testing"""
    client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    client.ping()
    return client


@pytest.fixture
def test_stream_name():
    """Use a separate test stream"""
    return 'test-ml-events'


class TestEventGeneration:
    """Test event generation format"""

    def test_generated_events_have_required_fields(self, redis_client, test_stream_name):
        """Verify generated events have all required fields"""
        # Read from actual ml-events stream (set by data-generator)
        messages = redis_client.xrevrange('ml-events', count=1)
        assert len(messages) > 0, "No events in ml-events stream"

        message_id, message_data = messages[0]
        assert b'event' in message_data, "Event field missing"

        event = json.loads(message_data[b'event'].decode('utf-8'))

        # Verify required fields
        required_fields = ['schema_version', 'request_id', 'timestamp', 'model_version',
                          'features', 'prediction', 'metadata']
        for field in required_fields:
            assert field in event, f"Missing field: {field}"

    def test_features_are_numeric_only(self, redis_client):
        """Verify all features are numeric (no non-numeric fields)"""
        messages = redis_client.xrevrange('ml-events', count=5)

        for message_id, message_data in messages:
            event = json.loads(message_data[b'event'].decode('utf-8'))
            features = event['features']

            # Verify we have only numeric features (feature_1, feature_2, feature_3)
            assert 'feature_1' in features
            assert 'feature_2' in features
            assert 'feature_3' in features

            # Verify no non-numeric fields like is_premium_user
            assert 'is_premium_user' not in features, "Non-numeric field in features"

            # Verify all feature values are numeric
            for key, value in features.items():
                assert isinstance(value, (int, float)), f"{key} is not numeric: {type(value)}"

    def test_prediction_format(self, redis_client):
        """Verify prediction format"""
        messages = redis_client.xrevrange('ml-events', count=3)

        for message_id, message_data in messages:
            event = json.loads(message_data[b'event'].decode('utf-8'))
            prediction = event['prediction']

            assert 'label' in prediction
            assert 'confidence' in prediction
            assert isinstance(prediction['label'], int)
            assert isinstance(prediction['confidence'], float)
            assert 0.0 <= prediction['confidence'] <= 1.0


class TestEventConsumer:
    """Test event consumer parsing"""

    def test_consumer_parses_events(self, redis_client):
        """Verify consumer can parse events from stream"""
        consumer = RedisStreamConsumer(
            redis_client=redis_client,
            stream_name='ml-events',
            consumer_group='test-group',
            consumer_name='test-consumer'
        )

        # Create consumer group
        try:
            consumer.create_consumer_group()
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # Read events
        events = consumer.read_events(count=1, block=500)

        assert len(events) > 0, "Consumer didn't parse any events"
        event = events[0]

        # Verify standardized format
        assert 'request_id' in event
        assert 'features' in event
        assert 'prediction' in event
        assert isinstance(event['features'], dict)
        assert 'feature_1' in event['features']
        assert 'feature_2' in event['features']
        assert 'feature_3' in event['features']

    def test_features_are_floats(self, redis_client):
        """Verify consumer converts all features to floats"""
        consumer = RedisStreamConsumer(
            redis_client=redis_client,
            stream_name='ml-events',
            consumer_group='test-group-float',
            consumer_name='test-consumer-float'
        )

        try:
            consumer.create_consumer_group()
        except redis.exceptions.ResponseError:
            pass

        events = consumer.read_events(count=3, block=500)

        for event in events:
            features = event['features']
            assert isinstance(features['feature_1'], float)
            assert isinstance(features['feature_2'], float)
            assert isinstance(features['feature_3'], float)


class TestDriftDetection:
    """Test drift detection logic"""

    def test_baseline_collection(self):
        """Verify baseline collection works"""
        detector = DriftDetector(
            baseline_window_size=10,
            sliding_window_size=10
        )

        # Add baseline samples
        for i in range(10):
            features = {
                'feature_1': float(i),
                'feature_2': float(i * 2),
                'feature_3': float(i * 0.5)
            }
            is_complete = detector.add_baseline_sample(features)

            if i == 9:
                assert is_complete, "Baseline should be complete after 10 samples"

        assert detector.is_baseline_ready()

    def test_sliding_window_detection(self):
        """Verify sliding window drift detection"""
        detector = DriftDetector(
            baseline_window_size=10,
            sliding_window_size=10,
            psi_threshold=0.2,
            ks_threshold=0.05
        )

        # Add baseline samples (normal distribution)
        for i in range(10):
            features = {
                'feature_1': float(i),
                'feature_2': float(i * 2),
                'feature_3': float(i * 0.5)
            }
            detector.add_baseline_sample(features)
            detector.add_baseline_prediction({'label': i % 2})

        assert detector.is_baseline_ready()

        # Add sliding window samples (drifted distribution)
        for i in range(10):
            # Shift mean by 10 to simulate drift
            features = {
                'feature_1': float(i + 10),
                'feature_2': float((i + 10) * 2),
                'feature_3': float((i + 10) * 0.5)
            }
            detector.add_sliding_sample(features)
            detector.add_sliding_prediction({'label': i % 2})

        assert detector.is_sliding_window_ready()

        # Detect drift
        result = detector.detect_feature_drift('feature_1')
        assert result is not None
        # With significant shift, should detect some drift
        assert result['psi_score'] > 0


class TestMetricsEndpoint:
    """Test metrics endpoint availability"""

    def test_drift_service_metrics_available(self):
        """Verify drift-service exposes metrics"""
        import http.client
        conn = http.client.HTTPConnection('localhost', 8000, timeout=5)
        try:
            conn.request('GET', '/metrics')
            response = conn.getresponse()
            assert response.status == 200
            data = response.read()
            assert b'python_info' in data  # Basic prometheus metric
        finally:
            conn.close()

    def test_inference_api_metrics_available(self):
        """Verify inference-api exposes metrics"""
        import http.client
        conn = http.client.HTTPConnection('localhost', 8001, timeout=5)
        try:
            conn.request('GET', '/metrics')
            response = conn.getresponse()
            assert response.status == 200
            data = response.read()
            assert b'python_info' in data
        finally:
            conn.close()


class TestAPIEndpoints:
    """Test API endpoint functionality"""

    def test_inference_api_health(self):
        """Test inference API health endpoint"""
        import http.client
        import json

        conn = http.client.HTTPConnection('localhost', 8001, timeout=5)
        try:
            conn.request('GET', '/health')
            response = conn.getresponse()
            assert response.status == 200
            data = json.loads(response.read().decode())
            assert data['status'] == 'healthy'
            assert data['service'] == 'inference-api'
        finally:
            conn.close()

    def test_drift_service_health(self):
        """Test drift service health endpoint"""
        import http.client
        import json

        conn = http.client.HTTPConnection('localhost', 8000, timeout=5)
        try:
            conn.request('GET', '/health')
            response = conn.getresponse()
            assert response.status == 200
            data = json.loads(response.read().decode())
            assert data['status'] == 'healthy'
            assert data['service'] == 'drift-detection'
        finally:
            conn.close()

    def test_inference_predict_endpoint(self):
        """Test inference predict endpoint"""
        import http.client
        import json

        conn = http.client.HTTPConnection('localhost', 8001, timeout=10)
        try:
            request_body = json.dumps({
                'feature_1': 0.5,
                'feature_2': 1.2,
                'feature_3': 0.8
            })

            conn.request('POST', '/predict', request_body)
            response = conn.getresponse()
            assert response.status == 200

            data = json.loads(response.read().decode())
            assert 'request_id' in data
            assert 'prediction' in data
            assert 'label' in data['prediction']
            assert 'confidence' in data['prediction']
        finally:
            conn.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
