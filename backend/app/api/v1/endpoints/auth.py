"""Authentication endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    TokenResponse,
    PasswordResetRequest,
    PasswordReset,
    TokenRefresh
)
from app.services.user_service import UserService
from app.core.logging import logger

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(
    *,
    db: Session = Depends(get_db),
    user_data: UserCreate
) -> TokenResponse:
    """Register a new user."""
    try:
        user_service = UserService()
        user = await user_service.register(db, data=user_data.dict())
        
        # Generate tokens
        tokens = await user_service.authenticate(
            db,
            email=user_data.email,
            password=user_data.password
        )
        
        return tokens
    except Exception as e:
        logger.error("Error in user registration", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    *,
    db: Session = Depends(get_db),
    user_data: UserLogin
) -> TokenResponse:
    """Login user and return access token."""
    try:
        user_service = UserService()
        return await user_service.authenticate(
            db,
            email=user_data.email,
            password=user_data.password
        )
    except Exception as e:
        logger.error("Error in user login", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.post("/verify-email/{token}")
async def verify_email(
    *,
    db: Session = Depends(get_db),
    token: str
) -> Response:
    """Verify user's email."""
    try:
        user_service = UserService()
        await user_service.verify_email(db, token=token)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error("Error in email verification", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    *,
    db: Session = Depends(get_db),
    refresh_data: TokenRefresh
) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        user_service = UserService()
        return await user_service.refresh_token(
            db,
            refresh_token=refresh_data.refresh_token
        )
    except Exception as e:
        logger.error("Error in token refresh", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/forgot-password")
async def forgot_password(
    *,
    db: Session = Depends(get_db),
    request_data: PasswordResetRequest
) -> Response:
    """Request password reset."""
    try:
        user_service = UserService()
        await user_service.request_password_reset(
            db,
            email=request_data.email
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error("Error in password reset request", exc_info=e)
        # Don't reveal if email exists
        return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/reset-password/{token}")
async def reset_password(
    *,
    db: Session = Depends(get_db),
    token: str,
    reset_data: PasswordReset
) -> Response:
    """Reset password using token."""
    try:
        user_service = UserService()
        await user_service.reset_password(
            db,
            token=token,
            new_password=reset_data.new_password
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error("Error in password reset", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 