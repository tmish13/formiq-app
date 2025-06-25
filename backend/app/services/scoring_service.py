"""
Exercise Form Scoring Service

Converts ML model fault classifications into meaningful user scores (0-100).
Based on biomechanical research and exercise-specific scoring criteria.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from app.core.logging import get_logger
from app.core.config import Settings

logger = get_logger(__name__)


@dataclass
class MLModelResults:
    """Container for ML model outputs."""
    posture_fault: bool
    stability_fault: bool
    depth_fault: bool
    good_form: bool
    confidence: float
    exercise_type: str


@dataclass
class ExerciseScores:
    """Container for calculated exercise scores."""
    posture_score: float  # 0-100
    stability_score: float  # 0-100
    depth_score: float  # 0-100
    overall_score: float  # 0-100
    confidence_level: str  # "high", "medium", "low"


class ScoringService:
    """
    Service for converting ML model fault classifications into user-friendly scores.
    
    Scoring Philosophy:
    - 90-100: Excellent form (no faults detected)
    - 70-89: Good form (minor issues)
    - 50-69: Fair form (moderate issues, needs attention)
    - 30-49: Poor form (significant issues)
    - 0-29: Dangerous form (major faults, risk of injury)
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the scoring service."""
        self.settings = settings
        
        # Exercise-specific scoring weights
        self.exercise_weights = {
            'squat': {
                'posture': 0.4,    # Critical for back safety
                'depth': 0.35,     # Essential for effectiveness
                'stability': 0.25  # Important for knee safety
            },
            'deadlift': {
                'posture': 0.5,    # Most critical for back safety
                'depth': 0.25,     # Range of motion
                'stability': 0.25  # Control and balance
            },
            'default': {
                'posture': 0.4,
                'depth': 0.3,
                'stability': 0.3
            }
        }
        
        # Confidence-based score adjustments
        self.confidence_thresholds = {
            'high': 0.8,     # Very confident in classification
            'medium': 0.6,   # Moderately confident
            'low': 0.4       # Low confidence - be conservative
        }
    
    def calculate_exercise_scores(
        self, 
        ml_results: MLModelResults,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> ExerciseScores:
        """
        Calculate comprehensive exercise scores from ML model results.
        
        Args:
            ml_results: Results from the XGBoost model
            additional_metrics: Optional additional data (angles, trajectory smoothness, etc.)
            
        Returns:
            ExerciseScores with all calculated scores
        """
        try:
            logger.info(f"Calculating scores for {ml_results.exercise_type} exercise")
            
            # Get exercise-specific weights
            weights = self.exercise_weights.get(
                ml_results.exercise_type.lower(), 
                self.exercise_weights['default']
            )
            
            # Calculate individual component scores
            posture_score = self._calculate_posture_score(
                ml_results.posture_fault, 
                ml_results.confidence,
                additional_metrics
            )
            
            stability_score = self._calculate_stability_score(
                ml_results.stability_fault,
                ml_results.confidence,
                additional_metrics
            )
            
            depth_score = self._calculate_depth_score(
                ml_results.depth_fault,
                ml_results.confidence, 
                additional_metrics
            )
            
            # Calculate weighted overall score
            overall_score = (
                posture_score * weights['posture'] +
                stability_score * weights['stability'] + 
                depth_score * weights['depth']
            )
            
            # Determine confidence level
            confidence_level = self._determine_confidence_level(ml_results.confidence)
            
            # Apply confidence-based adjustments
            overall_score = self._apply_confidence_adjustment(overall_score, confidence_level)
            
            scores = ExerciseScores(
                posture_score=round(posture_score, 1),
                stability_score=round(stability_score, 1),
                depth_score=round(depth_score, 1),
                overall_score=round(overall_score, 1),
                confidence_level=confidence_level
            )
            
            logger.info(f"Calculated scores: Overall={scores.overall_score}, "
                       f"Posture={scores.posture_score}, Stability={scores.stability_score}, "
                       f"Depth={scores.depth_score}, Confidence={confidence_level}")
            
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating exercise scores: {e}", exc_info=True)
            # Return safe default scores
            return ExerciseScores(
                posture_score=50.0,
                stability_score=50.0,
                depth_score=50.0,
                overall_score=50.0,
                confidence_level="low"
            )
    
    def _calculate_posture_score(
        self, 
        posture_fault: bool, 
        confidence: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate posture component score."""
        
        if not posture_fault:
            # Good posture detected
            base_score = 95.0
            # Could enhance with specific posture quality metrics
            if additional_metrics and 'torso_angle' in additional_metrics:
                torso_angle = additional_metrics['torso_angle']
                # Example: penalize excessive forward lean
                if abs(torso_angle) > 30:  # degrees
                    base_score -= min(10, abs(torso_angle) - 30)
        else:
            # Posture fault detected
            base_score = 35.0  # Significant penalty for posture issues
            # Could adjust based on severity if available
            
        # Apply confidence weighting
        return base_score * min(1.0, confidence + 0.2)  # Don't penalize too much for lower confidence
    
    def _calculate_stability_score(
        self,
        stability_fault: bool,
        confidence: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate stability component score."""
        
        if not stability_fault:
            base_score = 90.0
            # Could enhance with trajectory smoothness metrics
            if additional_metrics and 'trajectory_smoothness' in additional_metrics:
                smoothness = additional_metrics['trajectory_smoothness']
                base_score = min(100.0, base_score + (smoothness * 10))
        else:
            base_score = 40.0  # Moderate penalty for stability issues
            
        return base_score * min(1.0, confidence + 0.2)
    
    def _calculate_depth_score(
        self,
        depth_fault: bool,
        confidence: float,
        additional_metrics: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate depth/range of motion score."""
        
        if not depth_fault:
            base_score = 92.0
            # Could enhance with actual depth measurements
            if additional_metrics and 'knee_angle_min' in additional_metrics:
                knee_angle = additional_metrics['knee_angle_min']
                # Reward deeper squats (closer to 90 degrees)
                if knee_angle <= 90:
                    base_score = min(100.0, base_score + 8)
                elif knee_angle > 110:
                    base_score -= min(15, knee_angle - 110)
        else:
            base_score = 45.0  # Penalty for insufficient depth
            
        return base_score * min(1.0, confidence + 0.2)
    
    def _determine_confidence_level(self, confidence: float) -> str:
        """Determine confidence level from numerical confidence."""
        if confidence >= self.confidence_thresholds['high']:
            return 'high'
        elif confidence >= self.confidence_thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _apply_confidence_adjustment(self, score: float, confidence_level: str) -> float:
        """Apply conservative adjustments for low confidence predictions."""
        if confidence_level == 'low':
            # Be more conservative with low confidence
            return score * 0.9
        elif confidence_level == 'medium':
            return score * 0.95
        else:
            return score  # No adjustment for high confidence
    
    def get_score_interpretation(self, score: float) -> Dict[str, str]:
        """Get human-readable interpretation of score."""
        if score >= 90:
            return {
                'level': 'Excellent',
                'description': 'Outstanding form! Keep up the great work.',
                'color': '#4CAF50'  # Green
            }
        elif score >= 70:
            return {
                'level': 'Good', 
                'description': 'Solid form with minor areas for improvement.',
                'color': '#8BC34A'  # Light Green
            }
        elif score >= 50:
            return {
                'level': 'Fair',
                'description': 'Decent form but needs attention to avoid injury.',
                'color': '#FFC107'  # Amber
            }
        elif score >= 30:
            return {
                'level': 'Poor',
                'description': 'Significant form issues that could lead to injury.',
                'color': '#FF9800'  # Orange
            }
        else:
            return {
                'level': 'Critical',
                'description': 'Dangerous form! Please focus on proper technique.',
                'color': '#F44336'  # Red
            }