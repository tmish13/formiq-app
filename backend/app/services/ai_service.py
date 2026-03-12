"""Consolidated AI service for pose detection and form analysis."""
import mediapipe as mp
import numpy as np
import cv2
from typing import Dict, List, Any, Tuple, Optional, Union
import torch
from pathlib import Path
import asyncio # Added for asyncio.to_thread
import time
import hashlib
import os
import pandas as pd
import uuid

from app.core.config import settings as global_settings, Settings # IMPORTED Settings
from app.core.logging import get_logger
from app.models.enums import ExerciseType, FeedbackType, FeedbackSeverity # IMPORTED Feedback Enums
from app.constants.angles import UNIVERSAL_ANGLE_DEFINITIONS # ORIGINAL IMPORT
from app.services.ml_model_service import MLModelService, EnhancedSquatModelLoader
from app.services.enhanced_feature_extraction_service import EnhancedSquatFeatureExtractor
from app.services.cache_service import CacheService, get_cache_service

logger = get_logger(__name__)

# Renamed from AIModelService
class AIService:
    NUM_EXPECTED_LANDMARKS = 33 # MediaPipe Pose model typically has 33 landmarks

    def __init__(self, app_settings: Optional[Settings] = None): # MODIFIED constructor
        """Initialize the AI model service."""
        logger.info("Initializing AIService...")
        self.settings = app_settings or global_settings # Use provided or global settings

        # Initialize MediaPipe Pose — complexity=2 matches PostureV1 training data.
        # Fallback to complexity=1 only on init failure (e.g. resource constraints).
        self._pose_complexity_used = self.settings.AI_MODEL_COMPLEXITY
        self._pose_complexity_fallback = False
        try:
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=self.settings.AI_MODEL_COMPLEXITY,
                min_detection_confidence=self.settings.AI_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=self.settings.AI_MIN_TRACKING_CONFIDENCE,
            )
            logger.info(
                "MediaPipe Pose initialized: model_complexity=%d, det_conf=%.2f, track_conf=%.2f",
                self.settings.AI_MODEL_COMPLEXITY,
                self.settings.AI_MIN_DETECTION_CONFIDENCE,
                self.settings.AI_MIN_TRACKING_CONFIDENCE,
            )
        except Exception as e:
            logger.warning(
                "MediaPipe Pose init failed at complexity=%d (%s), falling back to complexity=1",
                self.settings.AI_MODEL_COMPLEXITY, e,
            )
            self._pose_complexity_used = 1
            self._pose_complexity_fallback = True
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=self.settings.AI_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=self.settings.AI_MIN_TRACKING_CONFIDENCE,
            )
        
        # Initialize GPU-accelerated pose model if available
        self._init_gpu_pose_model()
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"AI Service using device: {self.device}")
        self.model = self._load_form_analysis_model()
        self.exercise_classification_model = self._load_exercise_classification_model()
        
        # Initialize enhanced ML model service and feature extraction
        self.ml_model_service = MLModelService(self.settings)
        self.enhanced_squat_model = EnhancedSquatModelLoader(self.settings)
        self.squat_feature_extractor = EnhancedSquatFeatureExtractor()
        
        # Feature flag for ML models
        self.use_ml_models = getattr(self.settings, 'USE_ML_MODELS', True)
        
        # Batch processing configuration
        self.batch_size = getattr(self.settings, 'POSE_BATCH_SIZE', 8)
        self.use_gpu_acceleration = getattr(self.settings, 'USE_GPU_POSE_DETECTION', True) and torch.cuda.is_available()
        
        logger.info(f"AIService initialized with ML models: {self.use_ml_models}, "
                   f"Batch size: {self.batch_size}, GPU acceleration: {self.use_gpu_acceleration}")
        
        # Cache service for ML prediction optimization
        self.cache_service: Optional[CacheService] = None
        self._cache_initialized = False
        
        # TODO: Integrate loading of other models (pose, comparison) from ml_model_service.py
        # TODO: Integrate loading of templates from ml_model_service.py
    
    async def _ensure_cache_service(self) -> Optional[CacheService]:
        """Lazily initialize cache service for ML prediction optimization."""
        if not self._cache_initialized:
            try:
                self.cache_service = await get_cache_service(self.settings)
                if self.cache_service:
                    logger.info("Cache service initialized successfully for AIService")
                else:
                    logger.warning("Cache service initialization failed, operating without cache")
            except Exception as e:
                logger.warning(f"Cache service initialization error: {e}")
                self.cache_service = None
            finally:
                self._cache_initialized = True
        
        return self.cache_service
        
    def _init_gpu_pose_model(self) -> None:
        """Initialize GPU-accelerated pose model if available."""
        try:
            # Check if GPU is available and desired
            if torch.cuda.is_available():
                logger.info("GPU detected, enabling GPU acceleration for pose detection")
                self.gpu_pose = mp.solutions.pose.Pose(
                    static_image_mode=False,
                    model_complexity=1,  # Use lighter model for GPU batching
                    min_detection_confidence=self.settings.AI_MIN_DETECTION_CONFIDENCE,
                    min_tracking_confidence=self.settings.AI_MIN_TRACKING_CONFIDENCE
                )
            else:
                logger.info("No GPU available, using CPU-only pose detection")
                self.gpu_pose = None
        except Exception as e:
            logger.warning(f"Failed to initialize GPU pose model: {e}")
            self.gpu_pose = None
        
    def _load_form_analysis_model(self) -> Any:
        """Load the form analysis model."""
        try:
            # Consistent path from settings
            model_path = Path(self.settings.AI_MODEL_PATH) / "form_analysis_model.pt" # Use self.settings
            if model_path.exists():
                logger.info(f"Loading form analysis model from: {model_path}")
                model = torch.load(model_path, map_location=self.device)
                model.eval() # Set model to evaluation mode
                logger.info("Form analysis model loaded successfully.")
                return model
            logger.warning(f"Form analysis model not found at {model_path}. Using default rules.")
            return None
        except Exception as e:
            logger.error(f"Error loading form analysis model: {str(e)}", exc_info=True)
            return None

    def _load_exercise_classification_model(self) -> Any:
        """Load the exercise classification model (placeholder)."""
        try:
            # model_path = Path(self.settings.AI_MODEL_PATH) / "exercise_classification_model.pt"
            # if model_path.exists():
            #     logger.info(f"Loading exercise classification model from: {model_path}")
            #     model = torch.load(model_path, map_location=self.device)
            #     model.eval()
            #     logger.info("Exercise classification model loaded successfully.")
            #     return model
            logger.warning(f"Exercise classification model not implemented yet. Returning None.")
            return None
        except Exception as e:
            logger.error(f"Error loading exercise classification model: {str(e)}", exc_info=True)
            return None

    async def classify_exercise_from_keypoints(
        self,
        keypoint_sequence: Optional[List[List[Optional[Dict[str, float]]]]]
    ) -> Tuple[Optional[str], Optional[float]]:
        """Exercise classification stub — not implemented."""
        raise NotImplementedError("classify_exercise_from_keypoints is not implemented")
            
    def detect_pose(self, frame: np.ndarray) -> Tuple[List[Dict[str, float]], float]:
        """Detect pose landmarks in a frame."""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False # Performance optimization
            results = self.pose.process(frame_rgb)
            frame_rgb.flags.writeable = True # Re-enable writing
            # frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR) # Convert back if needed for drawing
            
            if not results.pose_landmarks:
                return [], 0.0
                
            landmarks = []
            visibility_sum = 0.0
            lm_count = 0
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                })
                visibility_sum += landmark.visibility
                lm_count += 1
                
            confidence = (visibility_sum / lm_count) if lm_count > 0 else 0.0
            
            return landmarks, confidence
            
        except Exception as e:
            logger.error(f"Error detecting pose: {str(e)}", exc_info=True)
            return [], 0.0
            
    async def analyze_form(self, landmarks: List[Dict[str, float]], exercise_type: str) -> Dict[str, Any]:
        """
        Analyze exercise form based on pose landmarks with ML model integration.
        
        For squat exercises, uses trained XGBoost model with biomechanical features.
        Falls back to rule-based analysis for other exercises or when ML models are disabled.
        """
        
        async def _run_ml_inference_and_rules():
            if not landmarks:
                logger.warning("analyze_form called with no landmarks.")
                return {
                    "score": 0.0,
                    "feedback": ["No pose detected."],
                    "risk_level": "high",
                    "feedback_structured": []
                }
            
            current_score = 1.0
            feedback_messages = []
            feedback_structured_list = []
            analysis_method = "rule_based"
            
            # ML Model Analysis for Squats
            if (self.use_ml_models and 
                exercise_type.lower() == 'squat' and 
                self.enhanced_squat_model.is_model_available()):
                
                try:
                    logger.info("Using ML model for squat form analysis")
                    analysis_method = "ml_model"
                    
                    # Convert single frame landmarks to pose sequence format for feature extraction
                    # The feature extractor expects a sequence, so we create a single-frame sequence
                    pose_sequence = [landmarks]  # Single frame in sequence format
                    
                    # Extract biomechanical features
                    features = self.squat_feature_extractor.extract_features(pose_sequence)
                    logger.debug(f"Extracted {len(features)} features for ML inference")
                    
                    # Check cache for ML prediction first
                    cache_service = await self._ensure_cache_service()
                    cached_prediction = None
                    
                    if cache_service:
                        try:
                            cached_prediction = await cache_service.get_ml_prediction(
                                features, model_version="enhanced_v2.0"
                            )
                            if cached_prediction:
                                logger.debug("Using cached ML prediction for squat analysis")
                        except Exception as e:
                            logger.debug(f"Cache lookup failed for ML prediction: {e}")
                    
                    if cached_prediction:
                        # Use cached prediction
                        is_good_form = cached_prediction.get('is_good_form', False)
                        confidence = cached_prediction.get('ensemble_confidence', 0.5)
                        prediction_details = cached_prediction
                    else:
                        # Get ML prediction
                        is_good_form, confidence, prediction_details = self.enhanced_squat_model.predict_form_quality(features)
                        
                        # Cache the prediction for future use
                        if cache_service:
                            try:
                                prediction_result = {
                                    'is_good_form': is_good_form,
                                    'ensemble_confidence': confidence,
                                    **prediction_details
                                }
                                await cache_service.set_ml_prediction(
                                    features, prediction_result, 
                                    model_version="enhanced_v2.0",
                                    ttl=cache_service.prediction_ttl
                                )
                                logger.debug("Cached ML prediction for squat analysis")
                            except Exception as e:
                                logger.debug(f"Failed to cache ML prediction: {e}")
                    
                    # Convert ML prediction to score (0-100)
                    ml_score = confidence * 100
                    current_score = ml_score / 100  # Keep internal score as 0-1
                    
                    # Generate feedback based on ML prediction
                    if is_good_form:
                        feedback_messages.append(f"Good squat form detected (confidence: {confidence:.2f})")
                        feedback_structured_list.append({
                            "type": FeedbackType.TECHNIQUE,
                            "message": f"Excellent squat form! Overall score: {ml_score:.1f}%",
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.LOW
                        })
                    else:
                        feedback_messages.append(f"Form issues detected (confidence: {confidence:.2f})")
                        
                        # Generate specific feedback based on features
                        feature_feedback = self._generate_squat_feedback_from_features(features)
                        feedback_messages.extend(feature_feedback['messages'])
                        feedback_structured_list.extend(feature_feedback['structured'])
                    
                    # Add model metadata
                    feedback_structured_list.append({
                        "type": FeedbackType.TECHNIQUE,
                        "message": f"Analysis by FormIQ ML Model v{prediction_details.get('model_version', 'unknown')}",
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.INFO
                    })
                    
                    logger.info(f"ML analysis complete: score={ml_score:.1f}, form={'good' if is_good_form else 'poor'}")
                    
                except Exception as e_ml:
                    logger.error(f"ML model analysis failed, falling back to rules: {e_ml}", exc_info=True)
                    analysis_method = "rule_based_fallback"
                    feedback_messages.append("ML analysis failed, using rule-based analysis.")
                    # Continue to rule-based analysis below
            
            # Rule-based analysis (fallback or augmentation)
            if analysis_method in ["rule_based", "rule_based_fallback"]:
                logger.info(f"Using rule-based analysis for {exercise_type}")
                
                try:
                    # General spine alignment check
                    spine_angle = self._calculate_angle(landmarks, 11, 23, 24)  # L_SHOULDER, L_HIP, R_HIP
                    if spine_angle is not None and (spine_angle < 160 or spine_angle > 200):
                        msg = "Maintain a neutral spine."
                        feedback_messages.append(msg)
                        feedback_structured_list.append({
                            "type": FeedbackType.ALIGNMENT,
                            "message": msg,
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.MEDIUM,
                            "suggestions": ["Engage core, keep chest up."]
                        })
                        current_score *= 0.8
                    
                    # Exercise-specific rule-based analysis
                    if exercise_type.lower() == 'squat':
                        current_score = self._analyze_squat_rules(landmarks, feedback_messages, 
                                                               feedback_structured_list, current_score)
                    
                    # Add default message if no specific feedback
                    if len([msg for msg in feedback_messages if not msg.startswith("ML analysis")]) == 0:
                        feedback_messages.append("Form looks generally good based on available rules.")
                
                except Exception as e_rules:
                    logger.error(f"Error during rule-based analysis: {e_rules}", exc_info=True)
                    feedback_messages.append("Error during rule-based analysis.")
                    current_score = 0.3  # Partial score if rules fail
            
            # Calculate final score and risk level
            final_score = max(0.0, min(1.0, current_score))
            final_score_100 = final_score * 100
            
            # Determine risk level based on score
            if final_score > 0.8:
                risk_level = "low"
            elif final_score > 0.6:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            return {
                "score": final_score_100,
                "feedback": feedback_messages,
                "risk_level": risk_level,
                "feedback_structured": feedback_structured_list,
                "analysis_method": analysis_method
            }

        try:
            # Run the async analysis
            analysis_output = await _run_ml_inference_and_rules()
            return analysis_output
        except Exception as e_async_wrapper:
            logger.error(f"Async wrapper error in analyze_form: {e_async_wrapper}", exc_info=True)
            return {
                "score": 0.0,
                "feedback": ["Analysis failed due to an internal error."],
                "risk_level": "high",
                "feedback_structured": [],
                "analysis_method": "error"
            }

    async def analyze_form_sequence(
        self, 
        landmark_sequence: List[List[Dict[str, float]]], 
        exercise_type: str,
        min_confidence: float = 0.6
    ) -> Dict[str, Any]:
        """
        Analyze exercise form using temporal sequence of pose landmarks.
        
        This method provides improved accuracy by analyzing movement patterns
        over time rather than single frames.
        
        Args:
            landmark_sequence: List of pose landmark sequences for multiple frames
            exercise_type: Type of exercise being analyzed
            min_confidence: Minimum confidence threshold for analysis
            
        Returns:
            Dictionary with temporal analysis results including:
            - Enhanced scoring with temporal factors
            - Movement quality assessment
            - Consistency metrics
            - Frame-by-frame breakdown
        """
        if not landmark_sequence:
            logger.warning("analyze_form_sequence called with empty landmark sequence")
            return {
                "score": 0.0,
                "feedback": ["No pose sequence data provided."],
                "risk_level": "high",
                "feedback_structured": [],
                "analysis_method": "error"
            }
        
        logger.info(f"Starting temporal sequence analysis for {exercise_type} with {len(landmark_sequence)} frames")
        
        async def _run_temporal_analysis():
            try:
                # Enhanced ML Model Analysis for Squats with Temporal Processing
                if (self.use_ml_models and 
                    exercise_type.lower() == 'squat' and 
                    self.enhanced_squat_model.is_model_available()):
                    
                    logger.info("Using enhanced ML model for temporal squat analysis")
                    
                    # Extract features for each frame
                    feature_sequence = []
                    for frame_landmarks in landmark_sequence:
                        try:
                            # Feature extractor expects a sequence, so wrap single frame
                            frame_features = self.squat_feature_extractor.extract_features([frame_landmarks])
                            feature_sequence.append(frame_features)
                        except Exception as e:
                            logger.warning(f"Feature extraction failed for frame: {e}")
                            continue
                    
                    if not feature_sequence:
                        raise ValueError("No valid features extracted from sequence")
                    
                    # Check cache for temporal sequence prediction
                    cache_service = await self._ensure_cache_service()
                    cached_temporal_prediction = None
                    
                    if cache_service and len(feature_sequence) > 0:
                        try:
                            # Use first features for cache key (temporal sequences are harder to cache)
                            # In future, we could implement sequence-specific caching
                            representative_features = feature_sequence[0]  # Use first frame features as cache key
                            cached_temporal_prediction = await cache_service.get_ml_prediction(
                                representative_features, model_version="temporal_v2.0"
                            )
                            if cached_temporal_prediction:
                                logger.debug("Using cached temporal prediction for squat sequence")
                        except Exception as e:
                            logger.debug(f"Cache lookup failed for temporal prediction: {e}")
                    
                    if cached_temporal_prediction and 'temporal_confidence' in cached_temporal_prediction:
                        # Use cached temporal prediction
                        temporal_results = cached_temporal_prediction
                    else:
                        # Use enhanced temporal prediction
                        temporal_results = self.enhanced_squat_model.predict_temporal_sequence(
                            feature_sequence, min_confidence
                        )
                        
                        # Cache the temporal prediction (using representative features)
                        if cache_service and len(feature_sequence) > 0:
                            try:
                                representative_features = feature_sequence[0]
                                await cache_service.set_ml_prediction(
                                    representative_features, temporal_results,
                                    model_version="temporal_v2.0",
                                    ttl=cache_service.prediction_ttl // 2  # Shorter TTL for temporal predictions
                                )
                                logger.debug("Cached temporal prediction for squat sequence")
                            except Exception as e:
                                logger.debug(f"Failed to cache temporal prediction: {e}")
                    
                    # Process temporal results
                    final_score = temporal_results['temporal_confidence'] * 100
                    is_good_form = temporal_results['is_good_form']
                    
                    feedback_messages = []
                    feedback_structured = []
                    
                    # Generate temporal-specific feedback
                    if is_good_form:
                        feedback_messages.append(
                            f"Excellent squat form with consistent movement (confidence: {temporal_results['temporal_confidence']:.2f})"
                        )
                        feedback_structured.append({
                            "type": FeedbackType.TECHNIQUE,
                            "message": f"Consistent squat form! Temporal score: {final_score:.1f}%",
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.LOW
                        })
                    else:
                        feedback_messages.append(
                            f"Form inconsistencies detected (confidence: {temporal_results['temporal_confidence']:.2f})"
                        )
                    
                    # Add movement quality feedback
                    movement_quality = temporal_results['movement_quality']
                    
                    if movement_quality['consistency'] < 0.7:
                        feedback_messages.append("Work on movement consistency throughout the range of motion")
                        feedback_structured.append({
                            "type": FeedbackType.TECHNIQUE,
                            "message": f"Movement consistency needs improvement (score: {movement_quality['consistency']:.2f})",
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.MEDIUM,
                            "suggestions": ["Focus on controlled movement", "Practice tempo control"]
                        })
                    
                    if temporal_results['improvement_trend']:
                        feedback_messages.append("Good - your form is improving throughout the movement")
                        feedback_structured.append({
                            "type": FeedbackType.TECHNIQUE,
                            "message": "Positive improvement trend detected",
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.LOW
                        })
                    
                    # Stability analysis
                    if temporal_results['temporal_stability'] < 0.8:
                        feedback_messages.append("Focus on stability - movement appears shaky")
                        feedback_structured.append({
                            "type": FeedbackType.ALIGNMENT,
                            "message": f"Movement stability could be improved (score: {temporal_results['temporal_stability']:.2f})",
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.MEDIUM,
                            "suggestions": ["Engage core muscles", "Slow down the movement", "Focus on control"]
                        })
                    
                    # Add model metadata
                    feedback_structured.append({
                        "type": FeedbackType.TECHNIQUE,
                        "message": f"Analysis by Enhanced FormIQ Temporal ML Model",
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.INFO
                    })
                    
                    # Determine risk level based on temporal factors
                    if final_score > 80 and temporal_results['temporal_stability'] > 0.8:
                        risk_level = "low"
                    elif final_score > 60 and temporal_results['temporal_stability'] > 0.6:
                        risk_level = "medium"
                    else:
                        risk_level = "high"
                    
                    return {
                        "score": final_score,
                        "feedback": feedback_messages,
                        "risk_level": risk_level,
                        "feedback_structured": feedback_structured,
                        "analysis_method": "temporal_ml_model",
                        "temporal_metrics": {
                            "frame_count": temporal_results['frame_count'],
                            "valid_frames": temporal_results['valid_frames'],
                            "consistency_score": temporal_results['consistency_score'],
                            "stability_score": temporal_results['temporal_stability'],
                            "improvement_trend": temporal_results['improvement_trend']
                        },
                        "movement_quality": movement_quality
                    }
                    
                else:
                    # Fallback to frame-by-frame analysis for non-ML or non-squat exercises
                    logger.info(f"Using frame-by-frame analysis for {exercise_type} (ML not available)")
                    
                    frame_scores = []
                    all_feedback = []
                    all_structured_feedback = []
                    
                    # Analyze each frame
                    for i, frame_landmarks in enumerate(landmark_sequence):
                        if not frame_landmarks:
                            continue
                            
                        try:
                            # Use single frame analysis
                            frame_result = self._run_single_frame_analysis(frame_landmarks, exercise_type)
                            frame_scores.append(frame_result['score'])
                            
                            # Add frame-specific feedback with timestamps
                            for feedback_item in frame_result.get('feedback_structured', []):
                                feedback_item = feedback_item.copy()
                                feedback_item['timestamp'] = i * (1.0 / 30)  # Assume 30fps
                                all_structured_feedback.append(feedback_item)
                                
                        except Exception as e:
                            logger.warning(f"Frame {i} analysis failed: {e}")
                            continue
                    
                    if frame_scores:
                        # Calculate temporal metrics
                        avg_score = np.mean(frame_scores)
                        score_consistency = 1.0 - (np.std(frame_scores) / (np.mean(frame_scores) + 1e-6))
                        
                        # Generate summary feedback
                        feedback_messages = [
                            f"Analyzed {len(frame_scores)} frames with average score: {avg_score:.1f}%"
                        ]
                        
                        if score_consistency < 0.7:
                            feedback_messages.append("Work on maintaining consistent form throughout the movement")
                            all_structured_feedback.append({
                                "type": FeedbackType.TECHNIQUE,
                                "message": f"Form consistency needs improvement (score: {score_consistency:.2f})",
                                "timestamp": 0.0,
                                "severity": FeedbackSeverity.MEDIUM
                            })
                        
                        # Determine risk level
                        if avg_score > 80 and score_consistency > 0.8:
                            risk_level = "low"
                        elif avg_score > 60 and score_consistency > 0.6:
                            risk_level = "medium"
                        else:
                            risk_level = "high"
                        
                        return {
                            "score": avg_score,
                            "feedback": feedback_messages,
                            "risk_level": risk_level,
                            "feedback_structured": all_structured_feedback,
                            "analysis_method": "rule_based_sequence",
                            "temporal_metrics": {
                                "frame_count": len(landmark_sequence),
                                "valid_frames": len(frame_scores),
                                "consistency_score": score_consistency,
                                "score_range": [min(frame_scores), max(frame_scores)]
                            }
                        }
                    else:
                        raise ValueError("No valid frames could be analyzed")
                        
            except Exception as e:
                logger.error(f"Temporal analysis failed: {e}", exc_info=True)
                return {
                    "score": 0.0,
                    "feedback": [f"Temporal analysis failed: {str(e)}"],
                    "risk_level": "high",
                    "feedback_structured": [],
                    "analysis_method": "error"
                }
        
        try:
            # Run temporal analysis in separate thread
            return await _run_temporal_analysis()
        except Exception as e:
            logger.error(f"Async temporal analysis wrapper failed: {e}", exc_info=True)
            return {
                "score": 0.0,
                "feedback": ["Temporal analysis failed due to an internal error."],
                "risk_level": "high",
                "feedback_structured": [],
                "analysis_method": "error"
            }
    
    def _run_single_frame_analysis(self, landmarks: List[Dict[str, float]], exercise_type: str) -> Dict[str, Any]:
        """
        Helper method to run single frame analysis without async wrapper.
        Used by temporal sequence analysis for fallback processing.
        """
        if not landmarks:
            return {
                "score": 0.0,
                "feedback": ["No pose detected."],
                "risk_level": "high",
                "feedback_structured": []
            }
        
        current_score = 1.0
        feedback_messages = []
        feedback_structured_list = []
        
        try:
            # General spine alignment check
            spine_angle = self._calculate_angle(landmarks, 11, 23, 24)
            if spine_angle is not None and (spine_angle < 160 or spine_angle > 200):
                msg = "Maintain a neutral spine."
                feedback_messages.append(msg)
                feedback_structured_list.append({
                    "type": FeedbackType.ALIGNMENT,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.MEDIUM,
                    "suggestions": ["Engage core, keep chest up."]
                })
                current_score *= 0.8
            
            # Exercise-specific analysis
            if exercise_type.lower() == 'squat':
                current_score = self._analyze_squat_rules(landmarks, feedback_messages, 
                                                       feedback_structured_list, current_score)
            
        except Exception as e:
            logger.error(f"Error in single frame analysis: {e}")
            current_score = 0.3
        
        final_score = max(0.0, min(1.0, current_score)) * 100
        
        if final_score > 80:
            risk_level = "low"
        elif final_score > 60:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return {
            "score": final_score,
            "feedback": feedback_messages,
            "risk_level": risk_level,
            "feedback_structured": feedback_structured_list
        }
    
    def _generate_squat_feedback_from_features(self, features: Dict[str, float]) -> Dict[str, List]:
        """
        Generate specific feedback messages based on extracted biomechanical features.
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            Dictionary with 'messages' and 'structured' feedback lists
        """
        messages = []
        structured = []
        
        try:
            # Depth feedback
            if features.get('depth_flag', 0) == 0:
                msg = "Increase squat depth - aim to get your hips below knee level"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.RANGE_OF_MOTION,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.MEDIUM,
                    "suggestions": ["Focus on sitting back into the squat", "Improve ankle mobility"]
                })
            
            # Posture feedback
            if features.get('excessive_forward_lean', 0) == 1:
                msg = "Reduce forward lean - keep your torso more upright"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.ALIGNMENT,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.MEDIUM,
                    "suggestions": ["Engage your core", "Keep chest up", "Focus on sitting back rather than forward"]
                })
            
            # Stability feedback
            if features.get('knee_valgus_flag', 0) == 1:
                msg = "Control knee position - avoid letting knees cave inward"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.ALIGNMENT,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.HIGH,
                    "suggestions": ["Push knees out over toes", "Strengthen glutes", "Work on hip mobility"]
                })
            
            # Asymmetry feedback
            if features.get('asymmetry_flag', 0) == 1:
                msg = "Balance your movement - one side appears different from the other"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.ALIGNMENT,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.MEDIUM,
                    "suggestions": ["Focus on symmetrical movement", "Check for mobility imbalances"]
                })
            
            # Tempo feedback
            if features.get('controlled_descent_flag', 0) == 0:
                msg = "Control your descent - take 2-3 seconds to lower down"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.TECHNIQUE,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.LOW,
                    "suggestions": ["Count to 3 on the way down", "Focus on muscle control"]
                })
            
            # Provide positive feedback for good aspects
            good_aspects = []
            if features.get('depth_flag', 0) == 1:
                good_aspects.append("excellent depth")
            if features.get('torso_control_flag', 0) == 1:
                good_aspects.append("good torso control")
            if features.get('smooth_ascent_flag', 0) == 1:
                good_aspects.append("smooth movement")
            
            if good_aspects:
                msg = f"Good work on: {', '.join(good_aspects)}"
                messages.append(msg)
                structured.append({
                    "type": FeedbackType.TECHNIQUE,
                    "message": msg,
                    "timestamp": 0.0,
                    "severity": FeedbackSeverity.LOW
                })
                
        except Exception as e:
            logger.error(f"Error generating feature-based feedback: {e}")
            messages.append("Unable to generate detailed feedback")
        
        return {
            "messages": messages,
            "structured": structured
        }
    
    def _analyze_squat_rules(self, landmarks: List[Dict[str, float]], 
                           feedback_messages: List[str], 
                           feedback_structured_list: List[Dict], 
                           current_score: float) -> float:
        """
        Rule-based squat analysis for fallback when ML model is not available.
        
        Args:
            landmarks: Pose landmarks
            feedback_messages: List to append feedback messages
            feedback_structured_list: List to append structured feedback
            current_score: Current score to modify
            
        Returns:
            Updated score after rule-based analysis
        """
        try:
            # Left and right knee angles
            left_knee_angle = self._calculate_angle(landmarks, 23, 25, 27)  # L_HIP, L_KNEE, L_ANKLE
            right_knee_angle = self._calculate_angle(landmarks, 24, 26, 28)  # R_HIP, R_KNEE, R_ANKLE
            
            # Analyze knee angles for depth
            valid_knee_angles = [a for a in [left_knee_angle, right_knee_angle] if a is not None]
            if valid_knee_angles:
                avg_knee_angle = np.mean(valid_knee_angles)
                min_knee_angle = min(valid_knee_angles)
                
                # Depth analysis
                if min_knee_angle > 110:  # Insufficient depth
                    msg = f"Squat deeper - current knee angle: {avg_knee_angle:.1f}°"
                    feedback_messages.append(msg)
                    feedback_structured_list.append({
                        "type": FeedbackType.RANGE_OF_MOTION,
                        "message": msg,
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.MEDIUM,
                        "suggestions": ["Aim for knee angle below 90°", "Work on ankle mobility"]
                    })
                    current_score *= 0.7
                elif min_knee_angle > 90:  # Partial depth
                    msg = f"Good depth, try to go slightly lower - current: {avg_knee_angle:.1f}°"
                    feedback_messages.append(msg)
                    feedback_structured_list.append({
                        "type": FeedbackType.RANGE_OF_MOTION,
                        "message": msg,
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.LOW
                    })
                    current_score *= 0.9
                else:  # Good depth
                    feedback_messages.append("Excellent squat depth!")
                    feedback_structured_list.append({
                        "type": FeedbackType.TECHNIQUE,
                        "message": "Perfect squat depth achieved",
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.LOW
                    })
                
                # Symmetry check
                if len(valid_knee_angles) == 2:
                    angle_diff = abs(left_knee_angle - right_knee_angle)
                    if angle_diff > 15:  # Significant asymmetry
                        msg = f"Balance your squat - {angle_diff:.1f}° difference between legs"
                        feedback_messages.append(msg)
                        feedback_structured_list.append({
                            "type": FeedbackType.ALIGNMENT,
                            "message": msg,
                            "timestamp": 0.0,
                            "severity": FeedbackSeverity.MEDIUM,
                            "suggestions": ["Focus on even weight distribution", "Check for mobility imbalances"]
                        })
                        current_score *= 0.85
            
            # Torso angle analysis
            torso_angle = self._calculate_angle(landmarks, 11, 23, 12)  # L_SHOULDER, L_HIP, R_SHOULDER
            if torso_angle is not None:
                # Convert to lean angle from vertical (approximate)
                lean_angle = abs(90 - torso_angle) if torso_angle < 90 else abs(torso_angle - 90)
                
                if lean_angle > 30:  # Excessive forward lean
                    msg = f"Reduce forward lean - keep torso more upright ({lean_angle:.1f}° lean)"
                    feedback_messages.append(msg)
                    feedback_structured_list.append({
                        "type": FeedbackType.ALIGNMENT,
                        "message": msg,
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.MEDIUM,
                        "suggestions": ["Engage core muscles", "Focus on sitting back, not forward"]
                    })
                    current_score *= 0.8
                elif lean_angle > 20:  # Moderate lean
                    msg = f"Good posture, slight forward lean detected ({lean_angle:.1f}°)"
                    feedback_messages.append(msg)
                    feedback_structured_list.append({
                        "type": FeedbackType.ALIGNMENT,
                        "message": msg,
                        "timestamp": 0.0,
                        "severity": FeedbackSeverity.LOW
                    })
                    current_score *= 0.95
            
        except Exception as e:
            logger.error(f"Error in rule-based squat analysis: {e}")
            current_score *= 0.9  # Small penalty for analysis errors
        
        return current_score
            
    def _get_landmark_coords(self, landmarks_list: List[Optional[Dict[str, float]]], index: int) -> Optional[np.ndarray]:
        """Safely get landmark coordinates as a numpy array from a list that may contain Nones."""
        if 0 <= index < len(landmarks_list):
            landmark_data = landmarks_list[index] # This could be a Dict or None
            if landmark_data is not None:
                # Ensure 'x' and 'y' are present. 'z' is optional but good to handle.
                x = landmark_data.get("x")
                y = landmark_data.get("y")
                
                if x is not None and y is not None: # Essential coordinates must exist
                    z = landmark_data.get("z", 0.0) # Default z to 0.0 if not present
                    return np.array([x, y, z])
                else:
                    # logger.debug(f"Landmark at index {index} missing x or y: {landmark_data}") # Optional logging
                    return None # Essential coordinates missing
            # else: landmark_data is None, so fall through to return None
        return None

    def _calculate_angle(self, landmarks_list: List[Optional[Dict[str, float]]], p1_idx: int, p2_idx: int, p3_idx: int) -> Optional[float]:
        """Calculate the angle formed by three landmarks."""
        p1 = self._get_landmark_coords(landmarks_list, p1_idx)
        p2 = self._get_landmark_coords(landmarks_list, p2_idx) # Vertex
        p3 = self._get_landmark_coords(landmarks_list, p3_idx)

        if p1 is None or p2 is None or p3 is None:
            # logger.debug(f"Cannot calculate angle: one or more points ({p1_idx}, {p2_idx}, {p3_idx}) missing from landmarks.") # Optional logging
            return None

        try:
            # Calculate vectors
            v1 = p1 - p2
            v2 = p3 - p2

            # Calculate angle using dot product
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)

            if norm_v1 == 0 or norm_v2 == 0:
                return None # Avoid division by zero
            
            cos_angle = dot_product / (norm_v1 * norm_v2)
            # Clamp value to avoid potential floating point issues with arccos
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            
            angle = np.degrees(np.arccos(cos_angle))
            return angle
        except Exception as e:
            logger.error(f"Error calculating angle for points {p1_idx},{p2_idx},{p3_idx}: {str(e)}")
            return None

    # Placeholder for methods from other services to be potentially merged here
    # def _load_pose_model ... from ml_model_service
    # def _load_form_comparison_model ... from ml_model_service
    # def _load_template_poses ... from ml_model_service
    # def _detect_exercise_phases ... from ai.py
    # def _generate_detailed_feedback ... maybe call BiomechanicsService?

    async def initialize_models(self):
        """Initialize AI models"""
        try:
            # TODO: Initialize actual models
            pass
        except Exception as e:
            raise AIServiceError(f"Failed to initialize AI models: {str(e)}")

    async def analyze_exercise_form(self, video_path: str) -> Dict[str, Any]:
        """Analyze exercise form using AI."""
        try:
            # Implementation for form analysis
            return {
                "score": 0.0,
                "feedback": [],
                "keypoints": [],
                "risk_level": "low"
            }
        except Exception as e:
            raise AIServiceError(f"Failed to analyze exercise form: {str(e)}")

    async def generate_workout_plan(
        self,
        user_level: str,
        goals: List[str],
        equipment: List[str],
        duration: int
    ) -> Dict[str, Any]:
        """Generate a personalized workout plan."""
        try:
            # Implementation for workout plan generation
            return {
                "plan": [],
                "duration": duration,
                "difficulty": user_level,
                "equipment_needed": equipment
            }
        except Exception as e:
            raise AIServiceError(f"Failed to generate workout plan: {str(e)}")

    async def suggest_exercises(
        self,
        exercise_type: ExerciseType,
        user_level: str,
        equipment: List[str]
    ) -> List[Dict[str, Any]]:
        """Suggest exercises based on type and user level."""
        try:
            # Implementation for exercise suggestions
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to suggest exercises: {str(e)}")

    async def analyze_progress(self, workout_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's workout progress."""
        try:
            # Implementation for progress analysis
            return {
                "improvements": [],
                "recommendations": [],
                "stats": {}
            }
        except Exception as e:
            raise AIServiceError(f"Failed to analyze progress: {str(e)}")

    async def generate_form_tips(self, exercise_type: ExerciseType) -> List[str]:
        """Generate form tips for a specific exercise type."""
        try:
            # Implementation for form tips generation
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to generate form tips: {str(e)}")

    async def predict_injury_risk(self, exercise_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict injury risk for an exercise."""
        try:
            # Implementation for injury risk prediction
            return {
                "risk_level": "low",
                "risk_factors": [],
                "recommendations": []
            }
        except Exception as e:
            raise AIServiceError(f"Failed to predict injury risk: {str(e)}")

    async def optimize_workout(
        self,
        current_plan: Dict[str, Any],
        user_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize a workout plan based on user feedback."""
        try:
            # Implementation for workout optimization
            return current_plan
        except Exception as e:
            raise AIServiceError(f"Failed to optimize workout: {str(e)}")

    def extract_frames(self, video_path: str, frame_rate: int = 30) -> List[np.ndarray]:
        """Extract frames from video at specified rate."""
        try:
            frames = []
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if frame_count % frame_rate == 0:
                    frames.append(frame)
                frame_count += 1
                
            cap.release()
            return frames
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            raise

    async def preprocess_video(self, video_path: str) -> str:
        """Preprocess video for analysis"""
        try:
            # TODO: Implement video preprocessing
            return video_path
        except Exception as e:
            raise AIServiceError(f"Failed to preprocess video: {str(e)}")

    async def extract_pose_landmarks(self, frame: np.ndarray) -> Dict:
        """Extract pose landmarks from frame"""
        try:
            # TODO: Implement pose landmark extraction
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to extract pose landmarks: {str(e)}")

    async def analyze_pose_sequence(self, landmarks: List[Dict]) -> Dict:
        """Analyze sequence of pose landmarks"""
        try:
            # TODO: Implement pose sequence analysis
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to analyze pose sequence: {str(e)}")

    async def generate_feedback(self, analysis: Dict) -> str:
        """Generate feedback based on analysis"""
        try:
            # TODO: Implement feedback generation
            return "Good form!"
        except Exception as e:
            raise AIServiceError(f"Failed to generate feedback: {str(e)}")

    async def detect_exercise_phases(self, landmarks: List[Dict]) -> List[Dict]:
        """Detect different phases of the exercise"""
        try:
            # TODO: Implement phase detection
            return []
        except Exception as e:
            raise AIServiceError(f"Failed to detect exercise phases: {str(e)}")

    async def calculate_joint_angles(self, landmarks: Dict) -> Dict:
        """Calculate joint angles from landmarks"""
        try:
            # TODO: Implement joint angle calculation
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to calculate joint angles: {str(e)}")

    async def analyze_form_with_low_confidence(self, video_path: str, exercise_type: ExerciseType) -> Dict:
        """Analyze form when confidence is low"""
        try:
            # TODO: Implement low confidence analysis
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to analyze form with low confidence: {str(e)}")

    async def handle_model_error(self, video_path: str, error: Exception) -> Dict:
        """Handle model errors gracefully"""
        try:
            # TODO: Implement error handling
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to handle model error: {str(e)}")

    async def validate_video_duration(self, video_path: str) -> bool:
        """Validate video duration"""
        try:
            # TODO: Implement video duration validation
            return True
        except Exception as e:
            raise AIServiceError(f"Failed to validate video duration: {str(e)}")

    async def get_exercise_specific_thresholds(self, exercise_type: ExerciseType) -> Dict:
        """Get exercise-specific thresholds"""
        try:
            # TODO: Implement threshold retrieval
            return {}
        except Exception as e:
            raise AIServiceError(f"Failed to get exercise thresholds: {str(e)}")

    async def save_analysis_debug_info(self, video_path: str, analysis: Dict, output_path: str):
        """Save debug information for analysis"""
        try:
            # TODO: Implement debug information saving
            logger.info(f"Debug info for {video_path} would be saved to {output_path} with data: {analysis}")
            pass # Placeholder
        except Exception as e:
            raise AIServiceError(f"Failed to save debug info: {str(e)}")

    async def process_frames_for_pose(
        self,
        frames_data_np: List[np.ndarray], # MODIFIED: from frame_paths to frames_data_np
        min_pose_confidence_threshold: Optional[float] = None
    ) -> List[Optional[List[Optional[Dict[str, float]]]]]:
        """
        Processes a list of frame image numpy arrays to detect pose landmarks.
        Ensures each frame's result is a list of NUM_EXPECTED_LANDMARKS items (Optional[Dict])
        or None if the frame is unusable.

        Args:
            frames_data_np: A list of frame images as NumPy arrays.
            min_pose_confidence_threshold: The minimum confidence for overall pose detection per frame
                                           and for individual landmark visibility.

        Returns:
            A list where each outer list element corresponds to a frame:
            - None: if the overall pose confidence for the frame is below the threshold,
                    if the frame cannot be read, if MediaPipe detects no landmarks, 
                    or if an error occurs during processing for that frame.
            - List[Optional[Dict[str, float]]]: A list of length NUM_EXPECTED_LANDMARKS.
              Each inner list element is either a landmark Dict (if detected and visible)
              or None (if not detected or below visibility threshold).
        """
        logger.info(f"AIService: Starting pose processing for {len(frames_data_np)} frames with threshold {min_pose_confidence_threshold}.")
        
        if min_pose_confidence_threshold is None:
            logger.warning("min_pose_confidence_threshold not provided to process_frames_for_pose, using AI_MIN_DETECTION_CONFIDENCE as fallback.")
            min_pose_confidence_threshold = self.settings.AI_MIN_DETECTION_CONFIDENCE # Use self.settings

        all_frame_results: List[Optional[List[Optional[Dict[str, float]]]]] = []

        for i, frame_np in enumerate(frames_data_np): # MODIFIED: iterate over frames_data_np
            try:
                # frame = await asyncio.to_thread(cv2.imread, frame_path) # REMOVED
                if frame_np is None: # ADDED: Check if the numpy array itself is None
                    logger.warning(f"AIService: Received None for frame {i+1}/{len(frames_data_np)}")
                    all_frame_results.append(None)
                    continue

                # raw_landmarks_from_mp is List[Dict[str, float]] (guaranteed 33 if pose detected)
                # overall_frame_confidence is float
                raw_landmarks_from_mp, overall_frame_confidence = await asyncio.to_thread(self.detect_pose, frame_np) # Pass frame_np

                if overall_frame_confidence < min_pose_confidence_threshold or not raw_landmarks_from_mp:
                    log_msg = f"AIService: Frame {i+1}/{len(frames_data_np)} unusable. " # MODIFIED: Removed frame_path
                    if overall_frame_confidence < min_pose_confidence_threshold:
                        log_msg += f"Overall confidence ({overall_frame_confidence:.2f}) < threshold ({min_pose_confidence_threshold:.2f}). "
                    if not raw_landmarks_from_mp:
                        log_msg += "No landmarks detected by MediaPipe."
                    logger.debug(log_msg.strip())
                    all_frame_results.append(None)
                    continue
                
                # Initialize with Nones for all expected landmarks
                output_landmarks_for_frame: List[Optional[Dict[str, float]]] = [None] * self.NUM_EXPECTED_LANDMARKS
                num_detected_raw = len(raw_landmarks_from_mp)
                visible_count = 0

                for lm_idx in range(self.NUM_EXPECTED_LANDMARKS):
                    if lm_idx < num_detected_raw: # Should always be true if raw_landmarks_from_mp is not empty
                        landmark_data = raw_landmarks_from_mp[lm_idx]
                        if landmark_data.get('visibility', 0.0) >= min_pose_confidence_threshold:
                            output_landmarks_for_frame[lm_idx] = landmark_data
                            visible_count += 1
                        # else: it remains None, correctly indicating low visibility or absence
                    # else: lm_idx >= num_detected_raw, means MediaPipe returned fewer than expected, remains None

                logger.debug(
                    f"AIService: Frame {i+1}/{len(frames_data_np)} ({frame_np}): Processed. "
                    f"Overall confidence: {overall_frame_confidence:.2f}. "
                    f"MediaPipe detected: {num_detected_raw}. Visible (>= threshold): {visible_count}/{self.NUM_EXPECTED_LANDMARKS}."
                )
                all_frame_results.append(output_landmarks_for_frame)

            except Exception as e:
                logger.error(f"AIService: Error processing frame {i+1}/{len(frames_data_np)} ({frame_np}) for pose: {e}", exc_info=True)
                all_frame_results.append(None)
        
        processed_count = sum(1 for lm_list in all_frame_results if lm_list is not None)
        total_frames = len(frames_data_np)
        missing_ratio = round(1.0 - (processed_count / total_frames), 4) if total_frames > 0 else 1.0

        logger.info(
            "AIService pose_extraction: model_complexity=%d total_frames=%d "
            "frames_detected=%d missing_ratio=%.4f pose_complexity_fallback=%s",
            self._pose_complexity_used,
            total_frames,
            processed_count,
            missing_ratio,
            self._pose_complexity_fallback,
        )
        return all_frame_results

    # Helper function for linear interpolation of landmark data
    def _interpolate_landmark(
        self, 
        lm_prev: Optional[Dict[str, float]], 
        lm_next: Optional[Dict[str, float]], 
        ratio: float
    ) -> Optional[Dict[str, float]]:
        if lm_prev is None or lm_next is None:
            return None # Cannot interpolate if one of the endpoints is missing

        # Ensure all required keys are present; use .get for safety
        x_prev, y_prev, z_prev, vis_prev = lm_prev.get('x'), lm_prev.get('y'), lm_prev.get('z'), lm_prev.get('visibility')
        x_next, y_next, z_next, vis_next = lm_next.get('x'), lm_next.get('y'), lm_next.get('z'), lm_next.get('visibility')

        if any(v is None for v in [x_prev, y_prev, z_prev, vis_prev, x_next, y_next, z_next, vis_next]):
            logger.debug("Interpolation skipped due to missing coordinate/visibility in source landmarks.")
            return None # Not enough data to interpolate

        # Interpolate coordinates
        interp_x = x_prev + (x_next - x_prev) * ratio
        interp_y = y_prev + (y_next - y_prev) * ratio
        interp_z = z_prev + (z_next - z_prev) * ratio
        # Interpolate visibility (or use a fixed value like 0.5 to mark as interpolated)
        interp_vis = vis_prev + (vis_next - vis_prev) * ratio 
        # Alternatively, could set interp_vis = min(vis_prev, vis_next) or a fixed value e.g. 0.5

        return {"x": interp_x, "y": interp_y, "z": interp_z, "visibility": interp_vis}

    async def smooth_and_interpolate_poses(
        self,
        pose_sequence: List[Optional[List[Optional[Dict[str, float]]]]],
        num_expected_landmarks: int = 33,
        smoothing_window_size: int = 5, # Must be odd
        max_interpolation_gap: int = 3 
    ) -> List[Optional[List[Optional[Dict[str, float]]]]]:
        """
        Smooths and interpolates a sequence of pose landmarks.

        Assumes input pose_sequence[frame_idx] is either None or a list of 
        `num_expected_landmarks` items, where each is Optional[Dict[str, float]].
        """
        if not pose_sequence:
            return []

        num_frames = len(pose_sequence)
        if num_frames < 3: # Not enough data for meaningful smoothing/interpolation
            logger.info("Pose sequence too short for smoothing/interpolation, returning as is.")
            return pose_sequence

        # --- Step 1: Restructure data into per-landmark trajectories ---
        # trajectories[landmark_idx][frame_idx] = Optional[Dict[str, float]]
        trajectories: List[List[Optional[Dict[str, float]]]] = [
            [None] * num_frames for _ in range(num_expected_landmarks)
        ]

        for frame_idx, frame_landmarks_list in enumerate(pose_sequence):
            if frame_landmarks_list is not None:
                if len(frame_landmarks_list) != num_expected_landmarks:
                    logger.warning(
                        f"Frame {frame_idx} has {len(frame_landmarks_list)} landmarks, "
                        f"expected {num_expected_landmarks}. Skipping this frame for smoothing/interpolation."
                    )
                    # To handle this, we mark all landmarks for this frame as None in trajectories
                    for lm_idx in range(num_expected_landmarks):
                        trajectories[lm_idx][frame_idx] = None
                    continue 
                for lm_idx in range(num_expected_landmarks):
                    trajectories[lm_idx][frame_idx] = frame_landmarks_list[lm_idx]
        
        processed_trajectories = [[None] * num_frames for _ in range(num_expected_landmarks)]

        # --- Step 2 & 3: Interpolation and Smoothing per landmark trajectory ---
        for lm_idx in range(num_expected_landmarks):
            current_trajectory = trajectories[lm_idx]
            interpolated_trajectory: List[Optional[Dict[str, float]]] = [None] * num_frames
            
            # --- Interpolation Pass ---
            for frame_idx in range(num_frames):
                if current_trajectory[frame_idx] is not None:
                    interpolated_trajectory[frame_idx] = current_trajectory[frame_idx]
                else: # Attempt to interpolate
                    prev_lm_data, next_lm_data = None, None
                    prev_lm_frame_idx, next_lm_frame_idx = -1, -1

                    # Find previous valid landmark
                    for k in range(1, max_interpolation_gap + 1):
                        if frame_idx - k >= 0 and current_trajectory[frame_idx - k] is not None:
                            prev_lm_data = current_trajectory[frame_idx - k]
                            prev_lm_frame_idx = frame_idx - k
                            break
                    
                    # Find next valid landmark
                    for k in range(1, max_interpolation_gap + 1):
                        if frame_idx + k < num_frames and current_trajectory[frame_idx + k] is not None:
                            next_lm_data = current_trajectory[frame_idx + k]
                            next_lm_frame_idx = frame_idx + k
                            break
                    
                    if prev_lm_data and next_lm_data and (next_lm_frame_idx - prev_lm_frame_idx <= max_interpolation_gap +1 ): # Check gap validity
                        # Calculate interpolation ratio
                        ratio = (frame_idx - prev_lm_frame_idx) / (next_lm_frame_idx - prev_lm_frame_idx)
                        interpolated_landmark = self._interpolate_landmark(prev_lm_data, next_lm_data, ratio)
                        if interpolated_landmark:
                            interpolated_trajectory[frame_idx] = interpolated_landmark
                        else: # Fallback if interpolation failed for some reason
                            interpolated_trajectory[frame_idx] = None 
                    else: # Could not interpolate
                        interpolated_trajectory[frame_idx] = None
            
            # --- Smoothing Pass (Moving Average) ---
            # Ensure smoothing_window_size is odd
            if smoothing_window_size % 2 == 0:
                logger.warning("Smoothing window size must be odd. Adjusting to next odd number.")
                smoothing_window_size +=1
            
            half_window = smoothing_window_size // 2
            smoothed_trajectory: List[Optional[Dict[str, float]]] = list(interpolated_trajectory) # Start with interpolated

            for frame_idx in range(num_frames):
                if interpolated_trajectory[frame_idx] is None: # Cannot smooth if no data
                    continue

                window_landmarks = []
                for k_offset in range(-half_window, half_window + 1):
                    win_frame_idx = frame_idx + k_offset
                    if 0 <= win_frame_idx < num_frames and interpolated_trajectory[win_frame_idx] is not None:
                        window_landmarks.append(interpolated_trajectory[win_frame_idx])
                
                if not window_landmarks: # Should not happen if interpolated_trajectory[frame_idx] is not None
                    continue

                # Average coordinates and visibility
                avg_x = sum(lm['x'] for lm in window_landmarks if lm and 'x' in lm) / len(window_landmarks)
                avg_y = sum(lm['y'] for lm in window_landmarks if lm and 'y' in lm) / len(window_landmarks)
                avg_z = sum(lm['z'] for lm in window_landmarks if lm and 'z' in lm) / len(window_landmarks)
                # Keep original visibility or average it too? For now, keep original from interpolated.
                # If averaging visibility: avg_vis = sum(lm['visibility'] for lm in window_landmarks) / len(window_landmarks)
                
                # Create a new dictionary for the smoothed landmark to avoid modifying the original from interpolated_trajectory
                smoothed_trajectory[frame_idx] = {
                    "x": avg_x, "y": avg_y, "z": avg_z,
                    "visibility": interpolated_trajectory[frame_idx]['visibility'] # Keep interpolated visibility
                }
            processed_trajectories[lm_idx] = smoothed_trajectory

        # --- Step 4: Reconstruct the output sequence ---
        final_pose_sequence: List[Optional[List[Optional[Dict[str, float]]]]] = [None] * num_frames
        for frame_idx in range(num_frames):
            # Check if all landmarks for this frame are None after processing
            # This could happen if the original frame was None, or if interpolation/smoothing failed for all landmarks.
            # A frame should be considered "present" if at least one landmark is present.
            
            landmarks_for_this_frame: List[Optional[Dict[str, float]]] = [
                processed_trajectories[lm_idx][frame_idx] for lm_idx in range(num_expected_landmarks)
            ]

            # If the original frame was None (e.g. process_frames_for_pose returned None for it),
            # we should respect that and keep it None, unless interpolation specifically filled it.
            # The current logic populates processed_trajectories even for initially None frames if interpolation occurs.
            # Let's decide: if pose_sequence[frame_idx] was None, the result should also be None,
            # unless we specifically want interpolation to "create" frames.
            # For now, if original pose_sequence[frame_idx] was None, let's ensure final_pose_sequence[frame_idx] is None.
            if pose_sequence[frame_idx] is None:
                 final_pose_sequence[frame_idx] = None
            elif any(lm is not None for lm in landmarks_for_this_frame): # Frame has at least one landmark
                final_pose_sequence[frame_idx] = landmarks_for_this_frame
            else: # Frame had no valid landmarks after processing
                final_pose_sequence[frame_idx] = None # Or an empty list if that's preferred: []
                                                     # Current type hint expects List[Optional[...]] so None for the whole frame is okay.
        
        logger.info(f"AIService: Pose sequence smoothing and interpolation completed for {num_frames} frames.")
        return final_pose_sequence 

    def smooth_angle_trajectories(
        self,
        raw_angles_per_frame: List[Optional[Dict[str, float]]],
        smoothing_window: int = 5,
        max_gap_to_interpolate: int = 3 # Max frames to interpolate angles over
    ) -> List[Optional[Dict[str, Optional[float]]]]:
        """
        Smooths angle trajectories for each joint using a moving average and interpolates small gaps.

        Args:
            raw_angles_per_frame: List of dictionaries, where each dict contains {angle_name: value}
                                  for a frame. Frames can be None if no angles were calculated.
            smoothing_window: The size of the moving average window (should be odd).
            max_gap_to_interpolate: Maximum number of consecutive None frames for an angle to interpolate.

        Returns:
            A list of dictionaries of the same shape, with smoothed angle values.
        """
        if not raw_angles_per_frame:
            return []

        num_frames = len(raw_angles_per_frame)
        if num_frames == 0:
            return []

        # Ensure smoothing_window is odd
        if smoothing_window % 2 == 0:
            smoothing_window += 1
        half_window = smoothing_window // 2

        # Get all unique angle names from the first valid frame
        all_angle_names = set()
        for frame_angles in raw_angles_per_frame:
            if frame_angles:
                all_angle_names.update(frame_angles.keys())
        
        if not all_angle_names: # No angles found in any frame
            return [None] * num_frames


        # Restructure data: angle_trajectories[angle_name][frame_idx] = Optional[float]
        angle_trajectories: Dict[str, List[Optional[float]]] = {
            name: [None] * num_frames for name in all_angle_names
        }

        for frame_idx, frame_angles_dict in enumerate(raw_angles_per_frame):
            if frame_angles_dict:
                for angle_name in all_angle_names:
                    angle_trajectories[angle_name][frame_idx] = frame_angles_dict.get(angle_name)
        
        smoothed_angle_trajectories: Dict[str, List[Optional[float]]] = {
            name: [None] * num_frames for name in all_angle_names
        }

        for angle_name, trajectory in angle_trajectories.items():
            # 1. Interpolation pass
            interpolated_trajectory = list(trajectory) # Work on a copy
            for i in range(num_frames):
                if interpolated_trajectory[i] is None:
                    # Look for previous and next valid points within max_gap
                    prev_val, next_val = None, None
                    prev_idx, next_idx = -1, -1

                    # Search backward
                    for k in range(1, max_gap_to_interpolate + 1):
                        if i - k >= 0 and interpolated_trajectory[i - k] is not None:
                            prev_val = interpolated_trajectory[i - k]
                            prev_idx = i - k
                            break
                    
                    # Search forward
                    for k in range(1, max_gap_to_interpolate + 1):
                        if i + k < num_frames and interpolated_trajectory[i + k] is not None:
                            next_val = interpolated_trajectory[i + k]
                            next_idx = i + k
                            break
                    
                    if prev_val is not None and next_val is not None and (next_idx - prev_idx <= max_gap_to_interpolate +1) : # Ensure the gap is not too large overall
                        # Linear interpolation
                        ratio = (i - prev_idx) / (next_idx - prev_idx)
                        interpolated_trajectory[i] = prev_val + ratio * (next_val - prev_val)

            # 2. Smoothing pass (Moving Average on interpolated_trajectory)
            current_smoothed_trajectory = list(interpolated_trajectory) # Start with interpolated
            for i in range(num_frames):
                if interpolated_trajectory[i] is None: # Cannot smooth if no data point
                    continue

                window_values = []
                for k_offset in range(-half_window, half_window + 1):
                    win_idx = i + k_offset
                    if 0 <= win_idx < num_frames and interpolated_trajectory[win_idx] is not None:
                        window_values.append(interpolated_trajectory[win_idx])
                
                if window_values:
                    current_smoothed_trajectory[i] = sum(window_values) / len(window_values)
                # If window_values is empty but interpolated_trajectory[i] was not None,
                # it implies a very sparse region; keep the single interpolated point.
                # This is generally handled as current_smoothed_trajectory starts as a copy.

            smoothed_angle_trajectories[angle_name] = current_smoothed_trajectory

        # Reconstruct the output: List[Optional[Dict[str, Optional[float]]]]
        final_smoothed_angles_per_frame: List[Optional[Dict[str, Optional[float]]]] = [None] * num_frames
        for frame_idx in range(num_frames):
            if raw_angles_per_frame[frame_idx] is None: # Original frame was entirely None
                final_smoothed_angles_per_frame[frame_idx] = None
                continue

            # Initialize current_frame_angles_dict with all known angle names, defaulting to None.
            # This ensures that even if all smoothed values are None, the keys are preserved.
            current_frame_angles_dict: Dict[str, Optional[float]] = {
                name: None for name in all_angle_names
            }

            # Populate with actual smoothed values if they exist
            for angle_name in all_angle_names:
                smoothed_value = smoothed_angle_trajectories[angle_name][frame_idx]
                if smoothed_value is not None:
                    current_frame_angles_dict[angle_name] = smoothed_value
            
            final_smoothed_angles_per_frame[frame_idx] = current_frame_angles_dict
        
        return final_smoothed_angles_per_frame

    async def analyze_video_file_for_form_check(
        self,
        video_file_path: str,
        exercise_type: ExerciseType # Use the enum type
    ) -> Dict[str, Any]:
        """
        Analyzes a video file for form check, performs frame extraction, 
        pose detection, and form analysis using the best frame.
        This method encapsulates logic previously in FormCheckService.
        """
        logger.info(f"AIService: Analyzing video file {video_file_path} for exercise {exercise_type.value}")

        def _synchronous_frame_processing(path: str, ai_service_instance: 'AIService') -> List[Dict[str, Any]]:
            """Synchronous helper to process video frames using OpenCV and detect poses."""
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                logger.error(f"AIService: Could not open video file: {path}")
                raise IOError(f"Could not open video file: {path}")

            frame_results = []
            processed_frames = 0
            # Potentially use a setting for max_frames if different from pose detection default
            max_frames_to_process = settings.AI_MAX_FRAMES_PER_VIDEO_ANALYSIS or 300 

            while cap.isOpened() and processed_frames < max_frames_to_process:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Call the existing synchronous detect_pose method of this AIService instance
                landmarks, confidence = ai_service_instance.detect_pose(frame)
            
                if landmarks:
                    frame_results.append({"landmarks": landmarks, "confidence": confidence, "frame_index": processed_frames})
                processed_frames += 1

            cap.release()
            if processed_frames >= max_frames_to_process:
                logger.warning(f"AIService: Video {path} exceeded max frames ({max_frames_to_process}), processing truncated.")
            elif not frame_results:
                logger.warning(f"AIService: No landmarks detected in any frame for video {path}.")
            return frame_results

        try:
            # Run the synchronous OpenCV frame processing (including pose detection) in a separate thread
            # Pass 'self' (the AIService instance) to the threaded function to call self.detect_pose
            all_frame_landmark_results = await asyncio.to_thread(_synchronous_frame_processing, video_file_path, self)

            if not all_frame_landmark_results:
                logger.warning(f"AIService: No poses detected in video: {video_file_path}. Returning default/error structure.")
                return {
                    "score": 0.0, 
                    "feedback": ["No poses detected in the video. Unable to analyze form."], 
                    "risk_level": "high", 
                    "feedback_structured": [],
                    "model_version": self.model.version if hasattr(self.model, 'version') else "unknown_model_see_rules",
                    "video_hash": hashlib.md5(video_file_path.encode()).hexdigest() # Example hash
                }

            # Find the frame with the highest confidence for detailed analysis
            # (This is a simplification; a real system might analyze a sequence or key phases)
            best_frame_data = max(all_frame_landmark_results, key=lambda x: x["confidence"])
            logger.info(f"AIService: Best frame for analysis from {video_file_path} is index {best_frame_data.get('frame_index')} with confidence {best_frame_data.get('confidence')}")
            
            # Call the existing async form analysis method (model + rules) of this AIService instance
            # analyze_form expects exercise_type as a string value from the enum
            analysis_results = await self.analyze_form(
                landmarks=best_frame_data["landmarks"],
                exercise_type=exercise_type.value 
            )
            
            # Add model version and a video hash (example) to the results
            analysis_results["model_version"] = self.model.version if self.model and hasattr(self.model, 'version') else "rule_based_or_unknown_model"
            
            # Calculate a hash of the video file for potential caching key by the caller
            # This is a basic example; a more robust hash might read file content.
            # However, video_file_path might be a temp path, so content hash is better if video content is available.
            # For simplicity, using path hash. Caller (Celery task) might generate a content hash earlier.
            analysis_results["video_hash"] = hashlib.md5(str(video_file_path).encode() + str(os.path.getmtime(video_file_path)).encode()).hexdigest()

            logger.info(f"AIService: Successfully analyzed video file {video_file_path} for {exercise_type.value}")
            return analysis_results

        except IOError as ioe:
            logger.error(f"AIService: Video IO error during analysis ({video_file_path}): {ioe}", exc_info=True)
            # Return a structured error that the Celery task can use
            return {"score": 0.0, "feedback": [f"Error accessing video file: {ioe}"], "risk_level": "high", "feedback_structured": [], "error_message": f"Video IO Error: {ioe}"}
        except Exception as e:
            logger.error(f"AIService: Unexpected error in analyze_video_file_for_form_check for {video_file_path}: {e}", exc_info=True)
            return {"score": 0.0, "feedback": ["Video analysis failed due to an unexpected internal AI service error."], "risk_level": "high", "feedback_structured": [], "error_message": f"AI Service Error: {e}"} 

    async def process_np_frames_for_pose(
        self, 
        frames: List[np.ndarray], 
        min_pose_confidence_threshold: Optional[float] = None
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Detects poses in a list of NumPy frames using optimized batch processing.
        This method uses batch processing and GPU acceleration when available for improved performance.

        Args:
            frames: A list of video frames, where each frame is a NumPy array (BGR format).
            min_pose_confidence_threshold: Optional minimum confidence for a pose to be considered valid.
                                           If None, uses default from settings or class.

        Returns:
            A list of pose results. Each element corresponds to a frame:
            - If pose detected above threshold: Dict{"landmarks": List[Dict], "confidence": float}
            - If pose not detected or below threshold: None
        """
        if not frames:
            return []

        # Use the class's configured min_detection_confidence if not overridden
        threshold = min_pose_confidence_threshold if min_pose_confidence_threshold is not None \
                    else self.settings.AI_MIN_DETECTION_CONFIDENCE

        logger.info(f"Processing {len(frames)} frames for pose detection with batch size {self.batch_size}")
        start_time = time.time()

        # Use optimized batch processing
        if self.use_gpu_acceleration and len(frames) >= self.batch_size:
            all_frame_pose_data = await self._process_frames_batch_gpu(frames, threshold)
        else:
            all_frame_pose_data = await self._process_frames_batch_cpu(frames, threshold)
        
        processing_time = time.time() - start_time
        valid_detections = sum(1 for result in all_frame_pose_data if result is not None)
        
        total_frames = len(frames)
        missing_ratio = round(1.0 - (valid_detections / total_frames), 4) if total_frames > 0 else 1.0
        logger.info(
            "AIService pose_extraction: model_complexity=%d total_frames=%d "
            "frames_detected=%d missing_ratio=%.4f pose_extraction_ms=%.1f "
            "pose_complexity_fallback=%s",
            self._pose_complexity_used,
            total_frames,
            valid_detections,
            missing_ratio,
            processing_time * 1000,
            self._pose_complexity_fallback,
        )

        return all_frame_pose_data

    async def _process_frames_batch_cpu(
        self, 
        frames: List[np.ndarray], 
        threshold: float
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Process frames using CPU-based batch processing with optimized threading.
        """
        all_frame_pose_data: List[Optional[Dict[str, Any]]] = []
        
        # Process frames in batches for better memory management
        for i in range(0, len(frames), self.batch_size):
            batch = frames[i:i + self.batch_size]
            batch_results = await self._process_frame_batch_parallel(batch, threshold)
            all_frame_pose_data.extend(batch_results)
        
        return all_frame_pose_data

    async def _process_frames_batch_gpu(
        self, 
        frames: List[np.ndarray], 
        threshold: float
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Process frames using GPU acceleration when available.
        Falls back to CPU processing if GPU processing fails.
        """
        try:
            if self.gpu_pose is None:
                logger.warning("GPU pose model not available, falling back to CPU")
                return await self._process_frames_batch_cpu(frames, threshold)
            
            all_frame_pose_data: List[Optional[Dict[str, Any]]] = []
            
            # Process frames in optimized GPU batches
            for i in range(0, len(frames), self.batch_size):
                batch = frames[i:i + self.batch_size]
                batch_results = await self._process_gpu_batch(batch, threshold)
                all_frame_pose_data.extend(batch_results)
            
            return all_frame_pose_data
            
        except Exception as e:
            logger.warning(f"GPU batch processing failed: {e}, falling back to CPU")
            return await self._process_frames_batch_cpu(frames, threshold)

    async def _process_frame_batch_parallel(
        self, 
        batch: List[np.ndarray], 
        threshold: float
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Process a batch of frames in parallel using thread pool.
        """
        import concurrent.futures
        
        async def process_single_frame(frame: np.ndarray) -> Optional[Dict[str, Any]]:
            try:
                landmarks, confidence = await asyncio.to_thread(self.detect_pose, frame)
                
                if landmarks and confidence >= threshold:
                    return {
                        "landmarks": landmarks,
                        "confidence": confidence
                    }
                else:
                    return None
            except Exception as e:
                logger.error(f"Error processing frame in batch: {e}", exc_info=True)
                return None
        
        # Process all frames in the batch concurrently
        tasks = [process_single_frame(frame) for frame in batch if frame is not None]
        
        # Handle None frames in the batch
        results = []
        task_iter = iter(await asyncio.gather(*tasks, return_exceptions=True))
        
        for frame in batch:
            if frame is None:
                results.append(None)
            else:
                try:
                    result = next(task_iter)
                    if isinstance(result, Exception):
                        logger.error(f"Exception in parallel processing: {result}")
                        results.append(None)
                    else:
                        results.append(result)
                except StopIteration:
                    results.append(None)
        
        return results

    async def _process_gpu_batch(
        self, 
        batch: List[np.ndarray], 
        threshold: float
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Process a batch of frames using GPU-optimized MediaPipe.
        """
        async def process_frame_gpu(frame: np.ndarray) -> Optional[Dict[str, Any]]:
            try:
                # Use GPU pose model for faster processing
                landmarks, confidence = await asyncio.to_thread(self._detect_pose_gpu, frame)
                
                if landmarks and confidence >= threshold:
                    return {
                        "landmarks": landmarks,
                        "confidence": confidence
                    }
                else:
                    return None
            except Exception as e:
                logger.error(f"Error in GPU pose detection: {e}")
                return None
        
        # Process batch with GPU acceleration
        tasks = [process_frame_gpu(frame) for frame in batch if frame is not None]
        results = []
        task_iter = iter(await asyncio.gather(*tasks, return_exceptions=True))
        
        for frame in batch:
            if frame is None:
                results.append(None)
            else:
                try:
                    result = next(task_iter)
                    if isinstance(result, Exception):
                        logger.error(f"Exception in GPU processing: {result}")
                        results.append(None)
                    else:
                        results.append(result)
                except StopIteration:
                    results.append(None)
        
        return results

    def _detect_pose_gpu(self, frame: np.ndarray) -> Tuple[List[Dict[str, float]], float]:
        """
        GPU-optimized pose detection method.
        """
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False
            
            # Use GPU pose model if available
            pose_model = self.gpu_pose if self.gpu_pose else self.pose
            results = pose_model.process(frame_rgb)
            
            frame_rgb.flags.writeable = True
            
            if not results.pose_landmarks:
                return [], 0.0
                
            landmarks = []
            visibility_sum = 0.0
            lm_count = 0
            
            for landmark in results.pose_landmarks.landmark:
                landmarks.append({
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility
                })
                visibility_sum += landmark.visibility
                lm_count += 1
                
            confidence = (visibility_sum / lm_count) if lm_count > 0 else 0.0
            
            return landmarks, confidence
            
        except Exception as e:
            logger.error(f"Error in GPU pose detection: {str(e)}", exc_info=True)
            return [], 0.0

    async def analyze_form_sequence_with_sliding_window(
        self, 
        landmark_sequence: List[List[Dict[str, float]]], 
        exercise_type: str,
        window_size: int = 5,
        stride: int = 1,
        min_confidence: float = 0.6
    ) -> Dict[str, Any]:
        """
        Enhanced temporal sequence analysis using sliding window approach for improved accuracy.
        
        This method analyzes exercise form using overlapping windows of frames to capture
        temporal dependencies and movement patterns more effectively than single-frame analysis.
        
        Args:
            landmark_sequence: List of pose landmark sequences for multiple frames
            exercise_type: Type of exercise being analyzed
            window_size: Size of the sliding window (number of frames to analyze together)
            stride: Step size for sliding the window (1 = overlap all frames)
            min_confidence: Minimum confidence threshold for analysis
            
        Returns:
            Dictionary with enhanced temporal analysis results including:
            - Aggregated scoring across windows
            - Movement quality assessment
            - Temporal consistency metrics
            - Window-by-window breakdown
        """
        if not landmark_sequence or len(landmark_sequence) < window_size:
            logger.warning(f"Sequence too short for sliding window analysis: {len(landmark_sequence) if landmark_sequence else 0} frames, need at least {window_size}")
            return await self.analyze_form_sequence(landmark_sequence, exercise_type, min_confidence)
        
        logger.info(f"Starting sliding window temporal analysis for {exercise_type} with {len(landmark_sequence)} frames, "
                   f"window_size={window_size}, stride={stride}")
        
        def _run_sliding_window_analysis():
            try:
                window_results = []
                window_scores = []
                window_confidences = []
                
                # Generate sliding windows
                for start_idx in range(0, len(landmark_sequence) - window_size + 1, stride):
                    end_idx = start_idx + window_size
                    window_sequence = landmark_sequence[start_idx:end_idx]
                    
                    # Analyze each window
                    try:
                        window_result = self._analyze_window_sequence(
                            window_sequence, exercise_type, min_confidence, start_idx
                        )
                        window_results.append(window_result)
                        window_scores.append(window_result['score'])
                        window_confidences.append(window_result.get('confidence', 0.5))
                        
                    except Exception as e:
                        logger.warning(f"Window analysis failed for frames {start_idx}-{end_idx}: {e}")
                        continue
                
                if not window_results:
                    raise ValueError("No valid window results obtained")
                
                # Aggregate window results with temporal weighting
                aggregated_result = self._aggregate_window_results(
                    window_results, window_scores, window_confidences, landmark_sequence
                )
                
                # Add sliding window metadata
                aggregated_result.update({
                    "analysis_method": "sliding_window_temporal",
                    "window_analysis": {
                        "window_size": window_size,
                        "stride": stride,
                        "total_windows": len(window_results),
                        "window_scores": window_scores,
                        "window_confidences": window_confidences
                    }
                })
                
                return aggregated_result
                
            except Exception as e:
                logger.error(f"Sliding window analysis failed: {e}", exc_info=True)
                # Fallback to regular temporal analysis
                logger.info("Falling back to regular temporal sequence analysis")
                return asyncio.run(self.analyze_form_sequence(landmark_sequence, exercise_type, min_confidence))
        
        # Run the sliding window analysis
        return await asyncio.to_thread(_run_sliding_window_analysis)

    def _analyze_window_sequence(
        self, 
        window_sequence: List[List[Dict[str, float]]], 
        exercise_type: str, 
        min_confidence: float,
        start_frame: int
    ) -> Dict[str, Any]:
        """
        Analyze a single window of frames for temporal patterns.
        """
        if self.use_ml_models and exercise_type.lower() == 'squat' and self.enhanced_squat_model.is_model_available():
            # Extract features for the window
            feature_sequence = []
            for frame_landmarks in window_sequence:
                try:
                    # Feature extractor expects a sequence, so wrap single frame
                    frame_features = self.squat_feature_extractor.extract_features([frame_landmarks])
                    feature_sequence.append(frame_features)
                except Exception as e:
                    logger.warning(f"Feature extraction failed for window frame: {e}")
                    continue
            
            if not feature_sequence:
                raise ValueError("No valid features extracted from window")
            
            # Use temporal prediction on the window
            temporal_results = self.enhanced_squat_model.predict_temporal_sequence(
                feature_sequence, min_confidence
            )
            
            return {
                "score": temporal_results['temporal_confidence'] * 100,
                "confidence": temporal_results['temporal_confidence'],
                "is_good_form": temporal_results['is_good_form'],
                "stability": temporal_results['temporal_stability'],
                "consistency": temporal_results['consistency_score'],
                "movement_quality": temporal_results['movement_quality'],
                "start_frame": start_frame,
                "frame_count": len(window_sequence)
            }
        else:
            # Fallback to rule-based analysis for the window
            window_scores = []
            for frame_landmarks in window_sequence:
                try:
                    frame_result = self._run_single_frame_analysis(frame_landmarks, exercise_type)
                    window_scores.append(frame_result['score'])
                except Exception:
                    continue
            
            if window_scores:
                avg_score = np.mean(window_scores)
                consistency = 1.0 - (np.std(window_scores) / (np.mean(window_scores) + 1e-6))
                
                return {
                    "score": avg_score,
                    "confidence": min(1.0, consistency),
                    "is_good_form": avg_score > 60,
                    "stability": consistency,
                    "consistency": consistency,
                    "movement_quality": {"consistency": consistency},
                    "start_frame": start_frame,
                    "frame_count": len(window_sequence)
                }
            else:
                raise ValueError("No valid frame analysis in window")

    def _aggregate_window_results(
        self, 
        window_results: List[Dict[str, Any]], 
        window_scores: List[float], 
        window_confidences: List[float],
        full_sequence: List[List[Dict[str, float]]]
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple sliding windows using temporal weighting.
        """
        # Calculate temporal weights (center frames get higher weight)
        total_frames = len(full_sequence)
        weights = []
        
        for i, result in enumerate(window_results):
            start_frame = result['start_frame']
            window_center = start_frame + (result['frame_count'] // 2)
            
            # Weight based on distance from sequence center and confidence
            center_distance = abs(window_center - (total_frames // 2)) / (total_frames // 2)
            temporal_weight = 1.0 - (center_distance * 0.3)  # Reduce weight by up to 30% for edge frames
            confidence_weight = window_confidences[i]
            
            combined_weight = temporal_weight * confidence_weight
            weights.append(combined_weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)
        
        # Weighted aggregation
        final_score = sum(score * weight for score, weight in zip(window_scores, weights))
        final_confidence = sum(conf * weight for conf, weight in zip(window_confidences, weights))
        
        # Aggregate other metrics
        stabilities = [r.get('stability', 0.5) for r in window_results]
        consistencies = [r.get('consistency', 0.5) for r in window_results]
        
        final_stability = sum(stab * weight for stab, weight in zip(stabilities, weights))
        final_consistency = sum(cons * weight for cons, weight in zip(consistencies, weights))
        
        # Movement trend analysis
        score_trend = np.gradient(window_scores)
        is_improving = np.mean(score_trend) > 0.1
        
        # Generate comprehensive feedback
        feedback_messages = []
        feedback_structured = []
        
        # Overall performance feedback
        if final_score >= 80 and final_stability >= 0.8:
            feedback_messages.append(f"Excellent form with consistent movement (score: {final_score:.1f}%)")
            feedback_structured.append({
                "type": FeedbackType.TECHNIQUE,
                "message": f"Outstanding temporal form analysis! Score: {final_score:.1f}%",
                "timestamp": 0.0,
                "severity": FeedbackSeverity.LOW
            })
            risk_level = "low"
        elif final_score >= 60:
            feedback_messages.append(f"Good form with room for improvement (score: {final_score:.1f}%)")
            feedback_structured.append({
                "type": FeedbackType.TECHNIQUE,
                "message": f"Good form detected with temporal analysis. Score: {final_score:.1f}%",
                "timestamp": 0.0,
                "severity": FeedbackSeverity.MEDIUM
            })
            risk_level = "medium"
        else:
            feedback_messages.append(f"Form needs significant improvement (score: {final_score:.1f}%)")
            feedback_structured.append({
                "type": FeedbackType.TECHNIQUE,
                "message": f"Form issues detected. Score: {final_score:.1f}%",
                "timestamp": 0.0,
                "severity": FeedbackSeverity.HIGH
            })
            risk_level = "high"
        
        # Stability feedback
        if final_stability < 0.6:
            feedback_messages.append("Focus on movement stability - detected shaky or inconsistent movement")
            feedback_structured.append({
                "type": FeedbackType.ALIGNMENT,
                "message": f"Movement stability needs improvement (score: {final_stability:.2f})",
                "timestamp": 0.0,
                "severity": FeedbackSeverity.MEDIUM,
                "suggestions": ["Slow down the movement", "Engage core muscles", "Focus on control"]
            })
        
        # Trend feedback
        if is_improving:
            feedback_messages.append("Positive trend - your form is improving throughout the movement")
            feedback_structured.append({
                "type": FeedbackType.TECHNIQUE,
                "message": "Good improvement trend detected across the movement",
                "timestamp": 0.0,
                "severity": FeedbackSeverity.LOW
            })
        
        return {
            "score": final_score,
            "feedback": feedback_messages,
            "risk_level": risk_level,
            "feedback_structured": feedback_structured,
            "temporal_metrics": {
                "temporal_confidence": final_confidence,
                "temporal_stability": final_stability,
                "consistency_score": final_consistency,
                "improvement_trend": is_improving,
                "frame_count": total_frames,
                "window_count": len(window_results)
            },
            "movement_quality": {
                "consistency": final_consistency,
                "stability": final_stability,
                "trend": "improving" if is_improving else "stable",
                "average_confidence": final_confidence
            }
        }

    async def calculate_angles_for_pose_sequence(
        self,
        pose_sequence: List[Optional[List[Optional[Dict[str, Any]]]]],
        # exercise_type_str: Optional[str] = None # Removed, as per generalization requirement
    ) -> List[Optional[Dict[str, float]]]:
        """
        Calculates all defined joint angles for each frame in a pose sequence.
        Uses UNIVERSAL_ANGLE_DEFINITIONS for angle computation.

        Args:
            pose_sequence: A list where each item is a frame. Each frame is either:
                           - None (if the frame was unusable or pose not detected confidently)
                           - A list of landmarks for that frame. Each landmark is either:
                             - A dict with {'x', 'y', 'z', 'visibility'}
                             - None (if that specific landmark was not visible/detected)

        Returns:
            A list of dictionaries, one for each frame. Each dictionary contains {angle_name: value}
            for all calculable angles in UNIVERSAL_ANGLE_DEFINITIONS.
            If a frame was None in the input, or if no angles could be calculated for a frame (e.g., all landmarks missing),
            the corresponding item in the output list will be None.
            If a frame was valid but some specific angles couldn't be computed (due to missing specific landmarks for that angle),
            those angles will be absent from the frame's dictionary.
        """
        logger.debug(f"Starting angle calculation for a sequence of {len(pose_sequence)} frames.")
        all_frames_angles: List[Optional[Dict[str, float]]] = []

        if not pose_sequence:
            return []

        for frame_idx, frame_landmarks_list in enumerate(pose_sequence):
            # frame_landmarks_list is List[Optional[Dict[str, Any]]] or None
            if frame_landmarks_list is None:
                # This frame was marked as unusable (e.g. low confidence, no landmarks from MediaPipe)
                logger.debug(f"Frame {frame_idx}: Skipping angle calculation, frame_landmarks_list is None.")
                all_frames_angles.append(None)
                continue

            # Ensure frame_landmarks_list has the expected structure if not None
            # It should be a list of landmarks (or None for individual missing landmarks)
            if not isinstance(frame_landmarks_list, list):
                logger.warning(f"Frame {frame_idx}: Expected list of landmarks, got {type(frame_landmarks_list)}. Skipping.")
                all_frames_angles.append(None)
                continue
            
            # Check if the list of landmarks is empty (should not happen if not None, but defensive)
            if not frame_landmarks_list: # an empty list
                logger.debug(f"Frame {frame_idx}: Landmark list is empty. No angles to calculate.")
                all_frames_angles.append({})
                continue


            frame_angles: Dict[str, float] = {}
            # Iterate through all angles defined in UNIVERSAL_ANGLE_DEFINITIONS
            for angle_name, points in UNIVERSAL_ANGLE_DEFINITIONS.items():
                p1_idx, p2_idx, p3_idx = points["p1_idx"], points["p2_idx"], points["p3_idx"]
                
                # _calculate_angle expects a list of landmark dicts or Nones
                # frame_landmarks_list is List[Optional[Dict[str, float]]]
                angle_value = self._calculate_angle(frame_landmarks_list, p1_idx, p2_idx, p3_idx)
                
                if angle_value is not None:
                    frame_angles[angle_name] = angle_value
                # else: angle could not be computed, so it's omitted from frame_angles
            
            # If no angles were calculated for this frame (e.g., all necessary landmarks missing),
            # still append a dictionary, possibly empty, to maintain sequence length.
            # If frame_angles is empty, it means no universal angles could be calculated.
            all_frames_angles.append(frame_angles) 
            logger.debug(f"Frame {frame_idx}: Calculated {len(frame_angles)} angles.")

        return all_frames_angles

