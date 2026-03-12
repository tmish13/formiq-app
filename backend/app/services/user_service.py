"""User service module."""
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt
from fastapi import Depends, HTTPException, status

from app.core.config import settings, Settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    verify_email_verification_token_and_get_email
)
from app.core.exceptions import (
    AuthenticationException,
    ValidationException,
    NotFoundException,
    EmailError,
    ValidationError,
    ServiceError
)
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User,
    UserFilter,
    UserInDB
)
from app.schemas.token import Token
from app.core.password import get_password_hash, verify_password
from app.models.user import User as DBUser
from app.models.subscription import Subscription as DBSubscription
from app.services.base_service import BaseService

# Setup logger
logger = logging.getLogger(__name__)

class UserService(BaseService[DBUser, UserCreate, UserUpdate]):
    """User service for managing users, now inheriting from BaseService."""
    
    def __init__(self, db: Union[AsyncSession, Session], app_settings: Settings):
        super().__init__(db=db, model=DBUser, settings=app_settings)

    async def get_by_email_async(self, email: str) -> Optional[DBUser]:
        """Get user by email asynchronously."""
        try:
            stmt = select(self.model).filter(self.model.email == email.lower())
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}", exc_info=True)
            raise ServiceError(f"Failed to get user by email: {str(e)}")

    async def create_user_async(self, user_in: UserCreate, is_superuser: bool = False) -> DBUser:
        """Create a new user asynchronously, handling password hashing."""
        hashed_password = get_password_hash(user_in.password)
        user_data_dict = user_in.model_dump(exclude_unset=True)
        user_data_dict["hashed_password"] = hashed_password
        user_data_dict["password"] = None
        user_data_dict["is_superuser"] = is_superuser
        
        db_user = await super().create_async(obj_in=user_data_dict)
        return db_user

    async def update_user_async(self, user_id: UUID, user_in: UserUpdate) -> Optional[DBUser]:
        """Update an existing user asynchronously."""
        db_obj = await super().get_async(id=user_id)
        if not db_obj:
                return None
            
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            update_data["hashed_password"] = hashed_password
            del update_data["password"]
        else:
            update_data.pop("password", None)
            update_data.pop("hashed_password", None)

        return await super().update_async(db_obj=db_obj, obj_in=update_data)

    async def update_user_subscription_async(self, 
                                      user_id: UUID,
                                      tier: str, 
                                      start_date: Optional[datetime] = None, 
                                      end_date: Optional[datetime] = None,
                                      is_active: bool = True,
                                      provider: str = "internal",
                                      provider_subscription_id: Optional[str] = None) -> DBUser:
        """Update a user's subscription asynchronously with specific parameters."""
        user = await super().get_async(id=user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")
        
        user.subscription_tier = tier
        user.subscription_is_active = is_active
        self.db.add(user)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Subscription updated for user {user_id} to tier {tier}")
        return user
    
    async def complete_onboarding(
        self,
        db: AsyncSession,
        user_id: UUID,
        fitness_goal: Optional[str] = None,
        preferred_exercises: Optional[List] = None,
    ) -> DBUser:
        """
        Mark a user's onboarding as completed, optionally persisting preferences.

        Args:
            db: Database session
            user_id: ID of the user to update
            fitness_goal: Optional primary fitness goal string
            preferred_exercises: Optional list of exercise name strings

        Returns:
            Updated user object

        Raises:
            NotFoundException: If user is not found
        """
        from datetime import datetime

        user = await db.get(DBUser, user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")

        user.has_completed_onboarding = True
        user.onboarding_completed_at = datetime.utcnow()

        if fitness_goal is not None:
            user.fitness_goal = fitness_goal
        if preferred_exercises is not None:
            user.preferred_exercises = preferred_exercises

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Onboarding completed for user {user_id}")
        return user

    async def upload_avatar(
        self,
        user_id: UUID,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> Dict[str, str]:
        """
        Save an avatar image locally and update the user's profile_image_url.

        Files are stored under uploads/avatars/ relative to the process CWD
        (i.e. the backend/ directory when uvicorn is started from there).

        Args:
            user_id: UUID of the user
            file_content: Raw bytes of the image file
            filename: Original filename (used to derive extension)
            content_type: MIME type (not used for storage, validated by endpoint)

        Returns:
            Dict with avatar_url and thumbnail_url keys
        """
        import os
        from pathlib import Path

        upload_dir = Path("uploads/avatars")
        upload_dir.mkdir(parents=True, exist_ok=True)

        _, ext = os.path.splitext(filename)
        ext = ext.lower() if ext else ".jpg"
        avatar_filename = f"{user_id}{ext}"
        file_path = upload_dir / avatar_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        avatar_url = f"/uploads/avatars/{avatar_filename}"

        # Persist the URL on the user record
        user = await self.db.get(DBUser, user_id)
        if user:
            user.profile_image_url = avatar_url
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return {"avatar_url": avatar_url, "thumbnail_url": avatar_url}

    async def get_user_settings(self, user_id: UUID) -> Dict[str, Any]:
        """Get user settings and preferences."""
        user = await self.db.get(DBUser, user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")

        return {
            "notifications": {
                "email_updates": True,
                "workout_reminders": True,
                "progress_reports": True,
            },
            "privacy": {
                "profile_public": False,
                "share_progress": False,
            },
            "ui": {
                "theme": "light",
                "language": "en",
            },
            "exercise": {
                "fitness_level": getattr(user, "fitness_level", None),
                "fitness_goal": getattr(user, "fitness_goal", None),
                "preferred_exercises": getattr(user, "preferred_exercises", []) or [],
            },
        }

    async def update_user_settings(self, user_id: UUID, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update user settings, persisting exercise preferences to the user model."""
        user = await self.db.get(DBUser, user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")

        exercise_settings = settings.get("exercise", {})
        if "fitness_level" in exercise_settings:
            user.fitness_level = exercise_settings["fitness_level"]
        if "fitness_goal" in exercise_settings:
            user.fitness_goal = exercise_settings["fitness_goal"]
        if "preferred_exercises" in exercise_settings:
            user.preferred_exercises = exercise_settings["preferred_exercises"]

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return await self.get_user_settings(user_id)

    async def delete_avatar(self, user_id: UUID) -> None:
        """Delete avatar file from disk and clear profile_image_url."""
        from pathlib import Path

        user = await self.db.get(DBUser, user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")

        if user.profile_image_url:
            rel_path = user.profile_image_url.lstrip("/")
            file_path = Path(rel_path)
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError as exc:
                logger.warning(f"Could not delete avatar file {file_path}: {exc}")

        user.profile_image_url = None
        self.db.add(user)
        await self.db.commit()

    async def get_subscription_details(self, user_id: UUID) -> Dict[str, Any]:
        """Return subscription information derived from the user model."""
        user = await self.db.get(DBUser, user_id)
        if not user:
            raise NotFoundException(f"User {user_id} not found")

        tier = str(getattr(user, "subscription_tier", "free") or "free")
        is_active = bool(getattr(user, "subscription_is_active", True))

        tier_limits: Dict[str, Any] = {
            "free": {"analyses_per_month": 10, "video_storage_gb": 1},
            "pro": {"analyses_per_month": 100, "video_storage_gb": 10},
            "enterprise": {"analyses_per_month": -1, "video_storage_gb": 100},
        }.get(tier, {"analyses_per_month": 10, "video_storage_gb": 1})

        return {
            "plan": tier,
            "status": "active" if is_active else "inactive",
            "features": tier_limits,
            "billing": {
                "next_billing_date": None,
                "amount": None,
            },
        }


def get_user_service(
) -> UserService:
    """
    Get user service instance for synchronous operations.
    
    Args:
        db: SQLAlchemy database session
        app_settings: Application settings
        
    Returns:
        User service instance
    """
    from app.core.deps import get_db, get_settings
    from fastapi import Depends
    
    # Re-declare with Depends pointing to the now-imported functions
    actual_db: Session = Depends(get_db)
    actual_app_settings: Settings = Depends(get_settings)
    
    return UserService(db=actual_db, app_settings=actual_app_settings)

async def get_async_user_service(
) -> UserService:
    """
    Get user service instance for asynchronous operations.
    
    Args:
        db: SQLAlchemy asynchronous database session
        app_settings: Application settings
        
    Returns:
        User service instance
    """
    from app.core.deps import get_async_db, get_settings
    from fastapi import Depends

    # Re-declare with Depends pointing to the now-imported functions
    actual_db: AsyncSession = Depends(get_async_db)
    actual_app_settings: Settings = Depends(get_settings)

    return UserService(db=actual_db, app_settings=actual_app_settings)