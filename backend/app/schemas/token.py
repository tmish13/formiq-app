"""Token schema module."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class Token(BaseModel):
    """Token schema."""
    access_token: str
    refresh_token: str
    token_type: str

class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[UUID] = None
    exp: Optional[int] = None 