from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.enums import FormCheckStatus

class FormCheckBase(BaseModel):
    """Base schema for form check."""
    user_id: int
    video_path: str
    status: FormCheckStatus = FormCheckStatus.PENDING
    confidence: Optional[float] = None
    feedback: Optional[str] = None
    keypoints: Optional[List[dict]] = None

class FormCheckCreate(FormCheckBase):
    """Schema for creating a form check."""
    pass

class FormCheckUpdate(BaseModel):
    """Schema for updating a form check."""
    status: Optional[FormCheckStatus] = None
    confidence: Optional[float] = None
    feedback: Optional[str] = None
    keypoints: Optional[List[dict]] = None

class FormCheckInDB(FormCheckBase):
    """Schema for form check in database."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FormCheckResponse(FormCheckInDB):
    """Schema for form check response."""
    pass 