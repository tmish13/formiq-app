"""Users router module."""
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.schemas.common import Message
from app.services.user_service import UserService
from app.utils.rate_limit import rate_limit

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
async def read_users(
    db: AsyncSession = Depends(deps.get_async_db),
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
    return await user_service.get_all_async()


@router.post("/", response_model=UserSchema)
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
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
    user = await user_service.get_by_email_async(user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    return await user_service.create_async(user_in)


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
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
    return await user_service.update_async(current_user, user_in)


@router.get("/{user_id}", response_model=UserSchema)
async def read_user_by_id(
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
    user = await user_service.get_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
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
    user = await user_service.get_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return await user_service.update_async(user, user_in)


@router.delete("/{user_id}", response_model=UserSchema)
async def delete_user(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
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
    user = await user_service.get_by_id_async(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    return await user_service.delete_async(user)


@router.put("/me/password", response_model=Message)
@rate_limit(limit=5, window=300)  # 5 requests per 5 minutes
async def change_password(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    password_data: dict = Body(..., example={
        "current_password": "oldpass123",
        "new_password": "newpass123",
        "confirm_password": "newpass123"
    })
) -> Any:
    """
    Change the current user's password.
    
    Requires current password verification.
    New password must meet security requirements.
    Rate limited to 5 requests per 5 minutes.
    """
    user_service: UserService = deps.get_user_service()
    
    # Verify current password
    if not user_service.verify_password(password_data["current_password"], current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Verify new password matches confirmation
    if password_data["new_password"] != password_data["confirm_password"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    # Update password
    await user_service.change_password(current_user.id, password_data["new_password"])
    
    return {"message": "Password updated successfully"}

@router.put("/me/profile", response_model=UserSchema)
@rate_limit(limit=10, window=60)  # 10 requests per minute
async def update_profile(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    profile_data: UserUpdate = Body(...)
) -> Any:
    """
    Update the current user's profile information.
    
    Allows updating:
    - Full name
    - Email (requires verification)
    - Bio
    - Avatar
    - Preferences
    
    Rate limited to 10 requests per minute.
    """
    user_service: UserService = deps.get_user_service()
    
    # If email is being changed, verify it's not already taken
    if profile_data.email and profile_data.email != current_user.email:
        if await user_service.get_by_email_async(profile_data.email):
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    updated_user = await user_service.update_async(current_user, profile_data)
    return updated_user

@router.get("/me/settings", response_model=Dict[str, Any])
@rate_limit(limit=60, window=60)  # 60 requests per minute
async def get_settings(
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Get the current user's settings and preferences.
    
    Returns:
    - Notification preferences
    - Privacy settings
    - UI preferences
    - Exercise preferences
    - Subscription details
    
    Rate limited to 60 requests per minute.
    """
    settings = await user_service.get_user_settings(current_user.id)
    return settings

@router.put("/me/settings", response_model=Dict[str, Any])
@rate_limit(limit=10, window=60)  # 10 requests per minute
async def update_settings(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    settings_data: Dict[str, Any] = Body(...),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Update the current user's settings and preferences.
    
    Allows updating:
    - Notification preferences
    - Privacy settings
    - UI preferences
    - Exercise preferences
    
    Rate limited to 10 requests per minute.
    """
    updated_settings = await user_service.update_user_settings(
        user_id=current_user.id,
        settings=settings_data
    )
    return updated_settings 