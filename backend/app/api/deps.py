"""API dependencies."""
# Import dependencies from core.deps
from app.core.deps import get_db, get_async_db, get_settings, get_current_user, get_current_active_user, get_current_active_superuser, check_subscription_tier, validate_form_check_access, validate_feedback_access, get_redis_client

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from jose import jwt
from fastapi.security import OAuth2PasswordBearer

from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.core.security import oauth2_scheme
from app.core.config import settings, Settings
from app.core.db_deps import get_db, get_async_db
from app.core.database import SessionLocal
from app.core.security import (
    create_access_token, 
    verify_session_token_and_get_payload,
    get_password_hash,
    verify_password,
    create_email_verification_token,
    create_password_reset_token,
    verify_password_reset_token_and_get_email,
)
from app.models.user import User
from app.services.session_service import SessionService, get_async_session_service
from app.repositories.session_repository import SessionRepository
from typing import Dict, Any, Callable, Generator, Optional
from app.services.auth_service import AuthService
from app.services.video_service import VideoService
from app.services.storage_service import StorageService
from app.services.email_service import EmailService
from app.services.exercise_service import get_async_exercise_service
from app.services.progress_service import get_async_progress_service
from app.services.video_processing_service import get_async_video_processing_service
from app.services.feedback_service import get_async_feedback_service
from app.services.form_check_service import FormCheckService
from app.services.exercise_config_service import get_async_exercise_config_service, get_exercise_config_service
from app.services.ai_service import AIService
from app.core.cache import CacheService
from app.services.dynamic_form_analysis_service import get_async_dynamic_form_analysis_service
from app.services.biomechanics_service import get_biomechanics_service
from app.services.personalized_feedback_service import get_async_personalized_feedback_service
from app.services.health_service import get_async_health_service
from app.services.monitoring_service import get_async_monitoring_service
from app.services.analytics_service import get_async_analytics_service

# Dictionary to hold services and repositories
dependencies: Dict[str, Callable[..., Any]] = {}

# Fix the circular dependency by registering this function after import
def register_deps():
    """Register dependencies after application startup."""
    dependencies["get_user_service"] = get_user_service
    dependencies["get_session_service"] = get_async_session_service
    dependencies["get_auth_service"] = get_auth_service
    dependencies["get_video_service"] = get_video_service
    dependencies["get_email_service"] = get_email_service
    dependencies["get_exercise_service"] = get_async_exercise_service
    dependencies["get_progress_service"] = get_async_progress_service
    dependencies["get_video_processing_service"] = get_async_video_processing_service
    dependencies["get_feedback_service"] = get_async_feedback_service
    dependencies["get_form_analysis_service"] = get_async_form_check_service
    dependencies["get_exercise_config_service"] = get_async_exercise_config_service
    dependencies["get_video_service"] = get_async_video_service
    dependencies["get_form_check_service"] = get_async_form_check_service
    dependencies["get_dynamic_form_analysis_service"] = get_async_dynamic_form_analysis_service
    dependencies["get_biomechanics_service"] = get_biomechanics_service
    dependencies["get_personalized_feedback_service"] = get_async_personalized_feedback_service
    dependencies["get_health_service"] = get_async_health_service
    dependencies["get_monitoring_service"] = get_async_monitoring_service
    dependencies["get_analytics_service"] = get_async_analytics_service

async def get_user_service(db: AsyncSession = Depends(get_async_db), app_settings: Settings = Depends(get_settings)) -> UserService:
    """Dependency for getting the user service."""
    return UserService(db=db, app_settings=app_settings)

# Old get_session_service - to be removed or commented out
# async def get_session_service(db: AsyncSession = Depends(get_async_db)) -> SessionService:
#     """Dependency for getting the session service."""
#     session_repo = SessionRepository(db) # Old: imports SessionRepository, which should be unused now by SessionService
#     return SessionService(repository=session_repo) # Old: SessionService constructor changed

async def get_email_service() -> EmailService:
    """Dependency for getting the email service."""
    # Assuming EmailService() is sufficient, or EmailService(db=db) if it needs a session.
    # For now, keeping it simple. This might need adjustment if EmailService has complex deps.
    return EmailService()

async def get_auth_service(
    db: AsyncSession = Depends(get_async_db),
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
    app_settings: Settings = Depends(get_settings)
) -> AuthService:
    """Dependency for getting the authentication service."""
    # AuthService constructor does not take settings currently.
    # If it needs settings, its __init__ must be updated first.
    return AuthService(db=db, user_service=user_service, email_service=email_service)

async def get_video_service(db: AsyncSession = Depends(get_async_db), app_settings: Settings = Depends(get_settings)) -> VideoService:
    """Dependency for getting the video service."""
    storage_service = StorageService()
    # VideoService constructor does not take settings currently.
    # If it needs settings, its __init__ must be updated first.
    return VideoService(db=db, storage_service=storage_service)

async def get_async_storage_service(): # Placeholder if get_storage_service is not async already
    # This should actually return an instance of StorageService, possibly async initialized
    # For now, assuming get_storage_service can be used or adapted
    pass

async def get_async_video_service(
    db: AsyncSession = Depends(get_async_db),
    storage_service: StorageService = Depends(StorageService),
    settings: Settings = Depends(get_settings)
) -> VideoService:
    return VideoService(db=db, storage_service=storage_service, settings=settings)

# Placeholder for CacheService provider
async def get_cache_service() -> Optional[CacheService]:
    # In a real app, this would initialize and return a CacheService instance
    # or None if caching is disabled or misconfigured.
    # from app.core.cache import create_cache_client # Example
    # client = create_cache_client()
    # if client and client.is_available_sync(): # or await client.is_available()
    #     return CacheService(client)
    logger.info("get_cache_service called, returning None (stubbed). Caching will be disabled for FormCheckService.")
    return None # Return None if cache is not configured/available

async def get_ai_service() -> AIService:
    """Dependency for getting the AI service."""
    return AIService()

async def get_storage_service() -> StorageService:
    """Dependency for getting the Storage service."""
    # StorageService uses a global provider if None is passed, or takes a StorageProvider
    # Assuming global storage_provider is configured.
    return StorageService()

async def get_async_form_check_service(
    db: AsyncSession = Depends(get_async_db),
    settings: Settings = Depends(get_settings),
    storage_service: StorageService = Depends(get_storage_service),
    ai_service: AIService = Depends(get_ai_service),
    cache_service: Optional[CacheService] = Depends(get_cache_service)
) -> FormCheckService:
    return FormCheckService(
        db=db, 
        settings=settings, 
        storage_service=storage_service, 
        ai_service=ai_service, 
        cache_service=cache_service
    )

# Alias for convenience if modules directly access deps.get_form_check_service
get_form_check_service = get_async_form_check_service

# Service dependencies dictionary
# ... existing code ... 