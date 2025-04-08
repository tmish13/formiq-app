"""Token schemas."""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """Token payload schema."""
    sub: str = Field(..., description="Subject (usually user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: Optional[int] = Field(None, description="Issued at timestamp")
    jti: Optional[str] = Field(None, description="JWT ID (unique identifier)")
    type: Optional[str] = Field(None, description="Token type (access, refresh)")
    role: Optional[str] = Field(None, description="User role")


class Token(BaseModel):
    """Token schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until token expires")
    user: Optional[Dict[str, Any]] = Field(None, description="User data")


class RefreshToken(BaseModel):
    """Refresh token request schema."""
    refresh_token: str = Field(..., description="JWT refresh token")


class TokenBlacklist(BaseModel):
    """Token blacklist schema."""
    jti: str = Field(..., description="JWT ID")
    expires_at: int = Field(..., description="Timestamp when token expires")
    created_at: int = Field(..., description="Timestamp when token was added to blacklist")
    reason: Optional[str] = Field(None, description="Reason for blacklisting") 