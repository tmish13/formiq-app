"""Main application module."""
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Core imports
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.lifespan import lifespan

# API imports
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi

# Middleware imports
from app.core.middleware import setup_middleware, EnhancedRateLimiter

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Define API tags metadata
tags_metadata = [
    {
        "name": "authentication",
        "description": "Operations with user authentication. Includes registration, login, and token management."
    },
    {
        "name": "users",
        "description": "Operations about users. Includes profile management and settings."
    },
    {
        "name": "form-analysis",
        "description": "Exercise form analysis operations. Includes video upload and analysis results."
    },
    {
        "name": "workouts",
        "description": "Workout management operations. Includes plans and exercises."
    },
    {
        "name": "health",
        "description": "API health check and monitoring endpoints."
    }
]

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FormIQ API",
        description="""
        FormIQ API - Exercise Form Analysis and Workout Planning Platform
        
        ## Features
        * 👤 User Authentication and Management
        * 📊 Exercise Form Analysis
        * 🎯 Personalized Workout Plans
        * 📝 Form Check Submissions
        * 📈 Progress Tracking
        
        ## Authentication
        * All authenticated endpoints require a valid JWT token
        * Token must be included in the Authorization header as: `Bearer {token}`
        * Obtain tokens via the `/api/v1/auth/login` endpoint
        * Access tokens expire after 30 minutes
        * Refresh tokens expire after 7 days
        
        ## Rate Limiting
        * Authentication endpoints: 5 requests per minute
        * Form analysis upload: 10 requests per 2 minutes
        * Standard endpoints: 60 requests per minute
        * Rate limits are per user/IP combination
        
        ## Error Handling
        * All errors follow standard HTTP status codes
        * Error responses include detailed messages
        * Validation errors list all field-specific issues
        """,
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        openapi_tags=tags_metadata,
        terms_of_service="https://formiq.com/terms/",
        contact={
            "name": "FormIQ Support",
            "url": "https://formiq.com/support",
            "email": "support@formiq.com",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://formiq.com/license",
        },
        lifespan=lifespan,
    )

    # Configure middleware
    setup_middleware(app)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    app.add_middleware(EnhancedRateLimiter)

    # Add API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(health_router)

    # Set custom OpenAPI schema
    if settings.ENVIRONMENT != "production":
        app.openapi = custom_openapi(app)

    # Initialize core services
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on application startup."""
        # Initialize monitoring
        init_monitoring()
        
        # Initialize logging
        init_logging()
        
        # Initialize cache
        await init_cache()
        
        # Initialize rate limiting
        await init_rate_limit()
        
        # Initialize storage
        await init_storage()
        
        # Initialize security
        init_security()

    # Error handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail)}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handle request validation errors."""
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)}
        )

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