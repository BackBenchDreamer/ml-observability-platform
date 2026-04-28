"""
Drift Detection Module
Implements Kolmogorov-Smirnov test and Population Stability Index for drift detection
"""
import logging
from typing import Dict, List, Optional, Any
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Drift detector using statistical methods (KS test and PSI)
    Maintains baseline and sliding windows for comparison
    """
    
    def __init__(
        self,
        baseline_window_size: int = 100,
        sliding_window_size: int = 100,
        psi_threshold: float = 0.2,
        ks_threshold: float = 0.05
    ):
        """
        Initialize drift detector
        
        Args:
            baseline_window_size: Number of samples for baseline distribution
            sliding_window_size: Number of samples for sliding window
            psi_threshold: PSI threshold for drift detection (default: 0.2)
            ks_threshold: KS test p-value threshold (default: 0.05)
        """
        self.baseline_window_size = baseline_window_size
        self.sliding_window_size = sliding_window_size
        self.psi_threshold = psi_threshold
        self.ks_threshold = ks_threshold
        
        # Storage for baseline data (feature_name -> list of values)
        self.baseline_data: Dict[str, List[float]] = {
            'feature_1': [],
            'feature_2': [],
            'feature_3': []
        }
        
        # Storage for sliding window data
        self.sliding_data: Dict[str, List[float]] = {
            'feature_1': [],
            'feature_2': [],
            'feature_3': []
        }
        
        # Storage for prediction baseline and sliding window
        self.baseline_predictions: List[int] = []
        self.sliding_predictions: List[int] = []
        
        # Flag to track if baseline is complete
        self.baseline_complete = False
        
    def add_baseline_sample(self, features: Dict[str, float]) -> bool:
        """
        Add sample to baseline distribution
        
        Args:
            features: Dictionary with feature_1, feature_2, feature_3
            
        Returns:
            bool: True if baseline is now complete
        """
        if self.baseline_complete:
            logger.warning("Baseline already complete, ignoring sample")
            return True
            
        for feature_name, value in features.items():
            if feature_name in self.baseline_data:
                self.baseline_data[feature_name].append(float(value))
                
        # Check if baseline is complete
        if all(len(values) >= self.baseline_window_size for values in self.baseline_data.values()):
            self.baseline_complete = True
            logger.info(f"Baseline collection complete with {self.baseline_window_size} samples")
            return True
            
        return False
        
    def add_baseline_prediction(self, prediction: Dict[str, Any]) -> bool:
        """
        Add prediction to baseline distribution
        
        Args:
            prediction: Dictionary with label and confidence
            
        Returns:
            bool: True if baseline is complete
        """
        if len(self.baseline_predictions) < self.baseline_window_size:
            self.baseline_predictions.append(int(prediction.get('label', 0)))
            
        return len(self.baseline_predictions) >= self.baseline_window_size
        
    def add_sliding_sample(self, features: Dict[str, float]) -> None:
        """
        Add sample to sliding window
        Maintains fixed window size using FIFO
        
        Args:
            features: Dictionary with feature_1, feature_2, feature_3
        """
        for feature_name, value in features.items():
            if feature_name in self.sliding_data:
                self.sliding_data[feature_name].append(float(value))
                
                # Maintain window size
                if len(self.sliding_data[feature_name]) > self.sliding_window_size:
                    self.sliding_data[feature_name].pop(0)
                    
    def add_sliding_prediction(self, prediction: Dict[str, Any]) -> None:
        """
        Add prediction to sliding window
        
        Args:
            prediction: Dictionary with label and confidence
        """
        self.sliding_predictions.append(int(prediction.get('label', 0)))
        
        # Maintain window size
        if len(self.sliding_predictions) > self.sliding_window_size:
            self.sliding_predictions.pop(0)
            
    def is_baseline_ready(self) -> bool:
        """Check if baseline collection is complete"""
        return self.baseline_complete
        
    def is_sliding_window_ready(self) -> bool:
        """Check if sliding window has enough samples"""
        return all(len(values) >= self.sliding_window_size for values in self.sliding_data.values())
        
    def detect_feature_drift(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """
        Detect drift for a specific feature using KS test and PSI
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            dict: Drift detection results with ks_statistic, p_value, psi_score, drift_detected
        """
        if not self.baseline_complete:
            logger.warning("Baseline not complete, cannot detect drift")
            return None
            
        if feature_name not in self.baseline_data or feature_name not in self.sliding_data:
            logger.error(f"Unknown feature: {feature_name}")
            return None
            
        baseline = self.baseline_data[feature_name]
        sliding = self.sliding_data[feature_name]
        
        if len(sliding) < self.sliding_window_size:
            logger.debug(f"Sliding window not ready for {feature_name}: {len(sliding)}/{self.sliding_window_size}")
            return None
            
        # Perform Kolmogorov-Smirnov test
        ks_statistic, p_value = stats.ks_2samp(baseline, sliding)
        
        # Calculate Population Stability Index
        psi_score = self._calculate_psi(baseline, sliding)
        
        # Determine if drift is detected
        # Drift if PSI > threshold OR p-value < threshold (significant difference)
        drift_detected = (psi_score > self.psi_threshold) or (p_value < self.ks_threshold)
        
        result = {
            'feature': feature_name,
            'ks_statistic': float(ks_statistic),
            'p_value': float(p_value),
            'psi_score': float(psi_score),
            'drift_detected': drift_detected,
            'baseline_mean': float(np.mean(baseline)),
            'baseline_std': float(np.std(baseline)),
            'sliding_mean': float(np.mean(sliding)),
            'sliding_std': float(np.std(sliding)),
            'baseline_size': len(baseline),
            'sliding_size': len(sliding)
        }
        
        if drift_detected:
            logger.warning(f"Drift detected for {feature_name}: PSI={psi_score:.4f}, KS p-value={p_value:.4f}")
        else:
            logger.debug(f"No drift for {feature_name}: PSI={psi_score:.4f}, KS p-value={p_value:.4f}")
            
        return result
        
    def detect_prediction_drift(self) -> Optional[Dict[str, Any]]:
        """
        Detect drift in prediction distribution
        
        Returns:
            dict: Drift detection results for predictions
        """
        if not self.baseline_complete:
            logger.warning("Baseline not complete, cannot detect prediction drift")
            return None
            
        if len(self.sliding_predictions) < self.sliding_window_size:
            logger.debug(f"Sliding window not ready for predictions: {len(self.sliding_predictions)}/{self.sliding_window_size}")
            return None
            
        baseline = np.array(self.baseline_predictions)
        sliding = np.array(self.sliding_predictions)
        
        # Calculate distribution of labels
        baseline_dist = self._get_label_distribution(baseline)
        sliding_dist = self._get_label_distribution(sliding)
        
        # Calculate PSI for prediction distribution
        psi_score = self._calculate_distribution_psi(baseline_dist, sliding_dist)
        
        # Chi-square test for categorical data
        try:
            # Create contingency table
            baseline_counts = [baseline_dist.get(0, 0), baseline_dist.get(1, 0)]
            sliding_counts = [sliding_dist.get(0, 0), sliding_dist.get(1, 0)]
            
            if sum(baseline_counts) > 0 and sum(sliding_counts) > 0:
                chi2_stat, p_value = stats.chisquare(sliding_counts, baseline_counts)
            else:
                chi2_stat, p_value = 0.0, 1.0
        except Exception as e:
            logger.error(f"Error in chi-square test: {e}")
            chi2_stat, p_value = 0.0, 1.0
            
        # Drift if PSI > threshold OR p-value < threshold
        drift_detected = (psi_score > self.psi_threshold) or (p_value < self.ks_threshold)
        
        result = {
            'feature': 'prediction',
            'psi_score': float(psi_score),
            'chi2_statistic': float(chi2_stat),
            'p_value': float(p_value),
            'drift_detected': drift_detected,
            'baseline_distribution': baseline_dist,
            'sliding_distribution': sliding_dist,
            'baseline_size': len(baseline),
            'sliding_size': len(sliding)
        }
        
        if drift_detected:
            logger.warning(f"Prediction drift detected: PSI={psi_score:.4f}, p-value={p_value:.4f}")
        else:
            logger.debug(f"No prediction drift: PSI={psi_score:.4f}, p-value={p_value:.4f}")
            
        return result
        
    def _calculate_psi(self, baseline: List[float], sliding: List[float], bins: int = 10) -> float:
        """
        Calculate Population Stability Index (PSI)
        
        Args:
            baseline: Baseline distribution
            sliding: Sliding window distribution
            bins: Number of bins for discretization
            
        Returns:
            float: PSI score
        """
        try:
            baseline_arr = np.array(baseline)
            sliding_arr = np.array(sliding)
            
            # Create bins based on baseline distribution
            _, bin_edges = np.histogram(baseline_arr, bins=bins)
            
            # Calculate distributions
            baseline_hist, _ = np.histogram(baseline_arr, bins=bin_edges)
            sliding_hist, _ = np.histogram(sliding_arr, bins=bin_edges)
            
            # Convert to proportions
            baseline_prop = baseline_hist / len(baseline_arr)
            sliding_prop = sliding_hist / len(sliding_arr)
            
            # Avoid division by zero and log(0)
            baseline_prop = np.where(baseline_prop == 0, 0.0001, baseline_prop)
            sliding_prop = np.where(sliding_prop == 0, 0.0001, sliding_prop)
            
            # Calculate PSI
            psi = np.sum((sliding_prop - baseline_prop) * np.log(sliding_prop / baseline_prop))
            
            return float(psi)
            
        except Exception as e:
            logger.error(f"Error calculating PSI: {e}")
            return 0.0
            
    def _get_label_distribution(self, labels: np.ndarray) -> Dict[int, float]:
        """
        Get distribution of labels as proportions
        
        Args:
            labels: Array of label values
            
        Returns:
            dict: Label -> proportion mapping
        """
        unique, counts = np.unique(labels, return_counts=True)
        total = len(labels)
        return {int(label): float(count / total) for label, count in zip(unique, counts)}
        
    def _calculate_distribution_psi(self, baseline_dist: Dict[int, float], sliding_dist: Dict[int, float]) -> float:
        """
        Calculate PSI for categorical distributions
        
        Args:
            baseline_dist: Baseline label distribution
            sliding_dist: Sliding window label distribution
            
        Returns:
            float: PSI score
        """
        try:
            psi = 0.0
            all_labels = set(baseline_dist.keys()) | set(sliding_dist.keys())
            
            for label in all_labels:
                baseline_prop = baseline_dist.get(label, 0.0001)
                sliding_prop = sliding_dist.get(label, 0.0001)
                
                # Avoid log(0)
                if baseline_prop == 0:
                    baseline_prop = 0.0001
                if sliding_prop == 0:
                    sliding_prop = 0.0001
                    
                psi += (sliding_prop - baseline_prop) * np.log(sliding_prop / baseline_prop)
                
            return float(psi)
            
        except Exception as e:
            logger.error(f"Error calculating distribution PSI: {e}")
            return 0.0
            
    def get_baseline_stats(self) -> Dict[str, Any]:
        """Get statistics about baseline data"""
        return {
            'complete': self.baseline_complete,
            'feature_counts': {k: len(v) for k, v in self.baseline_data.items()},
            'prediction_count': len(self.baseline_predictions),
            'required_size': self.baseline_window_size
        }
        
    def get_sliding_stats(self) -> Dict[str, Any]:
        """Get statistics about sliding window data"""
        return {
            'feature_counts': {k: len(v) for k, v in self.sliding_data.items()},
            'prediction_count': len(self.sliding_predictions),
            'window_size': self.sliding_window_size
        }

# Made with Bob
