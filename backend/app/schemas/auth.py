from pydantic import BaseModel, EmailStr
from app.schemas.base import BaseSchema

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: int | None = None 