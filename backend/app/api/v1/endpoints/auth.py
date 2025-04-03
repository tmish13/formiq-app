"""Authentication endpoints."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import User as UserSchema, UserCreate
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Register a new user.

    Args:
        db: Database session
        user_in: User create schema
        user_service: User service instance

    Returns:
        Created user

    Raises:
        HTTPException: If user with email already exists
    """
    user = await user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    return await user_service.create(user_in)


@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Login user.

    Args:
        db: Database session
        form_data: OAuth2 password request form
        user_service: User service instance

    Returns:
        Access token and token type

    Raises:
        HTTPException: If invalid credentials
    """
    user = await user_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserSchema)
async def read_users_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get current user.

    Args:
        current_user: Current user

    Returns:
        Current user
    """
    return current_user


@router.post("/test-token", response_model=UserSchema)
def test_token(current_user: User = Depends(deps.get_current_user)) -> Any:
    """Test access token.

    Args:
        current_user: Current user

    Returns:
        Current user
    """
    return current_user 