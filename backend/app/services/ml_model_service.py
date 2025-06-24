"""ML model loading and management service."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import joblib
import numpy as np

from app.core.config import Settings
from app.core.exceptions import ServerErrorException

logger = logging.getLogger(__name__)


class SquatModelLoader:
    """
    Service for loading and managing squat form analysis ML models.
    
    Implements lazy loading pattern to avoid startup penalties and provides
    graceful error handling with fallback capabilities.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_path = Path(__file__).parent.parent / "ml_models" / "squat"
        
        # Model components (loaded lazily)
        self._classifier = None
        self._scaler = None
        self._feature_names = None
        self._optimal_threshold = None
        self._metadata = None
        self._models_loaded = False
        
    def _load_models(self) -> None:
        """
        Load all model components from disk.
        
        Raises:
            ServerErrorException: If models cannot be loaded
        """
        if self._models_loaded:
            return
            
        try:
            logger.info(f"Loading squat models from {self.model_path}")
            
            # Load binary classification model
            classifier_path = self.model_path / "binary_classification_model.joblib"
            if not classifier_path.exists():
                raise FileNotFoundError(f"Classifier model not found: {classifier_path}")
            self._classifier = joblib.load(classifier_path)
            logger.info("Binary classification model loaded successfully")
            
            # Load feature scaler
            scaler_path = self.model_path / "feature_scaler.joblib"
            if not scaler_path.exists():
                raise FileNotFoundError(f"Feature scaler not found: {scaler_path}")
            self._scaler = joblib.load(scaler_path)
            logger.info("Feature scaler loaded successfully")
            
            # Load feature names
            feature_names_path = self.model_path / "feature_names.json"
            if not feature_names_path.exists():
                raise FileNotFoundError(f"Feature names not found: {feature_names_path}")
            with open(feature_names_path, 'r') as f:
                self._feature_names = json.load(f)
            logger.info(f"Feature names loaded: {len(self._feature_names)} features")
            
            # Load optimal threshold
            threshold_path = self.model_path / "optimal_threshold.json"
            if not threshold_path.exists():
                raise FileNotFoundError(f"Optimal threshold not found: {threshold_path}")
            with open(threshold_path, 'r') as f:
                threshold_data = json.load(f)
                self._optimal_threshold = threshold_data.get('threshold', 0.35)
            logger.info(f"Optimal threshold loaded: {self._optimal_threshold}")
            
            # Load metadata
            metadata_path = self.model_path / "production_metadata.json"
            if not metadata_path.exists():
                raise FileNotFoundError(f"Production metadata not found: {metadata_path}")
            with open(metadata_path, 'r') as f:
                self._metadata = json.load(f)
            logger.info(f"Model metadata loaded: v{self._metadata.get('version', 'unknown')}")
            
            self._models_loaded = True
            logger.info("All squat models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load squat models: {e}", exc_info=True)
            raise ServerErrorException(f"ML model loading failed: {str(e)}")
    
    def predict_form_quality(self, features: Dict[str, float]) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Predict squat form quality using the loaded ML model.
        
        Args:
            features: Dictionary of extracted biomechanical features
            
        Returns:
            Tuple of (is_good_form, confidence, prediction_details)
            
        Raises:
            ServerErrorException: If prediction fails
        """
        try:
            self._load_models()  # Lazy loading
            
            # Validate feature completeness
            expected_features = set(self._feature_names)
            provided_features = set(features.keys())
            
            if not expected_features.issubset(provided_features):
                missing_features = expected_features - provided_features
                logger.warning(f"Missing features for prediction: {missing_features}")
                # For missing features, we could either:
                # 1. Fail the prediction
                # 2. Use default values
                # 3. Use a subset model
                # For now, we'll use default values (0.0) for missing features
                for feature in missing_features:
                    features[feature] = 0.0
            
            # Create feature vector in the correct order
            feature_vector = np.array([features[name] for name in self._feature_names]).reshape(1, -1)
            
            # Scale features
            scaled_features = self._scaler.transform(feature_vector)
            
            # Get prediction probability
            prediction_proba = self._classifier.predict_proba(scaled_features)[0]
            
            # Apply optimal threshold
            confidence = float(prediction_proba[1])  # Probability of good form
            is_good_form = confidence >= self._optimal_threshold
            
            prediction_details = {
                "model_version": self._metadata.get("version", "unknown"),
                "feature_count": len(self._feature_names),
                "optimal_threshold": self._optimal_threshold,
                "raw_probabilities": {
                    "poor_form": float(prediction_proba[0]),
                    "good_form": float(prediction_proba[1])
                },
                "confidence_score": confidence,
                "prediction": "good_form" if is_good_form else "poor_form"
            }
            
            logger.debug(f"ML prediction completed: {prediction_details}")
            return is_good_form, confidence, prediction_details
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}", exc_info=True)
            raise ServerErrorException(f"ML prediction failed: {str(e)}")
    
    def get_feature_names(self) -> list:
        """Get the list of required feature names."""
        self._load_models()
        return self._feature_names.copy()
    
    def get_model_metadata(self) -> Dict[str, Any]:
        """Get model metadata including version and performance metrics."""
        self._load_models()
        return self._metadata.copy() if self._metadata else {}
    
    def is_model_available(self) -> bool:
        """Check if the ML model is available and loaded."""
        try:
            self._load_models()
            return True
        except Exception:
            return False


class MLModelService:
    """
    Main service for managing all ML models in the application.
    
    Currently supports squat form analysis, can be extended for other exercises.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.squat_loader = SquatModelLoader(settings)
    
    def get_squat_model(self) -> SquatModelLoader:
        """Get the squat model loader."""
        return self.squat_loader
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all ML models."""
        return {
            "squat_model_available": self.squat_loader.is_model_available(),
            "squat_model_metadata": self.squat_loader.get_model_metadata() if self.squat_loader.is_model_available() else None
        }