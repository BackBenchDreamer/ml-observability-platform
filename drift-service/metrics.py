"""
Prometheus Metrics for Drift Detection Service
"""
import logging
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY

logger = logging.getLogger(__name__)

# Counters
events_processed_total = Counter(
    'drift_events_processed_total',
    'Total number of events processed'
)

drift_detected_total = Counter(
    'drift_detected_total',
    'Total number of drift detections',
    ['feature', 'drift_type']
)

alerts_published_total = Counter(
    'drift_alerts_published_total',
    'Total number of alerts published to Redis stream'
)

# Gauges for drift scores
drift_score_feature_1 = Gauge(
    'drift_score_feature_1',
    'Current drift score for feature_1'
)

drift_score_feature_2 = Gauge(
    'drift_score_feature_2',
    'Current drift score for feature_2'
)

drift_score_feature_3 = Gauge(
    'drift_score_feature_3',
    'Current drift score for feature_3'
)

# KS test statistics
ks_statistic = Gauge(
    'drift_ks_statistic',
    'Kolmogorov-Smirnov test statistic',
    ['feature']
)

ks_p_value = Gauge(
    'drift_ks_p_value',
    'Kolmogorov-Smirnov test p-value',
    ['feature']
)

# PSI scores
psi_score = Gauge(
    'drift_psi_score',
    'Population Stability Index score',
    ['feature']
)

# Prediction distribution
prediction_distribution = Gauge(
    'drift_prediction_distribution',
    'Distribution of predictions',
    ['label']
)

# Processing latency
processing_latency_seconds = Histogram(
    'drift_processing_latency_seconds',
    'Time spent processing events',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Baseline and sliding window status
baseline_samples_collected = Gauge(
    'drift_baseline_samples_collected',
    'Number of samples collected for baseline'
)

sliding_window_samples = Gauge(
    'drift_sliding_window_samples',
    'Current number of samples in sliding window'
)

baseline_complete = Gauge(
    'drift_baseline_complete',
    'Whether baseline collection is complete (1=complete, 0=incomplete)'
)


class MetricsManager:
    """Manager for updating Prometheus metrics"""
    
    def __init__(self):
        """Initialize metrics manager"""
        self.feature_drift_scores = {
            'feature_1': drift_score_feature_1,
            'feature_2': drift_score_feature_2,
            'feature_3': drift_score_feature_3
        }
        
    def record_event_processed(self):
        """Record that an event was processed"""
        events_processed_total.inc()
        
    def record_drift_detected(self, feature: str, drift_type: str):
        """
        Record drift detection
        
        Args:
            feature: Feature name where drift was detected
            drift_type: Type of drift (ks_test, psi, prediction)
        """
        drift_detected_total.labels(feature=feature, drift_type=drift_type).inc()
        
    def record_alert_published(self):
        """Record that an alert was published"""
        alerts_published_total.inc()
        
    def update_drift_scores(self, feature: str, psi: float, ks_stat: float, p_value: float):
        """
        Update drift scores for a feature
        
        Args:
            feature: Feature name
            psi: PSI score
            ks_stat: KS statistic
            p_value: KS test p-value
        """
        # Update feature-specific drift score (using PSI as primary metric)
        if feature in self.feature_drift_scores:
            self.feature_drift_scores[feature].set(psi)
            
        # Update detailed metrics
        psi_score.labels(feature=feature).set(psi)
        ks_statistic.labels(feature=feature).set(ks_stat)
        ks_p_value.labels(feature=feature).set(p_value)
        
    def update_prediction_distribution(self, distribution: dict):
        """
        Update prediction distribution metrics
        
        Args:
            distribution: Dictionary mapping label -> proportion
        """
        for label, proportion in distribution.items():
            prediction_distribution.labels(label=str(label)).set(proportion)
            
    def update_baseline_status(self, samples_collected: int, is_complete: bool):
        """
        Update baseline collection status
        
        Args:
            samples_collected: Number of samples collected
            is_complete: Whether baseline is complete
        """
        baseline_samples_collected.set(samples_collected)
        baseline_complete.set(1 if is_complete else 0)
        
    def update_sliding_window_status(self, samples: int):
        """
        Update sliding window status
        
        Args:
            samples: Number of samples in sliding window
        """
        sliding_window_samples.set(samples)
        
    def record_processing_time(self, duration_seconds: float):
        """
        Record processing time
        
        Args:
            duration_seconds: Processing duration in seconds
        """
        processing_latency_seconds.observe(duration_seconds)
        
    @staticmethod
    def get_metrics() -> bytes:
        """
        Get current metrics in Prometheus format
        
        Returns:
            bytes: Metrics in Prometheus text format
        """
        return generate_latest(REGISTRY)
        
    @staticmethod
    def get_content_type() -> str:
        """
        Get content type for metrics endpoint
        
        Returns:
            str: Content type string
        """
        return CONTENT_TYPE_LATEST


# Global metrics manager instance
metrics_manager = MetricsManager()


def get_metrics_manager() -> MetricsManager:
    """
    Get the global metrics manager instance
    
    Returns:
        MetricsManager: Global metrics manager
    """
    return metrics_manager

# Made with Bob
