"""Core dependencies for the application."""

from typing import Generator, Optional, AsyncGenerator, Dict, Any, Union, List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import redis # For sync redis client

# Core Config and DB
from app.core.config import settings, Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_deps import get_async_db as get_async_db_session, get_db as get_db_session
from app.core.auth_utils import get_current_user_payload
from app.core.auth_scheme import oauth2_scheme

# Models
from app.models.user import User
from app.models.form_check import FormCheck
from app.models.form_check import FeedbackItem
from app.models.workout import Workout
from app.models.enums import SubscriptionTier

# Repositories (add these)
from app.repositories.form_check_repository import FormCheckRepository
from app.repositories.feedback_item_repository import FeedbackItemRepository

# Services & their Getters
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.workout_service import WorkoutService
from app.services.form_check_service import FormCheckService
from app.services.exercise_service import ExerciseService
from app.services.exercise_config_service import ExerciseConfigService
from app.services.progress_service import ProgressService, get_async_progress_service as get_progress_service_provider
from app.services.session_service import SessionService
from app.services.monitoring_service import MonitoringService
from app.services.health_service import HealthService
from app.services.dynamic_form_analysis_service import DynamicFormAnalysisService
from app.services.personalized_feedback_service import PersonalizedFeedbackService
from app.services.storage_service import StorageService
from app.services.ai_service import AIService
from app.services.email_service import EmailService
from app.services.video_service import VideoService
from app.services.video_processing_service import VideoProcessingService
from app.services.feedback_service import FeedbackService
from app.services.biomechanics_service import BiomechanicsService
from app.services.analytics_service import AnalyticsService

# Cache
from app.core.cache import cache_service, CacheService
from app.core.redis import get_redis as get_sync_redis_client
from app.core.logging import get_logger
logger = get_logger(__name__)

# Explicitly define get_redis_client for use by other modules
get_redis_client = get_sync_redis_client

# --- Settings ---
# def get_settings() -> Settings: # Remove local definition
#     return settings

# --- Database ---
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_db_session():
        yield session

# def get_db() -> Generator[Session, None, None]: # Removed original get_db definition
#     """Get a synchronous database session."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# --- Authentication ---
async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
    # The lambda import for user_repo needs to be able to find get_async_user_repository
    # Ensure get_async_user_repository in user_repository.py correctly imports its get_async_db from db_deps.
    user_repo = Depends(lambda: __import__('app.repositories.user_repository', fromlist=['get_async_user_repository']).get_async_user_repository),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate user credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.error("User ID (sub) not found in token payload.")
        raise credentials_exception
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.error(f"Invalid User ID format in token payload: {user_id_str}")
        raise credentials_exception

    user = await user_repo.get_by_id_async(id=user_id)
    if user is None:
        logger.warning(f"User with ID {user_id} not found in database.")
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user

# --- Subscription Tier Check ---
async def check_subscription_tier(
    required_tier: SubscriptionTier, 
    current_user: User = Depends(get_current_user)
) -> bool:
    user_tier_value = current_user.subscription_tier.value if current_user.subscription_tier else SubscriptionTier.FREE.value
    
    # Assuming tier enum values are ordered (e.g. FREE=0, BASIC=1, PRO=2)
    # Higher value means higher tier
    # Need to map enum string to an ordered value if not intrinsically comparable
    # For simplicity, let's assume a helper or direct comparison if .value is comparable
    
    tier_order = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.BASIC: 1,
        SubscriptionTier.PRO: 2,
        SubscriptionTier.PREMIUM: 3, # Assuming PREMIUM exists
        SubscriptionTier.ENTERPRISE: 4
    }
    
    current_tier_order = tier_order.get(current_user.subscription_tier, tier_order[SubscriptionTier.FREE])
    required_tier_order = tier_order.get(required_tier, tier_order[SubscriptionTier.FREE])

    if current_tier_order < required_tier_order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires a {required_tier.name} subscription or higher.",
        )
    return True

# --- Access Validators ---
async def validate_form_check_access(
    form_check_id: UUID, 
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
) -> FormCheck:
    form_check_repo = FormCheckRepository(db)
    form_check = await form_check_repo.get_by_id_async(form_check_id)
    if not form_check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form check not found",
        )
    if form_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this form check",
        )
    return form_check

async def validate_feedback_access(
    feedback_id: UUID, # Assuming FeedbackItem ID is UUID
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
) -> FeedbackItem:
    feedback_repo = FeedbackItemRepository(db)
    feedback_item = await feedback_repo.get_by_id_async(feedback_id)
    
    if not feedback_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback item not found",
        )
    
    # Access to feedback implies access to its parent form_check
    form_check = await feedback_item.awaitable_attrs.form_check # Ensure relationship is loaded or use service
    if not form_check: # Should not happen if DB integrity is maintained
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated form check not found")

    if form_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this feedback item",
        )
    return feedback_item

async def get_async_workout_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> WorkoutService:
    return WorkoutService(db=db, app_settings=app_settings)

async def validate_workout_access(
    workout_id: UUID,
    current_user: User = Depends(get_current_user),
    workout_service: WorkoutService = Depends(get_async_workout_service),
) -> Workout:
    workout = await workout_service.get_workout_details_async(workout_id=workout_id, user_id=current_user.id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found or access denied"
        )
    return workout

