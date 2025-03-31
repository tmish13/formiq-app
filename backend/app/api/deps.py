"""Dependencies module."""
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.core.security import ALGORITHM
from app.db.session import async_session
from app.schemas.token import TokenPayload
from app.schemas.user import User
from app.services.user_service import UserService
from app.services.exercise_service import ExerciseService
from app.services.form_check_service import FormCheckService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Yields:
        Database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Get user service.

    Args:
        db: Database session

    Returns:
        User service instance
    """
    return UserService(db)

async def get_exercise_service(db: AsyncSession = Depends(get_db)) -> ExerciseService:
    """Get exercise service.

    Args:
        db: Database session

    Returns:
        Exercise service instance
    """
    return ExerciseService(db)

async def get_form_check_service(db: AsyncSession = Depends(get_db)) -> FormCheckService:
    """Get form check service.

    Args:
        db: Database session

    Returns:
        Form check service instance
    """
    return FormCheckService(db)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Get current user from token.

    Args:
        db: Database session
        token: JWT token
        user_service: User service instance

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user.

    Args:
        current_user: Current user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user 