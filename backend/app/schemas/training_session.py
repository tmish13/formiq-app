"""Pydantic schemas for TrainingSession."""
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TrainingSessionCreate(BaseModel):
    id: str                   # client-generated UUID from makeId()
    started_at: datetime
    goal: str
    sets_json: List[dict] = []


class TrainingSessionRead(TrainingSessionCreate):
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
