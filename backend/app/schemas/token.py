from typing import Optional
from pydantic import BaseModel

class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: Optional[int] = None 