# --- Service Getters ---
async def get_async_user_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> UserService:
    return UserService(db=db, app_settings=app_settings)

async def get_async_subscription_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> SubscriptionService:
    return SubscriptionService(db=db, app_settings=app_settings)

# get_async_workout_service is defined above validate_workout_access

async def get_storage_service() -> StorageService:
    return StorageService()

async def get_ai_service() -> AIService:
    # AIService __init__ uses global settings
    return AIService()

def get_cache_service() -> CacheService:
    """Returns the global cache_service instance."""
    # Ensure cache_service is initialized (e.g., in lifespan)
    # For dependency injection, just returning the instance is fine.
    return cache_service

async def get_async_form_check_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings),
    storage_service: StorageService = Depends(get_storage_service),
    ai_service: AIService = Depends(get_ai_service),
    cache_service: CacheService = Depends(get_cache_service)
) -> FormCheckService:
    return FormCheckService(
        db=db, 
        settings=app_settings, 
        storage_service=storage_service, 
        ai_service=ai_service, 
        cache_service=cache_service
    )

async def get_async_exercise_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> ExerciseService:
    return ExerciseService(db=db, settings=app_settings)

async def get_async_exercise_config_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> ExerciseConfigService:
    return ExerciseConfigService(db=db, settings=app_settings)

async def get_async_progress_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> ProgressService:
    return get_progress_service_provider(db=db, settings=app_settings)

async def get_async_session_service(
    redis_cli: redis.Redis = Depends(get_redis_client),
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> SessionService:
    return SessionService(redis_client=redis_cli, db=db, app_settings=app_settings)

async def get_async_monitoring_service(
    app_settings: Settings = Depends(get_settings),
    redis_cli: Optional[redis.Redis] = Depends(get_redis_client)
) -> MonitoringService:
    return MonitoringService(app_settings=app_settings, redis_client=redis_cli)

async def get_async_health_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings),
    cache_service: CacheService = Depends(get_cache_service)
) -> HealthService:
    return HealthService(db=db, app_settings=app_settings, cache_client=cache_service)

async def get_async_dynamic_form_analysis_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings),
    exercise_config_svc: ExerciseConfigService = Depends(get_async_exercise_config_service),
    form_check_svc: FormCheckService = Depends(get_async_form_check_service)
) -> DynamicFormAnalysisService:
    return DynamicFormAnalysisService(
        db=db, 
        settings=app_settings, 
        exercise_config_service=exercise_config_svc,
        form_check_service=form_check_svc
    )

async def get_async_personalized_feedback_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings)
) -> PersonalizedFeedbackService:
    return PersonalizedFeedbackService(db=db, settings=app_settings)

# --- Providers for newly added services ---

async def get_email_service() -> EmailService:
    """Get EmailService instance."""
    return EmailService()

async def get_async_video_service(
    db: AsyncSession = Depends(get_async_db_session),
    storage_service: StorageService = Depends(get_storage_service),
    app_settings: Settings = Depends(get_settings) # Changed from settings for consistency
) -> VideoService:
    return VideoService(db=db, storage_service=storage_service, app_settings=app_settings)

async def get_async_video_processing_service(
    app_settings: Settings = Depends(get_settings)
) -> VideoProcessingService:
    return VideoProcessingService(app_settings=app_settings)

async def get_async_feedback_service(
    video_processing_service: VideoProcessingService = Depends(get_async_video_processing_service)
) -> FeedbackService:
    return FeedbackService(video_processing_service=video_processing_service)

async def get_biomechanics_service() -> BiomechanicsService:
    """Get BiomechanicsService instance."""
    return BiomechanicsService()

async def get_async_analytics_service(
    db: AsyncSession = Depends(get_async_db_session),
    app_settings: Settings = Depends(get_settings),
    cache_svc: CacheService = Depends(get_cache_service)
) -> AnalyticsService:
    return AnalyticsService(db=db, settings=app_settings, cache_svc=cache_svc)

# Add all to __all__ for easier re-exporting if app.api.deps needs them
__all__ = [
    "get_settings",
    "get_async_db",
    "get_db_session",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_current_active_superuser",
    "check_subscription_tier",
    "validate_form_check_access",
    "validate_feedback_access",
    "validate_workout_access",
    "get_async_user_service",
    "get_async_subscription_service",
    "get_async_workout_service",
    "get_storage_service",
    "get_ai_service",
    "get_cache_service",
    "get_async_form_check_service",
    "get_async_exercise_service",
    "get_async_exercise_config_service",
    "get_async_progress_service",
    "get_async_session_service",
    "get_async_monitoring_service",
    "get_async_health_service",
    "get_async_dynamic_form_analysis_service",
    "get_async_personalized_feedback_service",
    # Newly added service getters
    "get_email_service",
    "get_async_video_service",
    "get_async_video_processing_service",
    "get_async_feedback_service",
    "get_biomechanics_service",
    "get_async_analytics_service",
    # Corresponding Services
    "EmailService",
    "VideoService",
    "VideoProcessingService",
    "FeedbackService",
    "BiomechanicsService",
    "AnalyticsService",
    # Models and Enums that might be used in type hints in endpoints
    "User",
    "FormCheck",
    "FeedbackItem",
    "Workout",
    "SubscriptionTier",
    "AsyncSession",
    "Session",
    "Depends",
    "HTTPException",
    "status",
    "ProgressService",
    "get_progress_service_provider"
] 