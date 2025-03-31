"""Form check schema module."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class FormCheckBase(BaseModel):
    """Form check base schema."""

    video_url: str
    exercise_id: UUID
    feedback: Optional[str] = None
    score: Optional[float] = None
    keypoints: Optional[List[Dict[str, float]]] = None
    status: str = "pending"


class FormCheckCreate(FormCheckBase):
    """Form check create schema."""

    pass


class FormCheckUpdate(FormCheckBase):
    """Form check update schema."""

    video_url: Optional[str] = None
    exercise_id: Optional[UUID] = None
    status: Optional[str] = None


class FormCheckInDBBase(FormCheckBase):
    """Form check in DB base schema."""

    id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class FormCheck(FormCheckInDBBase):
    """Form check schema."""

    pass


class FormCheckInDB(FormCheckInDBBase):
    """Form check in DB schema."""

    pass 