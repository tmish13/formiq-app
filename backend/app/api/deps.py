"""API dependencies."""
# Import dependencies from core.deps
from app.core.deps import (
    get_db,
    get_current_user,
    get_current_active_user,
    get_current_active_superuser,
    validate_form_check_access,
    validate_feedback_access,
    check_subscription_tier
) 

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.core.security import oauth2_scheme
from typing import Dict, Any, Callable

# Dictionary of services and repositories to be used as dependencies
dependencies: Dict[str, Any] = {}

# Fix the circular dependency by registering this function after import
def register_deps():
    """Register dependencies after application startup."""
    dependencies["get_user_service"] = get_user_service

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency for getting the user service."""
    user_repo = UserRepository(db)
    return UserService(repository=user_repo)

# Additional dependency functions can be added here 