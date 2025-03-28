from fastapi import APIRouter
from app.api.v1.endpoints import users, form_checks, subscriptions

api_router = APIRouter()

# Include routers
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(form_checks.router, prefix="/form-checks", tags=["form-checks"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])

__all__ = ["api_router"] 