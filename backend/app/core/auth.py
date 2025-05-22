from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Tuple
import secrets

from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    track_login_attempt, 
    create_access_token, 
    create_refresh_token,
    is_token_blacklisted,
    ALGORITHM
)
from app.core.config import settings
from app.core.constants import ROLE_PERMISSIONS, Roles
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Define API Key Security Scheme (for X-API-Key header)
api_key_header_auth = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header_auth)) -> str:
    """
    Dependency to validate an API key from the X-API-Key header.
    Compares against settings.TRAINING_API_KEY.
    """
    if not settings.TRAINING_API_KEY:
        logger.error("TRAINING_API_KEY is not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key authentication is not configured on the server."
        )
    if secrets.compare_digest(api_key, settings.TRAINING_API_KEY):
        return api_key # Or some principal representing the authenticated service
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key"
    )

logger = get_logger(__name__)

class AuthService:
    """Enhanced authentication service with security features."""
    
    @staticmethod
    async def authenticate_user(
        request: Request,
        db: Session, 
        email: str, 
        password: str
    ) -> Tuple[Optional[User], bool, bool]:
        """
        Authenticate a user with email and password with rate limiting protection.
        
        Args:
            request: Request object for IP tracking
            db: Database session
            email: User email
            password: User password
            
        Returns:
            Tuple containing:
            - User if authentication successful, None otherwise
            - Boolean indicating if account is locked
            - Boolean indicating authentication success/failure
        """
        # Get client IP for additional security logging
        client_ip = request.client.host if request.client else None
        
        # Check if account is locked due to too many failed attempts
        account_locked = track_login_attempt(email.lower(), success=False)
        if account_locked:
            logger.warning(
                "Account locked due to too many failed attempts",
                extra={
                    "email": email,
                    "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            return None, True, False
        
        # Try to find the user
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            logger.warning(
                "Login attempt with non-existent user", 
                extra={
                    "email": email,
                    "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            # We still track the attempt even if user doesn't exist
            # Use the same timing to prevent timing attacks
            return None, False, False
            
        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning(
                "Failed login attempt", 
                extra={
                    "user_id": user.id,
                    "email": email,
                    "ip": client_ip,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            return None, False, False
            
        # If we get here, authentication was successful
        # Reset failed attempts counter
        track_login_attempt(email.lower(), success=True)
        
        # Log successful login
        logger.info(
            "Successful login", 
            extra={
                "user_id": user.id,
                "email": email,
                "ip": client_ip,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
        
        # Update last login timestamp if the model has this field
        if hasattr(user, "last_login"):
            user.last_login = datetime.utcnow()
            db.commit()
            
        return user, False, True
    
    @staticmethod
    def get_current_user(
        db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
    ) -> User:
        """
        Get the current authenticated user.
        
        Args:
            db: Database session
            token: JWT token
            
        Returns:
            User
            
        Raises:
            AuthenticationException: If token is invalid or user not found
        """
        try:
            if is_token_blacklisted(token):
                raise AuthenticationException("Token is blacklisted or revoked")
                
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            
            # Ensure the token hasn't expired
            if datetime.fromtimestamp(token_data.exp) < datetime.now():
                raise AuthenticationException("Token has expired")
                
            # Validate token type (if present)
            if "type" in payload and payload["type"] != "access":
                raise AuthenticationException("Invalid token type")
                
        except (JWTError, ValidationError) as e:
            logger.warning(
                "Token validation error", 
                extra={"error": str(e)}
            )
            raise AuthenticationException("Could not validate credentials")
            
        user = db.query(User).filter(User.id == token_data.sub).first()
        if not user:
            raise AuthenticationException("User not found")
            
        # Check if user account status has changed since token was issued
        if not user.is_active:
            raise AuthenticationException("User account is disabled")
            
        return user
    
    @staticmethod
    def get_current_active_user(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Get the current active user.
        
        Args:
            current_user: Current user
            
        Returns:
            User
            
        Raises:
            AuthenticationException: If user is inactive
        """
        if not current_user.is_active:
            raise AuthenticationException("Inactive user account")
        return current_user
    
    @staticmethod
    def check_permission(
        current_user: User = Depends(get_current_active_user),
        required_permission: str = None,
    ) -> User:
        """
        Check if user has the required permission.
        
        Args:
            current_user: Current user
            required_permission: Required permission
            
        Returns:
            User
            
        Raises:
            AuthorizationException: If user does not have the required permission
        """
        if required_permission is None:
            return current_user
            
        role_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        
        # Admin has all permissions
        if current_user.role == Roles.ADMIN or required_permission in role_permissions:
            return current_user
            
        logger.warning(
            "Permission denied",
            extra={
                "user_id": current_user.id,
                "required_permission": required_permission,
                "user_role": current_user.role
            }
        )
        raise AuthorizationException("Not enough permissions")
    
    @staticmethod
    def generate_tokens(user_id: int, user_role: str = None) -> Dict[str, Any]:
        """
        Generate access and refresh tokens for user.
        
        Args:
            user_id: User ID
            user_role: User role for token claims
            
        Returns:
            Dict containing access and refresh tokens
        """
        # Additional claims for the token
        additional_data = {}
        if user_role:
            additional_data["role"] = user_role
        
        # Add unique token ID for potential revocation
        token_id = secrets.token_hex(16)
        additional_data["jti"] = token_id
        
        # Create access token with shorter expiration
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user_id, 
            expires_delta=access_token_expires,
            data=additional_data
        )
        
        # Create refresh token with longer expiration
        refresh_token = create_refresh_token(
            subject=user_id
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
        }

# Create a singleton instance
auth_service = AuthService()

# New dependency for admin checks
def get_current_admin_user(
    current_user: User = Depends(AuthService.get_current_active_user)
) -> User:
    """
    Dependency to get the current active user and verify if they are an admin.
    Raises HTTPException if the user is not an admin.
    """
    if current_user.role != Roles.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have administrative privileges.",
        )
    return current_user 