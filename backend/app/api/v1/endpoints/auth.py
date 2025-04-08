"""Authentication endpoints."""
from datetime import timedelta
from typing import Any, Dict, Optional
import time

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.core.security import (
    create_access_token, 
    create_refresh_token,
    verify_password_reset_token,
    create_password_reset_token,
    track_login_attempt
)
from app.core.auth import auth_service
from app.core.exceptions import AuthenticationException
from app.models.user import User
from app.schemas.token import Token, TokenPayload, RefreshToken
from app.schemas.user import User as UserSchema, UserCreate, UserPasswordReset
from app.schemas.common import Message
from app.services.user_service import UserService
from app.api.v1.docs import add_error_responses

router = APIRouter()


@router.post(
    "/register", 
    response_model=UserSchema, 
    status_code=status.HTTP_201_CREATED,
    responses=add_error_responses(400, 422, 429, 500)
)
async def register(
    request: Request,
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """
    Register a new user.
    
    Creates a new user account with the provided details.
    The password must meet security requirements:
    - At least 8 characters long
    - Contains uppercase and lowercase letters
    - Contains numbers
    - Contains special characters
    
    Rate limited to 3 requests per 5 minutes from the same IP address.
    """
    # Check for existing user
    user = await user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create new user
    return await user_service.create(user_in)


@router.post(
    "/register-admin", 
    response_model=UserSchema, 
    status_code=status.HTTP_201_CREATED,
    responses=add_error_responses(400, 403, 422, 500)
)
async def register_admin(
    request: Request,
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    admin_code: str = Query(..., description="Special admin registration code"),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """
    Register a new admin user with special admin code.
    
    Creates a new admin user account with elevated privileges.
    Requires a special admin registration code that must be provided
    as a query parameter for additional security.
    
    This endpoint is restricted and should be used only for initial
    admin account setup.
    """
    if admin_code != settings.ADMIN_REGISTRATION_CODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin registration code",
        )
    
    user = await user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create user with admin privileges
    admin_user = await user_service.create(user_in, is_superuser=True)
    return admin_user


@router.post(
    "/login", 
    response_model=Token,
    responses=add_error_responses(401, 422, 429)
)
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """
    Authenticate a user and return an access token and refresh token.
    
    The access token has a shorter lifespan and should be used for API requests.
    The refresh token has a longer lifespan and can be used to obtain a new
    access token when it expires.
    
    This endpoint is rate limited to prevent brute force attacks:
    - 5 attempts per minute from the same IP address
    - After 5 failed attempts, the account is locked for 5 minutes
    
    Returns a token response containing:
    - access_token: JWT token for API authentication
    - refresh_token: JWT token for refreshing the access token
    - token_type: Bearer
    - expires_in: Seconds until the access token expires
    - user: Basic user information
    """
    # Authenticate user with rate limiting protection
    user, account_locked, success = await auth_service.authenticate_user(
        request=request,
        db=db,
        email=form_data.username,
        password=form_data.password
    )
    
    # Handle account lockout
    if account_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Account locked temporarily.",
            headers={"Retry-After": "300"}  # 5 minutes
        )
    
    # Handle authentication failure
    if not user or not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate tokens
    tokens = auth_service.generate_tokens(user.id, user.role)
    
    # Set refresh token as httpOnly cookie for enhanced security
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh"
    )
    
    # Return token response with user data
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],  # Also include in response for non-browser clients
        "token_type": tokens["token_type"],
        "expires_in": tokens["expires_in"],
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": getattr(user, "full_name", None),
            "is_active": user.is_active,
            "is_verified": getattr(user, "is_verified", False),
            "role": user.role
        }
    }


@router.post(
    "/refresh",
    response_model=Token,
    responses=add_error_responses(401)
)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    refresh_token: Optional[str] = None,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """
    Refresh an access token using a refresh token.
    
    Accepts a refresh token either in the request body or as a httpOnly cookie,
    validates it, and returns a new access token if valid.
    
    If the refresh token is invalid or expired, returns a 401 Unauthorized response.
    """
    # Get refresh token from cookie or request body
    token = refresh_token or refresh_token_cookie
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # Validate refresh token
        user = await user_service.get_user_from_refresh_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Generate new tokens
        tokens = auth_service.generate_tokens(user.id, user.role)
        
        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT != "development",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/api/v1/auth/refresh"
        )
        
        # Return new token response
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": getattr(user, "full_name", None),
                "is_active": user.is_active,
                "is_verified": getattr(user, "is_verified", False),
                "role": user.role
            }
        }
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout the current user and invalidate their session"
)
async def logout(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Logout the current user.
    """
    # Add token to blacklist
    await deps.add_token_to_blacklist(current_user.id)
    
    return {"message": "Successfully logged out"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=add_error_responses(204, 400, 404, 429)
)
async def reset_password(
    request: Request,
    email: str,
    db: Session = Depends(deps.get_db),
    user_service: UserService = Depends(deps.get_user_service),
):
    """
    Initiate a password reset for a user.
    
    Sends a password reset email to the provided email address if a user
    with that email exists in the system.
    
    This endpoint is rate limited to 3 requests per 5 minutes from the same
    IP address to prevent abuse.
    
    Always returns a 204 No Content response, regardless of whether a user
    with the provided email exists, to prevent email enumeration attacks.
    """
    # Look up user by email
    user = await user_service.get_by_email(email)
    if not user:
        # Return success even if user doesn't exist to prevent email enumeration
        # But add a small delay to prevent timing attacks
        time.sleep(0.5)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    # Generate password reset token
    token = create_password_reset_token(user.email)
    
    # Send password reset email
    await user_service.send_password_reset_email(user.email, token)
    
    # Return success with no content
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reset-password-confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=add_error_responses(204, 400, 404, 422)
)
async def reset_password_confirm(
    request: Request,
    *,
    db: Session = Depends(deps.get_db),
    reset_data: UserPasswordReset,
    user_service: UserService = Depends(deps.get_user_service),
):
    """
    Complete the password reset process.
    
    Validates the reset token and sets a new password for the user.
    
    The new password must meet security requirements:
    - At least 8 characters long
    - Contains uppercase and lowercase letters
    - Contains numbers
    - Contains special characters
    
    Returns a 204 No Content response upon successful password reset.
    """
    # Verify token and get user email
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Get user by email
    user = await user_service.get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update password
    await user_service.update_password(user.id, reset_data.new_password)
    
    # Return success
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me", 
    response_model=UserSchema,
    responses=add_error_responses(401)
)
async def read_users_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the profile of the currently authenticated user.
    
    Returns the user's profile information, including:
    - ID
    - Email
    - Full name
    - Active status
    - Verification status
    - Role
    
    Requires authentication via a valid access token.
    """
    return current_user


@router.post(
    "/test-token", 
    response_model=Dict[str, Any],
    responses=add_error_responses(200, 401)
)
def test_token(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Test if the provided access token is valid.
    
    This endpoint can be used to verify that an access token is valid
    and to retrieve basic information about the authenticated user.
    
    Returns a success response with token validity confirmation and
    the user ID if the token is valid.
    """
    return {
        "token_valid": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
    } 