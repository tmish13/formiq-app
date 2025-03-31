"""Users router module."""
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Get current user.

    Args:
        current_user: Current user

    Returns:
        Current user
    """
    return current_user


@router.get("/", response_model=List[UserSchema])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Get users.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current user
        user_service: User service instance

    Returns:
        List of users
    """
    return user_service.get_all()


@router.post("/", response_model=UserSchema)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Create user.

    Args:
        db: Database session
        user_in: User create schema
        current_user: Current user
        user_service: User service instance

    Returns:
        Created user

    Raises:
        HTTPException: If user with the same email already exists
    """
    user = user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    return user_service.create(user_in)


@router.put("/me", response_model=UserSchema)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Update current user.

    Args:
        db: Database session
        user_in: User update schema
        current_user: Current user
        user_service: User service instance

    Returns:
        Updated user
    """
    return user_service.update(current_user, user_in)


@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Get user by ID.

    Args:
        user_id: User ID
        current_user: Current user
        user_service: User service instance

    Returns:
        User

    Raises:
        HTTPException: If user not found
    """
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
def update_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Update user.

    Args:
        db: Database session
        user_id: User ID
        user_in: User update schema
        current_user: Current user
        user_service: User service instance

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found
    """
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user_service.update(user, user_in)


@router.delete("/{user_id}", response_model=UserSchema)
def delete_user(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Delete user.

    Args:
        db: Database session
        user_id: User ID
        current_user: Current user
        user_service: User service instance

    Returns:
        Deleted user

    Raises:
        HTTPException: If user not found
    """
    user = user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user_service.delete(user) 