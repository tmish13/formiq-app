"""Session schemas."""
from typing import Dict, Optional
from pydantic import BaseModel

class SessionCreate(BaseModel):
    """Schema for creating a new session."""
    user_id: int
    device_info: Optional[Dict[str, str]] = None

class SessionData(BaseModel):
    """Schema for session data stored in Redis."""
    user_id: int
    created_at: int
    device_info: Optional[Dict[str, str]] = None
    is_active: bool = True

class SessionResponse(BaseModel):
    """Schema for session response."""
    session_id: str
    token: str
    user_id: int
    created_at: int
    device_info: Optional[Dict[str, str]] = None
    is_active: bool = True 