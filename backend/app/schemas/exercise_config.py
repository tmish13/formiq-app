"""
Exercise Configuration Schemas for API request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID
from datetime import datetime

# Nested schema components for exercise configuration

class JointAngleRule(BaseModel):
    """
    Schema for joint angle rules.
    """
    min_angle: float = Field(..., description="Minimum angle in degrees")
    max_angle: float = Field(..., description="Maximum angle in degrees")
    ideal_angle: float = Field(..., description="Ideal angle in degrees")
    tolerance: float = Field(default=15.0, description="Tolerance range for the angle")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "min_angle": 80.0,
                "max_angle": 170.0,
                "ideal_angle": 130.0,
                "tolerance": 15.0
            }
        }
    )

class TriggerCondition(BaseModel):
    """
    Schema for trigger conditions that define phase transitions.
    """
    joint: str = Field(..., description="Joint name")
    condition: str = Field(..., description="Condition type (e.g., angle, velocity)")
    value: float = Field(..., description="Threshold value")
    comparator: str = Field(..., description="Comparison operator (e.g., >, <, ==)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "joint": "leftKnee",
                "condition": "angle",
                "value": 90.0,
                "comparator": "<"
            }
        }
    )

class MovementPhase(BaseModel):
    """
    Schema for a movement phase.
    """
    description: str = Field(..., description="Description of the phase")
    triggers: Dict[str, List[TriggerCondition]] = Field(
        ..., 
        description="Conditions that trigger phase transitions"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Descent phase of a squat",
                "triggers": {
                    "next": [
                        {
                            "joint": "leftKnee",
                            "condition": "angle",
                            "value": 90.0,
                            "comparator": "<"
                        }
                    ],
                    "previous": [
                        {
                            "joint": "leftKnee",
                            "condition": "angle",
                            "value": 150.0,
                            "comparator": ">"
                        }
                    ]
                }
            }
        }
    )

class FeedbackTemplate(BaseModel):
    """
    Schema for feedback templates.
    """
    message: str = Field(..., description="Feedback message template")
    severity: str = Field(..., description="Severity level (low, medium, high)")
    type: str = Field(..., description="Feedback type (form, alignment, range, tempo, safety)")
    details: Optional[str] = Field(None, description="Detailed explanation")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Knees are going too far forward past your toes",
                "severity": "medium",
                "type": "form",
                "details": "Keep your knees aligned with your toes to reduce stress on the joints"
            }
        }
    )

class PhaseJointRules(BaseModel):
    """
    Schema for joint rules in a specific phase.
    """
    angles: Dict[str, JointAngleRule] = Field(..., description="Joint angle rules for this phase")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "angles": {
                    "leftKnee": {
                        "min_angle": 80.0,
                        "max_angle": 170.0,
                        "ideal_angle": 130.0,
                        "tolerance": 15.0
                    }
                }
            }
        }
    )

class JointAngleRules(BaseModel):
    """
    Schema for all joint angle rules.
    """
    phases: Dict[str, PhaseJointRules] = Field(..., description="Rules for each phase")
    joints: List[str] = Field(..., description="List of joints involved in the exercise")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "phases": {
                    "descent": {
                        "angles": {
                            "leftKnee": {
                                "min_angle": 80.0,
                                "max_angle": 170.0,
                                "ideal_angle": 130.0,
                                "tolerance": 15.0
                            }
                        }
                    }
                },
                "joints": ["leftKnee", "rightKnee", "leftHip", "rightHip"]
            }
        }
    )

class ClassificationMetadata(BaseModel):
    """
    Schema for exercise classification metadata.
    """
    keypoints: List[str] = Field(..., description="Key keypoints for classification")
    frame_count: int = Field(..., description="Typical number of frames in a repetition")
    features: Dict[str, Any] = Field(..., description="Features for ML classification")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "keypoints": ["leftKnee", "rightKnee", "leftHip", "rightHip"],
                "frame_count": 30,
                "features": {
                    "joint_angle_ranges": {
                        "leftKnee": [80, 170]
                    }
                }
            }
        }
    )

# --- New Rule Schemas ---
class RangeOfMotionRule(BaseModel):
    """
    Schema for Range of Motion (ROM) rules for a specific joint across a full rep.
    """
    joint_name: str = Field(..., description="Name of the joint to check ROM for")
    min_angle_overall: float = Field(..., description="Minimum angle expected for the joint throughout the repetition")
    max_angle_overall: float = Field(..., description="Maximum angle expected for the joint throughout the repetition")
    target_rom: Optional[float] = Field(None, description="Optional target ROM value in degrees (max_angle - min_angle)")
    tolerance_degrees: float = Field(default=10.0, description="Tolerance for ROM deviation in degrees")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "joint_name": "leftKnee",
                "min_angle_overall": 70.0,
                "max_angle_overall": 175.0,
                "target_rom": 105.0,
                "tolerance_degrees": 10.0
            }
        }
    )

class PostureAlignmentCondition(BaseModel):
    """
    Defines a specific condition for a posture rule, e.g., relative alignment of keypoints.
    """
    keypoints_involved: List[str] = Field(..., description="List of keypoints defining the posture element (e.g., ['ShoulderLeft', 'HipLeft', 'KneeLeft'] for body line)")
    # Example: check if ShoulderLeft, HipLeft, KneeLeft are collinear within a threshold
    # More complex conditions can be added, like relative angles between vectors formed by keypoints.
    # For initial implementation, focus on simpler checks like overall tilt or deviation from vertical/horizontal.
    expected_orientation: Optional[str] = Field(None, description="E.g., 'vertical', 'horizontal', or specific angle range for a line formed by keypoints")
    max_deviation_degrees: float = Field(default=10.0, description="Maximum allowed deviation in degrees from expected orientation or alignment")
    reference_plane: Optional[str] = Field("sagittal", description="Plane of reference if applicable (e.g., sagittal, frontal)")

class PostureRule(BaseModel):
    """
    Schema for posture rules.
    """
    rule_name: str = Field(..., description="Descriptive name for the posture rule (e.g., 'neutral_spine', 'head_up')")
    description: Optional[str] = Field(None, description="Detailed description of what this rule checks.")
    conditions: List[PostureAlignmentCondition] = Field(..., description="List of specific alignment conditions to check for this posture rule.")
    applicable_phases: Optional[List[str]] = Field(None, description="List of movement phases where this rule applies. If None, applies to all phases.")
    severity: str = Field(default="medium", description="Default severity if this posture rule is violated.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rule_name": "straight_back_during_squat_descent",
                "description": "Ensures the back remains relatively straight (neutral spine) during the descent phase of a squat.",
                "conditions": [
                    {
                        "keypoints_involved": ["Neck", "MidHip", "AverageShoulders"], # Assumes AverageShoulders is a derived point
                        "expected_orientation": "maintain_relative_angle", # This would require more specific parameters
                        "max_deviation_degrees": 15.0 
                    }
                ],
                "applicable_phases": ["descent"],
                "severity": "medium"
            }
        }
    )

class SymmetryRule(BaseModel):
    """
    Schema for symmetry rules between bilateral joints.
    """
    joint_pair: Tuple[str, str] = Field(..., description="Tuple of joint names to compare for symmetry (e.g., ('leftKnee', 'rightKnee'))")
    max_difference_degrees: float = Field(default=15.0, description="Maximum acceptable absolute difference in angles between the joint pair in degrees")
    applicable_phases: Optional[List[str]] = Field(None, description="List of movement phases where this rule applies. If None, applies to all phases.")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "joint_pair": ["leftKnee", "rightKnee"],
                "max_difference_degrees": 20.0,
                "applicable_phases": ["descent", "ascent"]
            }
        }
    )

# API schemas for exercise configurations

class ExerciseConfigBase(BaseModel):
    """
    Base schema for exercise configuration.
    """
    name: str = Field(..., description="Name of the configuration")
    version: int = Field(default=1, description="Version number")
    is_active: bool = Field(default=True, description="Whether this config is active")
    joint_angle_rules: JointAngleRules = Field(..., description="Joint angle rules")
    movement_phases: Dict[str, MovementPhase] = Field(..., description="Movement phases")
    feedback_templates: Dict[str, FeedbackTemplate] = Field(..., description="Feedback templates")
    classification_metadata: Optional[ClassificationMetadata] = Field(None, description="Metadata for classification")
    # Add new rule types
    rom_rules: Optional[List[RangeOfMotionRule]] = Field(None, description="Range of Motion rules for key joints")
    posture_rules: Optional[List[PostureRule]] = Field(None, description="Posture and alignment rules")
    symmetry_rules: Optional[List[SymmetryRule]] = Field(None, description="Symmetry rules for bilateral joints")

class ExerciseConfigCreate(ExerciseConfigBase):
    """
    Schema for creating a new exercise configuration.
    """
    exercise_id: UUID = Field(..., description="ID of the related exercise template")

class ExerciseConfigUpdate(BaseModel):
    """
    Schema for updating an exercise configuration.
    """
    name: Optional[str] = Field(None, description="Name of the configuration")
    version: Optional[int] = Field(None, description="Version number")
    is_active: Optional[bool] = Field(None, description="Whether this config is active")
    joint_angle_rules: Optional[JointAngleRules] = Field(None, description="Joint angle rules")
    movement_phases: Optional[Dict[str, MovementPhase]] = Field(None, description="Movement phases")
    feedback_templates: Optional[Dict[str, FeedbackTemplate]] = Field(None, description="Feedback templates")
    classification_metadata: Optional[ClassificationMetadata] = Field(None, description="Metadata for classification")
    # Add new rule types for update
    rom_rules: Optional[List[RangeOfMotionRule]] = Field(None, description="Range of Motion rules for key joints")
    posture_rules: Optional[List[PostureRule]] = Field(None, description="Posture and alignment rules")
    symmetry_rules: Optional[List[SymmetryRule]] = Field(None, description="Symmetry rules for bilateral joints")

class ExerciseConfigInDB(ExerciseConfigBase):
    """
    Schema for exercise configuration in the database.
    """
    id: UUID = Field(..., description="Unique ID")
    exercise_id: UUID = Field(..., description="ID of the related exercise template")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)

class ExerciseConfigWithExercise(ExerciseConfigInDB):
    """
    Schema that includes exercise details.
    """
    exercise_name: str = Field(..., description="Name of the related exercise")
    
    model_config = ConfigDict(from_attributes=True) 