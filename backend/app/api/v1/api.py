"""API v1 router configuration."""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    form_checks,
    subscriptions,
    workouts,
    health
)

# Create v1 router
api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    form_checks.router,
    prefix="/form-checks",
    tags=["Form Checks"]
)

api_router.include_router(
    subscriptions.router,
    prefix="/subscriptions",
    tags=["Subscriptions"]
)

api_router.include_router(
    workouts.router,
    prefix="/workouts",
    tags=["Workouts"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

__all__ = ["api_router"] 