from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class BaseSchema(BaseModel):
    """Base schema with common fields and configuration."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

class TimestampedSchema(BaseSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None 