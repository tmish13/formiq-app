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
from app.core.exceptions import (
    ValidationError,
    AuthenticationError,
    ServiceError,
    RateLimitException
)
from app.middleware.rate_limiter import EnhancedRateLimiter

router = APIRouter()

# Rate limit sensitive endpoints
SENSITIVE_ENDPOINTS = {
    "/api/v1/auth/login": {"limit": 5, "burst": 10, "window": 300},  # 5 attempts per 5 minutes
    "/api/v1/auth/register": {"limit": 3, "burst": 5, "window": 3600},  # 3 attempts per hour
    "/api/v1/auth/forgot-password": {"limit": 3, "burst": 5, "window": 3600},  # 3 attempts per hour
    "/api/v1/auth/reset-password": {"limit": 3, "burst": 5, "window": 3600},  # 3 attempts per hour
}

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
    except ValidationError as e:
        logger.warning(f"Validation error in user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Service error in user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
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
    except AuthenticationError as e:
        logger.warning(f"Authentication error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    except ServiceError as e:
        logger.error(f"Service error in login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
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
    except ValidationError as e:
        logger.warning(f"Validation error in email verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Service error in email verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification"
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
    except AuthenticationError as e:
        logger.warning(f"Authentication error in token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except ServiceError as e:
        logger.error(f"Service error in token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh"
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
        # Always return 204 to prevent email enumeration
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValidationError as e:
        logger.warning(f"Validation error in password reset request: {str(e)}")
        # Still return 204 to prevent email enumeration
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ServiceError as e:
        logger.error(f"Service error in password reset request: {str(e)}")
        # Still return 204 to prevent email enumeration
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
    except ValidationError as e:
        logger.warning(f"Validation error in password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ServiceError as e:
        logger.error(f"Service error in password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset"
        ) 