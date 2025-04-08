"""API router module."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, exercises, form_checks, feedback, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(form_checks.router, prefix="/form-checks", tags=["form-checks"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(health.router, prefix="/health", tags=["health"])

__all__ = ["api_router"] 