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
        created_at (DateTime): Creation timestamp
        updated_at (DateTime): Last update timestamp
    """
    __tablename__ = "exercise_configs"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    exercise_id = Column(SQLiteUUID(), ForeignKey("exercise_templates.id"), nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    joint_angle_rules = Column(JSON, nullable=False)
    movement_phases = Column(JSON, nullable=False)
    feedback_templates = Column(JSON, nullable=False)
    classification_metadata = Column(JSON, nullable=True)
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
        if value is None:
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