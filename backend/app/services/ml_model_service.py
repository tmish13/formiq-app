"""Enhanced ML model loading and management service with multi-model support."""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List
import joblib
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import Settings
from app.core.exceptions import ServerErrorException

logger = logging.getLogger(__name__)


class EnhancedSquatModelLoader:
    """
    Enhanced service for loading and managing multiple squat form analysis ML models.
    
    Implements the notebook's multi-model approach with adaptive feature selection:
    - Binary classifier (good vs bad form) 
    - Posture model (posture-specific analysis)
    - Stability model (stability-specific analysis)
    - Depth model (depth-specific analysis)
    
    Features:
    - Lazy loading with graceful error handling
    - Adaptive feature selection per model type
    - Ensemble prediction with confidence scoring
    - Overfitting prevention strategies
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_path = Path(__file__).parent.parent / "ml_models" / "squat"
        
        # Multi-model components (loaded lazily)
        self._models = {}  # {model_type: model}
        self._scalers = {}  # {model_type: scaler}
        self._feature_sets = {}  # {model_type: [feature_names]}
        self._thresholds = {}  # {model_type: threshold}
        self._metadata = {}
        self._models_loaded = False
        self._load_lock = threading.Lock()  # prevents double-load across Celery threads
        
        # Model types and their weights for ensemble prediction
        self.model_types = ['binary', 'posture', 'stability', 'depth']
        self.ensemble_weights = {
            'binary': 1.0,
            'posture': 0.8, 
            'stability': 0.6,
            'depth': 0.4
        }
        
        # Thread pool for async model operations
        self._executor = ThreadPoolExecutor(max_workers=2)
        
    def _load_models(self) -> None:
        """
        Load all multi-model components from disk with adaptive feature selection.
        Thread-safe: double-checked locking prevents duplicate loads when multiple
        Celery workers call predict_form_quality() concurrently on first request.
        _models_loaded is only set to True INSIDE the lock and ONLY on success.

        Raises:
            ServerErrorException: If critical models cannot be loaded
        """
        if self._models_loaded:
            return
        with self._load_lock:
            if self._models_loaded:  # re-check after acquiring lock
                return
            # All model loading happens INSIDE the lock so only one thread loads.
            try:
                logger.info(f"Loading enhanced squat models from {self.model_path}")
            
                # Try to load adaptive feature sets (from notebook approach)
                adaptive_features_path = self.model_path / "adaptive_feature_sets.json"
                if adaptive_features_path.exists():
                    with open(adaptive_features_path, 'r') as f:
                        self._feature_sets = json.load(f)
                    logger.info("Adaptive feature sets loaded successfully")
                else:
                    # Fallback to single feature set for all models
                    feature_names_path = self.model_path / "feature_names.json"
                    if feature_names_path.exists():
                        with open(feature_names_path, 'r') as f:
                            default_features = json.load(f)
                        for model_type in self.model_types:
                            self._feature_sets[model_type] = default_features
                        logger.info("Using default feature set for all models")
                    else:
                        raise FileNotFoundError("No feature definitions found")
            
                # Load confidence thresholds
                thresholds_path = self.model_path / "confidence_thresholds.json"
                if thresholds_path.exists():
                    with open(thresholds_path, 'r') as f:
                        self._thresholds = json.load(f)
                else:
                    # Use default thresholds
                    default_threshold_path = self.model_path / "optimal_threshold.json" 
                    if default_threshold_path.exists():
                        with open(default_threshold_path, 'r') as f:
                            threshold_data = json.load(f)
                            default_threshold = threshold_data.get('threshold', 0.35)
                        for model_type in self.model_types:
                            self._thresholds[model_type] = default_threshold
                    else:
                        for model_type in self.model_types:
                            self._thresholds[model_type] = 0.5
            
                # Load individual models and scalers
                models_loaded = 0
                for model_type in self.model_types:
                    try:
                        logger.info(f"Processing {model_type} model...")
                        # Try to load model-specific files first
                        model_path = self.model_path / f"{model_type}_model.joblib"
                        scaler_path = self.model_path / f"{model_type}_scaler.joblib"
                    
                        logger.debug(f"Checking specific model path: {model_path}")
                        if model_path.exists():
                            self._models[model_type] = joblib.load(model_path)
                            models_loaded += 1
                            logger.info(f"Loaded {model_type} model successfully")
                        else:
                            # Fallback to binary model for all types
                            binary_path = self.model_path / "binary_classification_model.joblib"
                            logger.debug(f"Checking fallback binary path: {binary_path}")
                            logger.debug(f"Binary path exists: {binary_path.exists()}")
                            if binary_path.exists():
                                logger.debug(f"Loading binary model for {model_type}...")
                                self._models[model_type] = joblib.load(binary_path)
                                models_loaded += 1
                                logger.info(f"Using binary model for {model_type} (fallback)")
                            else:
                                logger.warning(f"Neither specific nor fallback model found for {model_type}")
                    
                        logger.debug(f"Checking scaler path: {scaler_path}")
                        if scaler_path.exists():
                            self._scalers[model_type] = joblib.load(scaler_path)
                            logger.debug(f"Loaded specific scaler for {model_type}")
                        else:
                            # Try default scaler
                            default_scaler_path = self.model_path / "feature_scaler.joblib"
                            logger.debug(f"Checking default scaler path: {default_scaler_path}")
                            if default_scaler_path.exists():
                                self._scalers[model_type] = joblib.load(default_scaler_path)
                                logger.debug(f"Loaded default scaler for {model_type}")
                            else:
                                self._scalers[model_type] = None
                                logger.debug(f"No scaler found for {model_type}, using None")
                            
                    except Exception as e:
                        logger.error(f"Could not load {model_type} model: {e}", exc_info=True)
                        continue
            
                if models_loaded == 0:
                    raise ServerErrorException("No models could be loaded")
            
                # Load metadata
                metadata_path = self.model_path / "production_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        self._metadata = json.load(f)
            
                self._models_loaded = True
                logger.info(f"Enhanced squat models loaded: {models_loaded}/{len(self.model_types)} model types")
            
            except Exception as e:
                self._models_loaded = False  # allow retry on next call
                logger.error(f"Failed to load enhanced squat models: {e}", exc_info=True)
                raise ServerErrorException(f"Enhanced ML model loading failed: {str(e)}")
    
    def predict_form_quality(self, features: Dict[str, float]) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Enhanced prediction using ensemble of specialized models with adaptive feature selection.
        
        Args:
            features: Dictionary of extracted biomechanical features
            
        Returns:
            Tuple of (is_good_form, ensemble_confidence, detailed_results)
            
        Raises:
            ServerErrorException: If prediction fails
        """
        try:
            self._load_models()  # Lazy loading
            
            # Get predictions from all available models
            model_predictions = {}
            weighted_predictions = []
            total_weight = 0.0
            
            for model_type in self.model_types:
                if model_type not in self._models:
                    continue
                    
                try:
                    prediction_result = self._predict_single_model(
                        model_type, features
                    )
                    model_predictions[model_type] = prediction_result
                    
                    # Weight the prediction by model confidence and type weight
                    confidence = prediction_result['confidence']
                    model_weight = self.ensemble_weights.get(model_type, 0.5)
                    
                    if confidence >= 0.3:  # Only use predictions with reasonable confidence
                        prediction_value = 1.0 if prediction_result['is_good_form'] else 0.0
                        weighted_prediction = prediction_value * confidence * model_weight
                        weighted_predictions.append(weighted_prediction)
                        total_weight += confidence * model_weight
                        
                except Exception as e:
                    logger.warning(f"Model {model_type} prediction failed: {e}")
                    continue
            
            # Calculate ensemble prediction
            if total_weight > 0:
                ensemble_score = sum(weighted_predictions) / total_weight
                ensemble_confidence = min(1.0, total_weight / sum(self.ensemble_weights.values()))
                is_good_form = ensemble_score >= 0.5
            else:
                # Fallback to binary model only if available
                if 'binary' in model_predictions:
                    binary_result = model_predictions['binary']
                    is_good_form = binary_result['is_good_form']
                    ensemble_confidence = binary_result['confidence']
                    ensemble_score = binary_result['confidence'] if is_good_form else (1 - binary_result['confidence'])
                else:
                    raise ServerErrorException("No models available for prediction")
            
            # Prepare detailed results
            prediction_details = {
                "model_version": self._metadata.get("version", "enhanced_v2.0"),
                "ensemble_approach": True,
                "models_used": list(model_predictions.keys()),
                "ensemble_confidence": float(ensemble_confidence),
                "ensemble_score": float(ensemble_score),
                "is_good_form": is_good_form,
                "individual_predictions": model_predictions,
                "prediction": "good_form" if is_good_form else "poor_form"
            }
            
            logger.debug(f"Enhanced ensemble prediction completed: {prediction_details}")
            return is_good_form, ensemble_confidence, prediction_details
            
        except Exception as e:
            logger.error(f"Enhanced ML prediction failed: {e}", exc_info=True)
            raise ServerErrorException(f"Enhanced ML prediction failed: {str(e)}")
    
    def _predict_single_model(self, model_type: str, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Make prediction using a single specialized model with adaptive features.
        
        Args:
            model_type: Type of model ('binary', 'posture', 'stability', 'depth')
            features: Dictionary of all extracted features
            
        Returns:
            Dictionary with prediction results for this model
        """
        model = self._models[model_type]
        scaler = self._scalers.get(model_type)
        feature_names = self._feature_sets.get(model_type, [])
        threshold = self._thresholds.get(model_type, 0.5)
        
        # Extract only the features needed for this model
        model_features = {}
        missing_count = 0
        
        for feature_name in feature_names:
            if feature_name in features:
                model_features[feature_name] = features[feature_name]
            else:
                model_features[feature_name] = 0.0  # Default value for missing features
                missing_count += 1
        
        # Check feature availability
        feature_availability = 1.0 - (missing_count / len(feature_names)) if feature_names else 0.0
        
        if feature_availability < 0.5:
            raise ValueError(f"Insufficient feature availability for {model_type}: {feature_availability:.2f}")
        
        # Create feature vector in correct order
        feature_vector = np.array([model_features[name] for name in feature_names]).reshape(1, -1)
        
        # Scale features if scaler is available
        if scaler is not None:
            try:
                scaled_features = scaler.transform(feature_vector)
            except Exception as e:
                logger.warning(f"Scaling failed for {model_type}, using raw features: {e}")
                scaled_features = feature_vector
        else:
            scaled_features = feature_vector
        
        # Get prediction probability
        prediction_proba = model.predict_proba(scaled_features)[0]
        
        # Apply model-specific threshold
        confidence = float(prediction_proba[1])  # Probability of good form
        is_good_form = confidence >= threshold
        
        # Calculate uncertainty based on prediction confidence and feature availability
        prediction_uncertainty = 1.0 - abs(confidence - 0.5) * 2  # Distance from decision boundary
        feature_uncertainty = 1.0 - feature_availability
        overall_uncertainty = (prediction_uncertainty + feature_uncertainty) / 2
        
        return {
            "model_type": model_type,
            "is_good_form": is_good_form,
            "confidence": confidence,
            "uncertainty": overall_uncertainty,
            "feature_availability": feature_availability,
            "threshold_used": threshold,
            "raw_probabilities": {
                "poor_form": float(prediction_proba[0]),
                "good_form": float(prediction_proba[1])
            }
        }
    
    def get_feature_names(self, model_type: str = 'binary') -> List[str]:
        """Get the list of required feature names for a specific model type."""
        self._load_models()
        return self._feature_sets.get(model_type, []).copy()
    
    def get_all_feature_sets(self) -> Dict[str, List[str]]:
        """Get all adaptive feature sets for all model types."""
        self._load_models()
        return self._feature_sets.copy()
    
    def get_model_metadata(self) -> Dict[str, Any]:
        """Get enhanced model metadata including version and performance metrics."""
        self._load_models()
        metadata = self._metadata.copy() if self._metadata else {}
        metadata.update({
            "enhanced_version": "2.0",
            "model_types": list(self._models.keys()),
            "ensemble_weights": self.ensemble_weights,
            "adaptive_features": True,
            "temporal_analysis": True
        })
        return metadata
    
    def is_model_available(self, model_type: Optional[str] = None) -> bool:
        """Check if ML models are available and loaded."""
        try:
            self._load_models()
            if model_type:
                return model_type in self._models
            return len(self._models) > 0
        except Exception:
            return False
    
    async def predict_form_quality_async(self, features: Dict[str, float]) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Async version of prediction for better performance in Celery tasks.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self.predict_form_quality, 
            features
        )
    
    def predict_temporal_sequence(self, feature_sequence: List[Dict[str, float]], 
                                min_confidence: float = 0.6) -> Dict[str, Any]:
        """
        Analyze a temporal sequence of features for improved accuracy.
        
        Args:
            feature_sequence: List of feature dictionaries from consecutive frames
            min_confidence: Minimum confidence threshold for reliable predictions
            
        Returns:
            Dictionary with temporal analysis results
        """
        try:
            self._load_models()
            
            if len(feature_sequence) < 3:
                logger.warning("Temporal sequence too short for reliable analysis")
                # Fallback to single-frame analysis
                if feature_sequence:
                    return self._convert_to_temporal_result(
                        self.predict_form_quality(feature_sequence[-1])
                    )
                else:
                    raise ValueError("Empty feature sequence provided")
            
            # Analyze each frame
            frame_predictions = []
            for frame_features in feature_sequence:
                try:
                    is_good, confidence, details = self.predict_form_quality(frame_features)
                    frame_predictions.append({
                        "is_good_form": is_good,
                        "confidence": confidence,
                        "details": details
                    })
                except Exception as e:
                    logger.warning(f"Frame prediction failed: {e}")
                    continue
            
            if not frame_predictions:
                raise ValueError("No valid frame predictions in sequence")
            
            # Temporal smoothing and aggregation
            confidences = [pred['confidence'] for pred in frame_predictions]
            good_form_votes = [pred['is_good_form'] for pred in frame_predictions]
            
            # Weighted average based on confidence
            weights = np.array(confidences)
            weighted_votes = np.array([1.0 if vote else 0.0 for vote in good_form_votes])
            
            # Calculate temporal metrics
            temporal_confidence = np.mean(confidences)
            temporal_stability = 1.0 - np.std(confidences)  # Higher = more stable
            weighted_average = np.average(weighted_votes, weights=weights)
            
            # Final decision with temporal factors
            final_is_good = weighted_average >= 0.5
            final_confidence = min(1.0, temporal_confidence * temporal_stability)
            
            # Movement quality assessment
            confidence_trend = np.gradient(confidences)
            is_improving = np.mean(confidence_trend) > 0
            consistency_score = 1.0 - (np.std(confidences) / (np.mean(confidences) + 1e-6))
            
            return {
                "is_good_form": final_is_good,
                "temporal_confidence": float(final_confidence),
                "temporal_stability": float(temporal_stability),
                "consistency_score": float(consistency_score),
                "improvement_trend": is_improving,
                "frame_count": len(frame_predictions),
                "valid_frames": len([p for p in frame_predictions if p['confidence'] >= min_confidence]),
                "frame_predictions": frame_predictions,
                "movement_quality": {
                    "consistency": float(consistency_score),
                    "trend": "improving" if is_improving else "stable/declining",
                    "average_confidence": float(temporal_confidence)
                }
            }
            
        except Exception as e:
            logger.error(f"Temporal sequence prediction failed: {e}", exc_info=True)
            raise ServerErrorException(f"Temporal prediction failed: {str(e)}")
    
    def _convert_to_temporal_result(self, single_prediction: Tuple[bool, float, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert single-frame prediction to temporal result format."""
        is_good, confidence, details = single_prediction
        return {
            "is_good_form": is_good,
            "temporal_confidence": confidence,
            "temporal_stability": 1.0,  # Single frame = perfectly stable
            "consistency_score": 1.0,
            "improvement_trend": False,
            "frame_count": 1,
            "valid_frames": 1,
            "frame_predictions": [{"is_good_form": is_good, "confidence": confidence, "details": details}],
            "movement_quality": {
                "consistency": 1.0,
                "trend": "single_frame",
                "average_confidence": confidence
            }
        }


class MLModelService:
    """
    Main service for managing all ML models in the application.

    Currently supports squat form analysis, can be extended for other exercises.
    Manages both the legacy sklearn ensemble and the new PostureV1 CNN-LSTM.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.squat_loader = EnhancedSquatModelLoader(settings)

        # PostureV1 CNN-LSTM (lazy-initialized)
        self._posture_v1: Optional['PostureV1TorchLoader'] = None
        self._use_posture_v1 = getattr(settings, 'USE_POSTURE_V1', True)

    def get_squat_model(self) -> EnhancedSquatModelLoader:
        """Get the squat model loader."""
        return self.squat_loader

    def get_posture_v1(self) -> Optional['PostureV1TorchLoader']:
        """Get the PostureV1 CNN-LSTM loader (lazy init)."""
        if not self._use_posture_v1:
            return None
        if self._posture_v1 is None:
            from app.ml.posture_v1.loader import PostureV1TorchLoader
            self._posture_v1 = PostureV1TorchLoader(self.settings)
        return self._posture_v1

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all ML models."""
        result = {
            "squat_model_available": self.squat_loader.is_model_available(),
            "squat_model_metadata": self.squat_loader.get_model_metadata() if self.squat_loader.is_model_available() else None,
        }

        posture_v1 = self.get_posture_v1()
        if posture_v1 is not None:
            result["posture_v1_available"] = posture_v1.is_available()
            result["posture_v1_metadata"] = posture_v1.get_metadata()
        else:
            result["posture_v1_available"] = False
            result["posture_v1_metadata"] = None

        return result