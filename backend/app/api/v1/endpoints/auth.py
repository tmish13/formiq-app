"""Authentication endpoints."""
from datetime import timedelta, datetime
from typing import Any, Dict, Optional
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response, Cookie, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.core.config import settings
from app.core.security import (
    verify_token_payload,
    verify_session_token_and_get_payload
)
from app.core.exceptions import AuthenticationException, ValidationException, RateLimitExceededException, EmailError, NotFoundException
from app.models.user import User
from app.schemas.token import Token, TokenPayload, RefreshToken
from app.schemas.user import User as UserSchema, UserCreate, UserPasswordReset, UserResponse, UserUpdate
from app.schemas.auth import (
    PasswordResetRequest, 
    EmailVerificationRequest, 
    EmailVerificationConfirm
)
from app.schemas.common import Message
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.api.v1.docs import add_error_responses
from app.services.session_service import SessionService
from app.core.monitoring import (
    track_failed_login,
    track_password_reset,
    track_email_verification,
    track_session_start,
    track_rate_limit_hit
)
from app.core.redis import Redis

# Initialize logger
logger = logging.getLogger(__name__)

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
    user_service: UserService = Depends(deps.get_user_service),
    auth_service: AuthService = Depends(deps.get_auth_service)
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
    existing_user = await user_service.get_by_email_async(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create new user
    user = await user_service.create_async(user_in)
    
    # Send verification email using AuthService
    try:
        await auth_service.send_verification_email(email=user.email)
    except EmailError as e:
        logger.error(f"Failed to send verification email during registration for {user.email}: {str(e)}")
    
    return user


@router.post(
    "/register-admin", 
    response_model=UserSchema, 
    status_code=status.HTTP_201_CREATED,
    responses=add_error_responses(400, 403, 422, 500)
)
async def register_admin(
    request: Request,
    *,
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
    
    user = await user_service.get_by_email_async(user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    
    # Create user with admin privileges
    admin_user = await user_service.create_async(user_in, is_superuser=True)
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
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(deps.get_auth_service),
    session_service: SessionService = Depends(deps.get_async_session_service)
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
    user_db_obj, account_locked, auth_success = await auth_service.authenticate_user(
        request=request,
        email=form_data.username,
        password=form_data.password
    )

    if account_locked:
        track_rate_limit_hit(request, form_data.username, "/login", "account_locked")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Account locked temporarily.",
        )

    if not auth_success or not user_db_obj:
        track_failed_login(request, form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_db_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )

    token_data = await auth_service.generate_tokens(user_id=str(user_db_obj.id), user_role=user_db_obj.role.value if user_db_obj.role else None)

    session_id = await session_service.create_session(
        user_id=str(user_db_obj.id),
        user_agent=request.headers.get("User-Agent", "unknown"),
        ip_address=request.client.host if request.client else "unknown",
    )
    track_session_start(request, str(user_db_obj.id))

    response.set_cookie(
        key="refresh_token",
        value=token_data["refresh_token"],
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT != "local",
        expires=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    user_schema = UserSchema.from_orm(user_db_obj)

    return {
        "access_token": token_data["access_token"],
        "refresh_token": token_data["refresh_token"],
        "token_type": token_data["token_type"],
        "expires_in": token_data["expires_in"],
        "session_id": session_id,
        "user": user_schema 
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
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {"$ref": "#/components/responses/UnauthorizedError"}
    }
)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token_body: Optional[RefreshToken] = Body(None),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    auth_service: AuthService = Depends(deps.get_auth_service),
    redis_client: Redis = Depends(deps.get_redis_client)
) -> Any:
    """
    Refresh an access token using a refresh token.
    
    The refresh token can be provided in the request body or as a cookie.
    """
    token_to_verify = None
    if refresh_token_body and refresh_token_body.refresh_token:
        token_to_verify = refresh_token_body.refresh_token
    elif refresh_token_cookie:
        token_to_verify = refresh_token_cookie
    
    if not token_to_verify:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not provided in body or cookie."
        )

    payload = verify_token_payload(token_to_verify, redis_client, expected_token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid refresh token"
        )

    try:
        new_tokens = await auth_service.refresh_access_token(refresh_token_str=token_to_verify)
        
        response.set_cookie(
            key="refresh_token",
            value=new_tokens["refresh_token"],
            httponly=True,
            samesite="lax",
            secure=settings.ENVIRONMENT != "local",
            expires=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )

        return {
            "access_token": new_tokens["access_token"],
            "token_type": new_tokens["token_type"],
            "expires_in": new_tokens["expires_in"],
        }

    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not refresh token")


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
    session_service: SessionService = Depends(deps.get_async_session_service)
) -> Any:
    """
    Logout the current user.
    
    Deactivates the current session and clears the refresh token cookie.
    The access token will still be valid until it expires, but it won't
    be refreshable.
    """
    try:
        session_data = verify_session_token_and_get_payload(token, deps.get_redis())
        if session_data:
            await session_service.deactivate_session(session_data["session_id"])
        
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh",
            secure=settings.ENVIRONMENT != "development",
            httponly=True
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
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
    session_service: SessionService = Depends(deps.get_async_session_service),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Logout from all devices.
    
    Deactivates all active sessions for the current user and clears
    the refresh token cookie on this device.
    """
    try:
        session_data = verify_session_token_and_get_payload(token, deps.get_redis())
        if session_data:
            await session_service.deactivate_all_sessions(session_data["user_id"])
        
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh",
            secure=settings.ENVIRONMENT != "development",
            httponly=True
        )
        
        return {"message": "Successfully logged out from all devices"}
        
    except Exception as e:
        return {"message": "Successfully logged out from all devices"}


@router.post(
    "/reset-password/request",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Password reset email sent if account exists",
            "content": {
                "application/json": {
                    "example": {"message": "If account exists, password reset instructions have been sent"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Too many password reset emails. Try again in X minutes."}
                }
            }
        }
    }
)
async def request_password_reset(
    reset_request: PasswordResetRequest = Body(..., example={"email": "user@example.com"}),
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """
    Request a password reset email.
    
    For security reasons, this endpoint:
    * Always returns 202 whether the email exists or not
    * Sends reset instructions only if the email is registered
    * Uses rate limiting to prevent abuse (3 requests per hour)
    """
    await auth_service.request_password_reset(reset_request.email)
    
    return {"message": "If account exists, password reset instructions have been sent"}


@router.post(
    "/reset-password/confirm",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Password reset successful",
            "content": {
                "application/json": {
                    "example": {"message": "Password reset successful"}
                }
            }
        },
        400: {
            "description": "Invalid token or password",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired reset token"}
                }
            }
        }
    }
)
async def confirm_password_reset(
    password_reset: UserPasswordReset,
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """
    Confirm a password reset with token and new password.
    
    Takes the token from the reset link and the new password,
    then resets the user's password if the token is valid.
    """
    await auth_service.confirm_password_reset(
        token=password_reset.token,
        new_password=password_reset.new_password
    )
    
    return {"message": "Password reset successful"}


@router.post(
    "/verify-email/request",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Verification email sent if account exists",
            "content": {
                "application/json": {
                    "example": {"message": "If account exists and requires verification, instructions have been sent"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Too many verification emails. Try again in X minutes."}
                }
            }
        }
    }
)
async def request_email_verification(
    verification_request: EmailVerificationRequest = Body(..., example={"email": "user@example.com"}),
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """
    Request an email verification link.
    
    For security reasons, this endpoint:
    * Always returns 202 whether the email exists or not
    * Sends verification instructions only if the email is registered and not verified
    * Uses rate limiting to prevent abuse (3 requests per hour)
    """
    await auth_service.request_email_verification(verification_request.email)
    
    return {"message": "If account exists and requires verification, instructions have been sent"}


@router.post(
    "/verify-email/confirm",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Email verification successful",
            "content": {
                "application/json": {
                    "example": {"message": "Email verified successfully"}
                }
            }
        },
        400: {
            "description": "Invalid token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired verification token"}
                }
            }
        }
    }
)
async def confirm_email_verification(
    email_confirm: EmailVerificationConfirm = Body(..., example={"token": "your_verification_token"}),
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """Verify email with token."""
    await auth_service.verify_email_with_token(email_confirm.token)
    track_email_verification(email_confirm.token, True)
    return Message(message="Email verified successfully")


@router.post(
    "/test-token", 
    response_model=Dict[str, Any],
    responses=add_error_responses(200, 401)
)
async def test_token(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """Test if the current token is valid and return user info."""
    return {
        "token_valid": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
    }


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
async def send_verification_email(
    current_user: User = Depends(deps.get_current_user),
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """
    Resend verification email for the currently authenticated user.
    """
    if current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )
    try:
        await auth_service.send_verification_email(email=current_user.email)
        return Message(message="Verification email sent")
    except EmailError as e:
        logger.error(f"Failed to resend verification email for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email."
        )
    except Exception as e:
        logger.error(f"Unexpected error resending verification email for {current_user.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not resend verification email.")


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
    auth_service: AuthService = Depends(deps.get_auth_service)
) -> Any:
    """
    Verify email using a token from a verification link (GET request).
    """
    try:
        await auth_service.verify_email(token=token)
        return Message(message="Email successfully verified")
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during GET email verification for token {token}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not verify email.")


# ======= Social Authentication Endpoints =======

@router.post(
    "/social/google",
    response_model=dict,
    status_code=200,
    responses={
        200: {"description": "Successfully authenticated with Google"},
        400: {"description": "Invalid Google token"},
        500: {"description": "Social authentication error"}
    }
)
async def google_auth(
    token: str = Body(..., description="Google ID token"),
    db: AsyncSession = Depends(deps.get_async_db)
):
    """
    Authenticate user with Google OAuth2.
    
    Verifies the Google ID token and either logs in existing user
    or creates a new user account.
    """
    try:
        from app.services.social_auth_service import SocialAuthService
        social_auth_service = SocialAuthService()
        
        result = await social_auth_service.handle_social_login(
            provider="google",
            token=token,
            db=db
        )
        
        return result
        
    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Google authentication error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Google authentication failed")


@router.post(
    "/social/apple", 
    response_model=dict,
    status_code=200,
    responses={
        200: {"description": "Successfully authenticated with Apple"},
        400: {"description": "Invalid Apple token"},
        500: {"description": "Social authentication error"}
    }
)
async def apple_auth(
    token: str = Body(..., description="Apple ID token"),
    db: AsyncSession = Depends(deps.get_async_db)
):
    """
    Authenticate user with Apple Sign In.
    
    Verifies the Apple ID token and either logs in existing user
    or creates a new user account.
    """
    try:
        from app.services.social_auth_service import SocialAuthService
        social_auth_service = SocialAuthService()
        
        result = await social_auth_service.handle_social_login(
            provider="apple",
            token=token,
            db=db
        )
        
        return result
        
    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Apple authentication error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Apple authentication failed")


@router.get(
    "/social/google/redirect",
    status_code=302,
    responses={
        302: {"description": "Redirect to Google OAuth"}
    }
)
async def google_oauth_redirect():
    """
    Redirect to Google OAuth2 authorization URL.
    
    This endpoint redirects users to Google's OAuth2 consent screen.
    """
    from urllib.parse import urlencode
    
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/google/callback",
        "state": "random_state_string"  # In production, use secure random state
    }
    
    redirect_url = f"{google_auth_url}?{urlencode(params)}"
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


@router.get(
    "/social/apple/redirect", 
    status_code=302,
    responses={
        302: {"description": "Redirect to Apple OAuth"}
    }
)
async def apple_oauth_redirect():
    """
    Redirect to Apple Sign In authorization URL.
    
    This endpoint redirects users to Apple's Sign In consent screen.
    """
    from urllib.parse import urlencode
    
    apple_auth_url = "https://appleid.apple.com/auth/authorize"
    params = {
        "client_id": settings.APPLE_CLIENT_ID,
        "response_type": "code",
        "scope": "name email",
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/apple/callback",
        "state": "random_state_string",  # In production, use secure random state
        "response_mode": "form_post"
    }
    
    redirect_url = f"{apple_auth_url}?{urlencode(params)}"
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


@router.post(
    "/complete-onboarding",
    response_model=UserResponse,
    status_code=200,
    responses={
        200: {
            "description": "Onboarding completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Onboarding completed successfully",
                        "user": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "email": "user@example.com",
                            "has_completed_onboarding": True,
                            "onboarding_completed_at": "2024-01-20T10:45:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
async def complete_onboarding(
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service),
    db: AsyncSession = Depends(deps.get_db)
) -> Any:
    """
    Mark the current user's onboarding as completed.
    
    Updates the user's onboarding status and timestamp.
    """
    try:
        # Update user's onboarding status
        updated_user = await user_service.complete_onboarding(db, current_user.id)
        
        return {
            "message": "Onboarding completed successfully",
            "user": updated_user
        }
        
    except Exception as e:
        logger.error(f"Error completing onboarding for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding. Please try again."
        ) 