from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, is_token_blacklisted
from app.core.config import settings
from app.core.constants import ROLE_PERMISSIONS, Roles
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging import logger
from app.models.user import User
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

class AuthService:
    """Authentication service."""
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            db: Database session
            email: User email
            password: User password
            
        Returns:
            User if authentication successful, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
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
                raise AuthenticationException("Token is blacklisted")
                
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            
            if datetime.fromtimestamp(token_data.exp) < datetime.now():
                raise AuthenticationException("Token has expired")
        except (JWTError, ValidationError) as e:
            logger.error("token_decode_error", error=str(e))
            raise AuthenticationException("Could not validate credentials")
            
        user = db.query(User).filter(User.id == token_data.sub).first()
        if not user:
            raise AuthenticationException("User not found")
            
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
            raise AuthenticationException("Inactive user")
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
            "permission_denied",
            user_id=current_user.id,
            required_permission=required_permission,
            user_role=current_user.role
        )
        raise AuthorizationException("Not enough permissions")
    
    @staticmethod
    def generate_token(user_id: int) -> Dict[str, Any]:
        """
        Generate access token for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Token data
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        return {
            "access_token": AuthService.create_access_token(
                user_id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
        }
    
    @staticmethod
    def create_access_token(
        subject: Union[int, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token.
        
        Args:
            subject: Token subject (usually user ID)
            expires_delta: Token expiration delta
            
        Returns:
            Encoded JWT token
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        
        return encoded_jwt

auth_service = AuthService() 