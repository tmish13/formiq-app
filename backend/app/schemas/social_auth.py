"""Social authentication schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr


class SocialAuthRequest(BaseModel):
    """Social authentication request."""
    provider: str  # 'google' or 'apple'
    token: str  # ID token from the provider
    redirect_uri: Optional[str] = None


class SocialAuthResponse(BaseModel):
    """Social authentication response."""
    access_token: str
    refresh_token: str
    user: dict
    token_type: str = "bearer"


class SocialUserInfo(BaseModel):
    """Social user information extracted from token."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str
    provider_id: str