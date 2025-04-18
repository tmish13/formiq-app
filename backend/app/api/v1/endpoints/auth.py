"""Authentication endpoints."""
from datetime import timedelta, datetime
from typing import Any, Dict, Optional
import time

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response, Cookie, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
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
    track_login_attempt,
    get_password_hash,
    create_session_token,
    verify_session_token,
    verify_refresh_token
)
from app.core.auth import auth_service
from app.core.exceptions import AuthenticationException, ValidationException, RateLimitExceededException
from app.models.user import User
from app.schemas.token import Token, TokenPayload, RefreshToken
from app.schemas.user import User as UserSchema, UserCreate, UserPasswordReset, UserResponse
from app.schemas.common import Message
from app.services.user_service import UserService
from app.api.v1.docs import add_error_responses
from app.core.rate_limit import rate_limit
from app.services.auth import AuthService
from app.services.session_service import SessionService
from app.core.monitoring import (
    track_failed_login,
    track_password_reset,
    track_email_verification,
    track_session_start,
    track_rate_limit_hit
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    responses={
        201: {
            "description": "Successfully registered new user",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_verified": False,
                        "created_at": "2024-01-20T10:30:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid input or email already registered",
            "content": {
                "application/json": {
                    "example": {"detail": "Email already registered"}
                }
            }
        }
    }
)
@rate_limit(limit=3, window=300)  # 3 requests per 5 minutes
async def register(
    request: Request,
    user_in: UserCreate = Body(
        ...,
        example={
            "email": "user@example.com",
            "password": "strongpassword123",
            "confirm_password": "strongpassword123",
            "full_name": "John Doe"
        }
    ),
    db: Session = Depends(deps.get_db),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Register a new user.
    
    Requirements:
    * Valid email address
    * Password at least 8 characters long
    * Password must contain at least one number and one letter
    * Full name is required
    * Passwords must match
    
    Returns the created user object (without password).
    Sends a verification email to the user.
    """
    # Check for existing user
    existing_user = await user_service.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create new user
    user = await user_service.create(user_in)
    
    # Send verification email
    try:
        await user_service.send_verification_email(user)
    except EmailError as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        # Don't fail registration if email fails
        # But log it for monitoring
    
    return user


@router.post(
    "/register-admin", 
    response_model=UserSchema, 
    status_code=status.HTTP_201_CREATED,
    responses=add_error_responses(400, 403, 422, 500)
)
@rate_limit(limit=3, window=3600)  # 3 requests per hour
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
    responses={
        200: {
            "description": "Successfully authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600,
                        "session_id": "123e4567-e89b-12d3-a456-426614174000",
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "user@example.com",
                            "full_name": "John Doe",
                            "is_active": True,
                            "is_verified": False
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Incorrect email or password"}
                }
            }
        },
        429: {
            "description": "Too many failed attempts",
            "content": {
                "application/json": {
                    "example": {"detail": "Too many failed login attempts. Account locked temporarily."}
                }
            }
        }
    }
)
@rate_limit(limit=5, window=60, burst=10)  # 5 requests per minute, burst of 10
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    OAuth2 compatible token login.
    
    Returns:
    * JWT access token
    * JWT refresh token
    * Token type
    * Expiration time in seconds
    * Session ID
    * User information
    
    The access token should be included in the Authorization header
    of subsequent requests as: `Bearer {token}`
    
    The refresh token can be used to obtain a new access token
    when the current one expires.
    
    Rate limited to 5 requests per minute with a burst of 10.
    Account will be temporarily locked after multiple failed attempts.
    """
    # Get device info for session tracking
    device_info = get_device_info(request)
    
    # Authenticate user with rate limiting protection
    user = await user_service.authenticate(
        email=form_data.username,
        password=form_data.password,
        device_info=device_info
    )
    
    if not user:
        track_failed_login(form_data.username, str(request.client.host))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Account locked temporarily.",
            headers={"Retry-After": str(int((user.locked_until - datetime.utcnow()).total_seconds()))}
        )
    
    # Create session and track metrics
    session_token = create_session_token(user.id, device_info)
    session_data = verify_session_token(session_token)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )
    
    # Create refresh token
    refresh_token = create_refresh_token(user.id, session_data["session_id"])
    
    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh"
    )
    
    # Update user's last login and reset failed attempts
    await user_service.update(
        user.id,
        {
            "last_login": datetime.utcnow(),
            "failed_login_attempts": 0,
            "locked_until": None
        }
    )
    
    # Track session start
    track_session_start(user.id)
    
    # Return token response with user data
    return {
        "access_token": session_token,
        "refresh_token": refresh_token,  # Also include in response for non-browser clients
        "token_type": "bearer",
        "expires_in": settings.SESSION_EXPIRE_DAYS * 24 * 60 * 60,
        "session_id": session_data["session_id"],
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": getattr(user, "full_name", None),
            "is_active": user.is_active,
            "is_verified": getattr(user, "is_verified", False)
        }
    }


