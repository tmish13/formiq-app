"""Form check models for storing exercise analysis data."""
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from app.models.base import Base, SQLiteUUID
from app.models.enums import (
    FormCheckStatus,
    FeedbackType,
    FeedbackSeverity,
    ExerciseType
)
from app.models.base import BaseModel
from app.core.exceptions import ValidationError
import uuid

class FormCheck(BaseModel):
    """
    Model for storing form check analysis results.
    
    This model handles:
    - Exercise video metadata
    - Analysis results
    - Processing status
    - Performance metrics
    - Feedback items
    
    Relationships:
    - Many-to-one with User
    - Many-to-one with Video
    - One-to-many with FeedbackItem
    
    Attributes:
        user_id (UUID): ID of the user who submitted the form check
        exercise_type (ExerciseType): Type of exercise being analyzed
        video_url (str): URL to the uploaded video
        analysis_url (str): URL to the analyzed video with overlays
        score (float): Overall form score (0-100)
        overall_feedback (str): Summary feedback
        issues (str): JSON string of identified issues
        status (FormCheckStatus): Current processing status
        processing_time (float): Time taken to process in seconds
        confidence_score (float): AI model confidence (0-1)
        form_metadata (dict): Additional metadata
        results (dict): Detailed analysis results
        configuration_id (UUID): ID of the exercise configuration used for analysis
        reps_per_minute (float): Reps per minute
        reps_detected (int): Detected reps
    """
    __tablename__ = "form_checks"

    id = Column(SQLiteUUID(), primary_key=True, index=True)
    video_url = Column(String, nullable=False)
    exercise_id = Column(SQLiteUUID(), ForeignKey("exercise_templates.id"), nullable=False)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id"), nullable=False)
    video_id = Column(SQLiteUUID(), ForeignKey("videos.id"), nullable=True)
    feedback = Column(String)
    score = Column(Float)
    keypoints = Column(JSON)
    status = Column(Enum(FormCheckStatus), default=FormCheckStatus.PENDING, nullable=False)
    analysis_url = Column(String(1024), nullable=True)
    overall_feedback = Column(String(2048), nullable=True)
    issues = Column(JSON, nullable=True)
    processing_time = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    form_metadata = Column(JSON, nullable=True)
    results = Column(JSON, nullable=True)
    configuration_id = Column(SQLiteUUID(), ForeignKey("exercise_configs.id", ondelete="SET NULL"), nullable=True, index=True)
    reps_per_minute = Column(Float, nullable=True)
    reps_detected = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    exercise = relationship(
        "ExerciseTemplate",
        back_populates="form_checks",
        lazy="select"
    )
    user = relationship(
        "User",
        back_populates="form_checks",
        lazy="select"
    )
    video = relationship(
        "Video",
        back_populates="form_checks",
        lazy="select",
        foreign_keys=[video_id]
    )
    feedback_items = relationship(
        "FeedbackItem",
        back_populates="form_check",
        cascade="all, delete-orphan",
        lazy="select"
    )
    configuration = relationship(
        "ExerciseConfig",
        lazy="select"
    )

    @validates('video_url', 'analysis_url')
    def validate_url(self, key: str, url: str) -> str:
        """
        Validate URL format.
        
        Args:
            key (str): Field name
            url (str): URL to validate
            
        Returns:
            str: Validated URL
            
        Raises:
            ValidationError: If URL format is invalid
        """
        if not url:
            if key == 'video_url':
                raise ValidationError("Video URL is required")
            return url

        if len(url) > 1024:
            raise ValidationError(f"{key} URL is too long")

        # Basic URL validation
        if not url.startswith(('http://', 'https://', 's3://')):
            raise ValidationError(f"Invalid {key} URL format")

        return url

    @validates('score', 'confidence_score')
    def validate_score(self, key: str, score: Optional[float]) -> Optional[float]:
        """
        Validate score values.
        
        Args:
            key (str): Field name
            score (Optional[float]): Score to validate
            
        Returns:
            Optional[float]: Validated score
            
        Raises:
            ValidationError: If score is invalid
        """
        if score is None:
            return score

        if key == 'score' and not (0 <= score <= 100):
            raise ValidationError("Score must be between 0 and 100")
        elif key == 'confidence_score' and not (0 <= score <= 1):
            raise ValidationError("Confidence score must be between 0 and 1")

        return score

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        Raises:
            ValidationError: If any validation fails
        """
        super().validate()
        self.validate_url('video_url', self.video_url)
        if self.analysis_url:
            self.validate_url('analysis_url', self.analysis_url)
        if self.score is not None:
            self.validate_score('score', self.score)
        if self.confidence_score is not None:
            self.validate_score('confidence_score', self.confidence_score)

    def __repr__(self) -> str:
        return f"<FormCheck {self.id} - {self.exercise_id}>"

class FeedbackItem(BaseModel):
    """
    Model for storing individual feedback items for a form check.
    
    This model handles:
    - Specific form feedback
    - Timestamp information
    - Joint angle data
    - Improvement suggestions
    
    Relationships:
    - Many-to-one with FormCheck
    
    Attributes:
        form_check_id (UUID): ID of the parent form check
        type (FeedbackType): Type of feedback
        message (str): Feedback message
        timestamp (float): Video timestamp in seconds
        severity (FeedbackSeverity): Feedback severity level
        joint_angles (dict): Joint angle measurements
        suggestions (List[str]): Improvement suggestions
    """
    __tablename__ = "feedback_items"

    id = Column(Integer, primary_key=True, index=True)
    form_check_id = Column(
        SQLiteUUID(),
        ForeignKey("form_checks.id", ondelete="CASCADE"),
        nullable=False
    )
    type = Column(Enum(FeedbackType), nullable=False)
    message = Column(String(1024), nullable=False)
    timestamp = Column(Float, nullable=False)
    severity = Column(Enum(FeedbackSeverity), nullable=False)
    joint_angles = Column(JSON, nullable=True)
    suggestions = Column(JSON, nullable=True)

    form_check = relationship(
        "FormCheck",
        back_populates="feedback_items",
        lazy="select"
    )

    @validates('message')
    def validate_message(self, key: str, message: str) -> str:
        """
        Validate feedback message.
        
        Args:
            key (str): Field name
            message (str): Message to validate
            
        Returns:
            str: Validated message
            
        Raises:
            ValidationError: If message is invalid
        """
        if not message:
            raise ValidationError("Feedback message is required")
        
        if len(message) > 1024:
            raise ValidationError("Feedback message is too long")
        
        return message

    @validates('timestamp')
    def validate_timestamp(self, key: str, timestamp: float) -> float:
        """
        Validate video timestamp.
        
        Args:
            key (str): Field name
            timestamp (float): Timestamp to validate
            
        Returns:
            float: Validated timestamp
            
        Raises:
            ValidationError: If timestamp is invalid
        """
        if timestamp < 0:
            raise ValidationError("Timestamp cannot be negative")
        
        return timestamp

    def validate(self) -> None:
        """
        Validate all fields in the model.
        
        Raises:
            ValidationError: If any validation fails
        """
        super().validate()
        self.validate_message('message', self.message)
        self.validate_timestamp('timestamp', self.timestamp)
        
        if self.suggestions and not isinstance(self.suggestions, list):
            raise ValidationError("Suggestions must be a list")
        
        if self.joint_angles and not isinstance(self.joint_angles, dict):
            raise ValidationError("Joint angles must be a dictionary")

    def __repr__(self) -> str:
        return f"<FeedbackItem {self.id} - {self.type}>" 