"""Main application module."""
import logging
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time

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
        "name": "form-checks",
        "description": "Exercise form check operations. Includes video upload, status tracking, and analysis results retrieval."
    },
    {
        "name": "analysis",
        "description": "Operations related to triggering and managing AI analysis of forms and videos."
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
    logger.info("CORS middleware configured")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add API router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(health_router)

    # Set custom OpenAPI schema
    if settings.ENVIRONMENT != "production":
        app.openapi = custom_openapi(app)

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests and their processing time."""
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the request
        logger.info(
            f"{request.client.host} - {request.method} {request.url.path} "
            f"- {response.status_code} - {duration:.4f}s"
        )
        
        return response

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