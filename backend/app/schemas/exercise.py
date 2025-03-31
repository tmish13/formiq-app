"""Exercise schema module."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ExerciseBase(BaseModel):
    """Exercise base schema."""

    name: str
    description: Optional[str] = None
    video_url: Optional[str] = None
    difficulty: Optional[str] = None
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None


class ExerciseCreate(ExerciseBase):
    """Exercise create schema."""

    pass


class ExerciseUpdate(ExerciseBase):
    """Exercise update schema."""

    name: Optional[str] = None


class ExerciseInDBBase(ExerciseBase):
    """Exercise in DB base schema."""

    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class Exercise(ExerciseInDBBase):
    """Exercise schema."""

    pass


class ExerciseInDB(ExerciseInDBBase):
    """Exercise in DB schema."""

    pass 