"""API router module."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    exercises,
    form_checks,
    feedback,
    health,
    websockets,
    analysis,
    analytics,
    ml,
    progress,
    exercise_configs,
    workouts,
    cache_management
)
from .endpoints import training_data, admin
from app.api.v1.endpoints import videos

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(form_checks.router, prefix="/form-checks", tags=["form-checks"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(websockets.router, prefix="/ws", tags=["websockets"])
api_router.include_router(training_data.router, tags=["training-data"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(videos.router, tags=["videos"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(analytics.router, tags=["analytics"])
api_router.include_router(ml.router, tags=["ml"])
api_router.include_router(progress.router, tags=["progress"])
api_router.include_router(exercise_configs.router, tags=["exercise-configs"])
api_router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
api_router.include_router(cache_management.router, prefix="/cache", tags=["cache-management"])

__all__ = ["api_router"] 