"""Exercise configuration model for storing dynamic exercise rules and feedback criteria."""
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Enum, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.models.base import Base, SQLiteUUID
from app.models.enums import ExerciseType
from app.models.base import BaseModel
from app.core.exceptions import ValidationError
import uuid

class ExerciseConfig(BaseModel):
    """
    Model for storing dynamic exercise configuration data.
    
    This model handles:
    - Joint angle rules for different phases of an exercise
    - Movement phase definitions
    - Feedback templates for various rule violations
    - Metadata for exercise classification
    
    Relationships:
    - Many-to-one with ExerciseTemplate
    
    Attributes:
        name (str): Name of the configuration
        exercise_id (UUID): ID of the related exercise template
        version (int): Version number of the configuration
        is_active (bool): Whether this config is active
        joint_angle_rules (JSON): Rules for joint angles in different phases
        movement_phases (JSON): Definition of movement phases
        feedback_templates (JSON): Templates for feedback based on rule violations
        classification_metadata (JSON): Data for ML classification
        rom_rules (JSON): List of RangeOfMotionRule
        posture_rules (JSON): List of PostureRule
        symmetry_rules (JSON): List of SymmetryRule
        reference_pose_data (JSON): Data for visual overlays
        created_at (DateTime): Creation timestamp
        updated_at (DateTime): Last update timestamp
    """
    __tablename__ = "exercise_configs"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    exercise_id = Column(SQLiteUUID(), ForeignKey("exercise_templates.id"), nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    joint_angle_rules = Column(JSON, nullable=False)
    movement_phases = Column(JSON, nullable=False)
    feedback_templates = Column(JSON, nullable=False)
    classification_metadata = Column(JSON, nullable=True)
    rom_rules = Column(JSON, nullable=True)
    posture_rules = Column(JSON, nullable=True)
    symmetry_rules = Column(JSON, nullable=True)
    reference_pose_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    exercise = relationship(
        "ExerciseTemplate",
        back_populates="exercise_configs",
        lazy="select"
    )

    @validates('name')
    def validate_name(self, key: str, name: str) -> str:
        """
        Validate the configuration name.
        
        Args:
            key (str): Field name
            name (str): Config name
            
        Returns:
            str: Validated name
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError("Configuration name is required")
        if len(name) > 255:
            raise ValidationError("Configuration name is too long")
        return name

    @validates('joint_angle_rules', 'movement_phases', 'feedback_templates')
    def validate_json_field(self, key: str, value: Dict) -> Dict:
        """
        Validate JSON fields.
        
        Args:
            key (str): Field name
            value (Dict): JSON value
            
        Returns:
            Dict: Validated JSON
            
        Raises:
            ValidationError: If JSON is invalid
        """
        if key in ['rom_rules', 'posture_rules', 'symmetry_rules', 'classification_metadata', 'reference_pose_data'] and value is None:
            return value

        if value is None and key not in ['classification_metadata', 'rom_rules', 'posture_rules', 'symmetry_rules', 'reference_pose_data']:
            raise ValidationError(f"{key} is required")
        
        # Schema validation would happen here based on the field
        # This would be expanded based on the specific schema for each field
        
        return value

    def __repr__(self) -> str:
        return f"<ExerciseConfig {self.id} - {self.name} v{self.version}>"

# Add schema validation methods for specific fields
class ExerciseConfigSchema:
    """Schema validation methods for ExerciseConfig fields."""
    
    @staticmethod
    def validate_joint_angle_rules(rules: Dict) -> bool:
        """
        Validate joint angle rules schema.
        
        Args:
            rules (Dict): Joint angle rules
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If schema is invalid
        """
        required_keys = {'phases', 'joints'}
        if not all(key in rules for key in required_keys):
            raise ValidationError(f"Joint angle rules must contain: {required_keys}")
        
        # Validate phases
        if not isinstance(rules['phases'], dict):
            raise ValidationError("Phases must be a dictionary")
        
        for phase_name, phase_data in rules['phases'].items():
            if not isinstance(phase_data, dict) or 'angles' not in phase_data:
                raise ValidationError(f"Phase {phase_name} must contain 'angles' field")
        
        # Validate joints
        if not isinstance(rules['joints'], list):
            raise ValidationError("Joints must be a list")
        
        return True
    
    @staticmethod
    def validate_movement_phases(phases: Dict) -> bool:
        """
        Validate movement phases schema.
        
        Args:
            phases (Dict): Movement phases
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If schema is invalid
        """
        if not isinstance(phases, dict):
            raise ValidationError("Movement phases must be a dictionary")
        
        for phase_name, phase_data in phases.items():
            required_phase_keys = {'description', 'triggers'}
            if not all(key in phase_data for key in required_phase_keys):
                raise ValidationError(f"Phase {phase_name} must contain: {required_phase_keys}")
            
            if not isinstance(phase_data['triggers'], dict):
                raise ValidationError(f"Triggers for phase {phase_name} must be a dictionary")
        
        return True
    
    @staticmethod
    def validate_feedback_templates(templates: Dict) -> bool:
        """
        Validate feedback templates schema.
        
        Args:
            templates (Dict): Feedback templates
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If schema is invalid
        """
        if not isinstance(templates, dict):
            raise ValidationError("Feedback templates must be a dictionary")
        
        for template_key, template_data in templates.items():
            required_template_keys = {'message', 'severity', 'type'}
            if not all(key in template_data for key in required_template_keys):
                raise ValidationError(f"Template {template_key} must contain: {required_template_keys}")
            
            if template_data['severity'] not in ['low', 'medium', 'high']:
                raise ValidationError(f"Invalid severity for template {template_key}")
            
            if template_data['type'] not in ['form', 'alignment', 'range', 'tempo', 'safety']:
                raise ValidationError(f"Invalid type for template {template_key}")
        
        return True

# Pydantic models for structured JSON fields within ExerciseConfig
# These help with validation and type hinting in services using these configs.

from pydantic import BaseModel as PydanticBaseModel, validator, Field

class Condition(PydanticBaseModel):
    joint: str
    condition: str # e.g., "angle", "velocity"
    value: float
    comparator: str # e.g., "<", ">=", "=="
    # Optional: add more specific validation, e.g., comparator must be one of ["<", "<=", ...]

class MovementPhaseTrigger(PydanticBaseModel):
    target_phase: str
    conditions: List[Condition]
    # Optional: Add a field like 'trigger_type' if needed e.g. 'next_phase', 'end_rep' etc.
    # For now, the key in the parent dict (e.g., "next", "next_rep_starts_phase") defines this.

class MovementPhaseDefinition(PydanticBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    triggers: Dict[str, MovementPhaseTrigger]

class JointSpecificAngleRule(PydanticBaseModel):
    min_angle: Optional[float] = None
    max_angle: Optional[float] = None
    ideal_angle: Optional[float] = None
    tolerance: Optional[float] = None
    # Could add feedback_ref: Optional[str] = None to link to a specific feedback template

class PhaseAngleRules(PydanticBaseModel):
    angles: Dict[str, JointSpecificAngleRule]

class JointAngleRulesStructure(PydanticBaseModel):
    phases: Dict[str, PhaseAngleRules] # Phase name (e.g., "start", "descent") or "default"
    joints: List[str] # List of relevant joint names for these rules

class ROMRule(PydanticBaseModel):
    joint_name: str
    min_angle_overall: Optional[float] = None
    max_angle_overall: Optional[float] = None
    target_rom: Optional[float] = None
    tolerance_degrees: Optional[float] = Field(default=5.0) # Default tolerance if not specified
    applicable_phases: Optional[List[str]] = None
    severity: Optional[str] = None # e.g., low, medium, high - for overriding calculated

class PostureCondition(PydanticBaseModel):
    condition_type: str # e.g., "vector_angle_from_vertical", "point_distance"
    # For vector_angle_from_vertical:
    keypoints_for_vector: Optional[List[str]] = None
    expected_angle_degrees: Optional[float] = None
    max_deviation_degrees: Optional[float] = None
    # Add other fields for other condition_types as needed

class PostureRule(PydanticBaseModel):
    rule_name: str
    applicable_phases: Optional[List[str]] = None
    conditions: List[PostureCondition]
    severity: Optional[str] = None # Overall severity for this rule if all conditions met
    # feedback_ref: Optional[str] = None

class SymmetryRule(PydanticBaseModel):
    joint_pair: List[str] # Expects two joint names, e.g., ["LEFT_KNEE", "RIGHT_KNEE"]
    max_difference_degrees: float
    applicable_phases: Optional[List[str]] = None
    severity: Optional[str] = None
    # feedback_ref: Optional[str] = None

    @validator('joint_pair')
    def check_joint_pair_length(cls, v):
        if len(v) != 2:
            raise ValueError('joint_pair must contain exactly two joint names')
        return v

class FeedbackTemplateDefinition(PydanticBaseModel):
    message: str
    severity: str # 'low', 'medium', 'high'
    type: str # 'form', 'alignment', 'range', 'tempo', 'safety'

class ClassificationFeatures(PydanticBaseModel):
    # Define structure based on expected features, e.g.:
    joint_angle_ranges: Optional[Dict[str, List[float]]] = None # { "leftKnee": [min, max], ... }
    # Add other features like velocity profiles, keypoint positions, etc.

class ClassificationMetadataStructure(PydanticBaseModel):
    keypoints: List[str]
    frame_count: Optional[int] = None # Approximate typical frame count for the exercise/rep
    features: Optional[ClassificationFeatures] = None
    # model_version: Optional[str] = None # If using versioned classification models

# It might be beneficial to have a Pydantic version of ExerciseConfig for validation
# before DB insertion or when returning from service layer, but that's a larger refactor.
# For now, these smaller models help with the JSON fields. 