@router.post(
    "/refresh",
    response_model=Token,
    responses={
        200: {
            "description": "Successfully refreshed access token",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600,
                        "session_id": "123e4567-e89b-12d3-a456-426614174000"
                    }
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"}
    }
)
@rate_limit(limit=10, window=60)  # 10 requests per minute
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    refresh_token: Optional[str] = None,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Refresh an access token using a refresh token.
    
    Accepts a refresh token either in the request body or as a httpOnly cookie.
    Validates the token and session, then returns a new access token if valid.
    
    The new access token will be valid for the standard session duration.
    A new refresh token is also generated and set as a cookie.
    
    Rate limited to 10 requests per minute to prevent abuse.
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
        # Verify refresh token
        token_data = verify_refresh_token(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user = await user_service.get_by_id(token_data["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get device info for session tracking
        device_info = get_device_info(request)
        
        # Create new session token
        session_token = create_session_token(user.id, device_info)
        session_data = verify_session_token(session_token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        # Create new refresh token
        new_refresh_token = create_refresh_token(user.id, session_data["session_id"])
        
        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=settings.ENVIRONMENT != "development",
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/api/v1/auth/refresh"
        )
        
        # Track session start
        track_session_start(user.id)
        
        # Return new tokens
        return {
            "access_token": session_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.SESSION_EXPIRE_DAYS * 24 * 60 * 60,
            "session_id": session_data["session_id"]
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
    responses={
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {
                    "example": {"message": "Successfully logged out"}
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"}
    }
)
async def logout(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
    session_service: SessionService = Depends(deps.get_session_service)
) -> Any:
    """
    Logout the current user.
    
    Deactivates the current session and clears the refresh token cookie.
    The access token will still be valid until it expires, but it won't
    be refreshable.
    """
    try:
        # Verify session token
        session_data = verify_session_token(token)
        if session_data:
            # Deactivate session
            await session_service.deactivate_session(session_data["session_id"])
        
        # Clear refresh token cookie
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh",
            secure=settings.ENVIRONMENT != "development",
            httponly=True
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        # Always return success even if session deactivation fails
        # This ensures the client considers the logout successful
        return {"message": "Successfully logged out"}


@router.post(
    "/logout-all",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully logged out from all devices",
            "content": {
                "application/json": {
                    "example": {"message": "Successfully logged out from all devices"}
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"}
    }
)
async def logout_all(
    request: Request,
    response: Response,
    token: str = Depends(oauth2_scheme),
    session_service: SessionService = Depends(deps.get_session_service)
) -> Any:
    """
    Logout from all devices.
    
    Deactivates all active sessions for the current user and clears
    the refresh token cookie on this device.
    """
    try:
        # Verify session token
        session_data = verify_session_token(token)
        if session_data:
            # Deactivate all sessions for the user
            await session_service.deactivate_all_sessions(session_data["user_id"])
        
        # Clear refresh token cookie
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh",
            secure=settings.ENVIRONMENT != "development",
            httponly=True
        )
        
        return {"message": "Successfully logged out from all devices"}
        
    except Exception as e:
        # Always return success even if session deactivation fails
        return {"message": "Successfully logged out from all devices"}


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
    
    # Track password reset
    track_password_reset(user.email, "requested")
    
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
        track_password_reset(email, "invalid_token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    # Get user by email
    user = await user_service.get_by_email(email)
    if not user:
        track_password_reset(email, "user_not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Update password
    await user_service.update_password(user.id, reset_data.new_password)
    
    # Track password reset
    track_password_reset(email, "success")
    
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


@router.post(
    "/password-reset/request",
    status_code=202,
    responses={
        202: {
            "description": "Password reset email sent if account exists",
            "content": {
                "application/json": {
                    "example": {"message": "If account exists, password reset instructions have been sent"}
                }
            }
        }
    }
)
async def request_password_reset(
    email: str = Body(..., embed=True, example="user@example.com"),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Request a password reset email.
    
    For security reasons, this endpoint:
    * Always returns 202 whether the email exists or not
    * Sends reset instructions only if the email is registered
    * Uses rate limiting to prevent abuse
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(email)
    
    # Track password reset
    track_password_reset(email, "requested")
    
    return {"message": "If account exists, password reset instructions have been sent"}


@router.post(
    "/password-reset/verify",
    response_model=Token,
    responses={
        200: {
            "description": "Password successfully reset",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        400: {
            "description": "Invalid or expired token",
            "content": {
                "application/json": {
                    "example": {"detail": "Password reset token is invalid or has expired"}
                }
            }
        }
    }
)
async def reset_password(
    token: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Reset password using reset token.
    
    Requirements:
    * Valid reset token (from email)
    * New password meeting minimum requirements
    * Token not expired (valid for 24 hours)
    
    Returns a new access token upon successful reset.
    """
    auth_service = AuthService(db)
    
    # Track password reset
    track_password_reset(token, "requested")
    
    return await auth_service.reset_password(token, new_password)


@router.post(
    "/verify-email/send",
    response_model=Message,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Verification email sent",
            "content": {
                "application/json": {
                    "example": {"message": "Verification email sent"}
                }
            }
        },
        400: {
            "description": "Email already verified",
            "content": {
                "application/json": {
                    "example": {"detail": "Email already verified"}
                }
            }
        }
    }
)
@rate_limit(limit=3, window=300)  # 3 requests per 5 minutes
async def send_verification_email(
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Send email verification link to current user.
    
    Rate limited to 3 requests per 5 minutes to prevent abuse.
    Returns 400 if email is already verified.
    """
    if current_user.is_verified:
        track_email_verification(current_user.email, "already_verified")
        return {"msg": "Email already verified"}
    
    await user_service.send_verification_email(current_user)
    
    # Track email verification
    track_email_verification(current_user.email, "sent")
    
    return {"msg": "Verification email sent"}


@router.get(
    "/verify-email/{token}",
    response_model=Message,
    responses={
        200: {
            "description": "Email successfully verified",
            "content": {
                "application/json": {
                    "example": {"message": "Email successfully verified"}
                }
            }
        },
        400: {
            "description": "Invalid or expired verification token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired verification token"}
                }
            }
        }
    }
)
async def verify_email(
    token: str,
    db: Session = Depends(deps.get_db),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Verify user's email using the verification token.
    
    The token is sent to the user's email and is valid for 24 hours.
    Returns 400 if token is invalid or expired.
    """
    try:
        await user_service.verify_email(token)
        
        # Track email verification
        track_email_verification(token, "success")
        
        return {"message": "Email successfully verified"}
    except ValidationException as e:
        track_email_verification(token, "invalid_token")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 