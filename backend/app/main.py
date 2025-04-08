"""Main application module."""
import logging
from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

# Core imports
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.lifespan import lifespan

# API imports
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi

# Middleware imports
from app.core.middleware import setup_middleware

# Initialize logging
setup_logging()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENVIRONMENT != "production" else None,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Configure middleware
    setup_middleware(app)

    # Add API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(health_router)

    # Set custom OpenAPI schema
    if settings.ENVIRONMENT != "production":
        app.openapi = custom_openapi(app)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FormIQ with Uvicorn")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="debug" if settings.DEBUG else "info"
    ) 