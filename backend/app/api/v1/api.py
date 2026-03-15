"""API router module."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    exercises,
    form_checks,
    feedback,
    health,
    analysis,
    analytics,
    ml,
    progress,
    exercise_configs,
    cache_management,
    metrics_analysis,
    circuit_breakers,
    squat_sessions,
    training_sessions,
)
from .endpoints import admin, debug
from .endpoints.debug import beta_router
from app.api.v1.endpoints import videos

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(form_checks.router, prefix="/form-checks", tags=["form-checks"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(videos.router, tags=["videos"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(ml.router, tags=["ml"])
api_router.include_router(analytics.router)
api_router.include_router(progress.router, tags=["progress"])
api_router.include_router(exercise_configs.router, tags=["exercise-configs"])
api_router.include_router(cache_management.router, prefix="/cache", tags=["cache-management"])
api_router.include_router(metrics_analysis.router, prefix="/metrics-analysis", tags=["metrics-analysis"])
api_router.include_router(circuit_breakers.router, prefix="/circuit-breakers", tags=["circuit-breakers"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(beta_router, tags=["beta"])
api_router.include_router(squat_sessions.router, prefix="/squat-sessions", tags=["squat-sessions"])
api_router.include_router(training_sessions.router, prefix="/training-sessions", tags=["training-sessions"])

__all__ = ["api_router"]