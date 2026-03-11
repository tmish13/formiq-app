"""Pydantic schemas for SquatSession."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SquatSessionCreate(BaseModel):
    form_check_id: Optional[UUID] = None
    date: datetime
    working_weight_lb: float
    overall_score: float
    torso_stability: float
    knee_symmetry: float
    bottom_control: float
    forward_lean: float
    primary_limiter: str
    notes: Optional[str] = None
    sets_json: List[dict] = []


class SquatSessionRead(SquatSessionCreate):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
