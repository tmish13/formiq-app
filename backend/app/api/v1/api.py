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
    analysis
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

__all__ = ["api_router"] 