"""API router module."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, exercises, form_check

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exercises.router, prefix="/exercises", tags=["exercises"])
api_router.include_router(form_check.router, prefix="/form-checks", tags=["form-checks"])

__all__ = ["api_router"] 