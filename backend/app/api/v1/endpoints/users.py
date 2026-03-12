"""Users router module."""
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.schemas.common import Message
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def read_user_me(
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
    """Update current user (full replacement)."""
    return await user_service.update_async(db_obj=current_user, obj_in=user_in)


@router.patch("/me", response_model=UserSchema)
async def patch_user_me(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    user_service: UserService = Depends(deps.get_user_service),
) -> Any:
    """Partially update the current user's profile.

    Accepts any subset of UserUpdate fields. Only supplied fields are changed.
    """
    return await user_service.update_async(db_obj=current_user, obj_in=user_in)


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
async def change_password(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service),
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
    """
    
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
async def update_profile(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service),
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
    """
    # If email is being changed, verify it's not already taken
    if profile_data.email and profile_data.email != current_user.email:
        if await user_service.get_by_email_async(profile_data.email):
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

    updated_user = await user_service.update_async(db_obj=current_user, obj_in=profile_data)
    return updated_user

@router.get("/me/settings", response_model=Dict[str, Any])
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
    """
    settings = await user_service.get_user_settings(current_user.id)
    return settings

@router.put("/me/settings", response_model=Dict[str, Any])
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
    """
    updated_settings = await user_service.update_user_settings(
        user_id=current_user.id,
        settings=settings_data
    )
    return updated_settings


@router.post("/me/avatar", response_model=Dict[str, Any])
async def upload_avatar(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    file: UploadFile = File(...),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Upload user avatar image.
    
    Args:
        file: Avatar image file (JPG, PNG, GIF supported)
        
    Returns:
        Avatar upload result with URL
        
    Raises:
        HTTPException: If file format not supported or upload fails
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, PNG, and GIF are supported."
        )
    
    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
        )
    
    try:
        # Upload avatar using user service
        avatar_result = await user_service.upload_avatar(
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": avatar_result["avatar_url"],
            "thumbnail_url": avatar_result.get("thumbnail_url")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar upload failed: {str(e)}"
        )


@router.delete("/me/avatar", response_model=Dict[str, str])
async def delete_avatar(
    *,
    db: AsyncSession = Depends(deps.get_async_db),
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Delete user avatar image.
    
    Returns:
        Deletion result message
    """
    try:
        await user_service.delete_avatar(current_user.id)
        return {"message": "Avatar deleted successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar deletion failed: {str(e)}"
        )


@router.get("/me/subscription", response_model=Dict[str, Any])
async def get_subscription(
    *,
    current_user: User = Depends(deps.get_current_user),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    Get user subscription details.
    
    Returns:
        Subscription information including plan, status, and usage
    """
    try:
        subscription = await user_service.get_subscription_details(current_user.id)
        return subscription
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subscription: {str(e)}"
        ) 