"""
ML Model Module - Simple RandomForest Classifier
Trains on dummy data for demonstration purposes
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import logging

logger = logging.getLogger(__name__)


class MLModel:
    """Simple ML model wrapper for binary classification"""
    
    def __init__(self):
        self.model = None
        self.model_id = "random-forest-v1"
        self.model_version = "1.0.0"
        self._train_model()
    
    def _train_model(self):
        """Train a simple RandomForest on dummy data"""
        logger.info("Training RandomForest model...")
        
        # Generate simple dummy data (3 features, binary classification)
        np.random.seed(42)
        n_samples = 1000
        
        # Create synthetic data where label depends on features
        X = np.random.randn(n_samples, 3)
        # Simple rule: label=1 if feature_1 + feature_2 > 0, else 0
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=10,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Log accuracy
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        logger.info(f"Model trained - Train accuracy: {train_score:.3f}, Test accuracy: {test_score:.3f}")
    
    def predict(self, features: dict) -> dict:
        """
        Make prediction from features
        
        Args:
            features: Dict with feature_1, feature_2, feature_3
            
        Returns:
            Dict with label (int) and confidence (float)
        """
        # Extract features in correct order
        feature_array = np.array([[
            features.get('feature_1', 0.0),
            features.get('feature_2', 0.0),
            features.get('feature_3', 0.0)
        ]])
        
        # Get prediction and probability
        label = int(self.model.predict(feature_array)[0])
        probabilities = self.model.predict_proba(feature_array)[0]
        confidence = float(probabilities[label])
        
        return {
            "label": label,
            "confidence": confidence
        }
    
    def get_model_info(self) -> dict:
        """Return model metadata"""
        return {
            "model_id": self.model_id,
            "model_version": self.model_version
        }


# Global model instance
_model_instance = None


def get_model() -> MLModel:
    """Get or create model singleton"""
    global _model_instance
    if _model_instance is None:
        _model_instance = MLModel()
    return _model_instance

# Made with Bob
