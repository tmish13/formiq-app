from typing import Dict, Any, Optional
from app.schemas.base import BaseSchema

class FormCheckBase(BaseSchema):
    """Base form check schema with common fields."""
    exercise_type: str
    video_url: str
    analysis_url: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class FormCheckCreate(FormCheckBase):
    """Schema for creating a new form check."""
    user_id: int

class FormCheckResponse(FormCheckBase):
    """Schema for form check response."""
    user_id: int 