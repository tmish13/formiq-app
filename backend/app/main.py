from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import get_logger
from app.core.monitoring import init_monitoring
from app.middleware.middleware import FormIQMiddleware
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.docs import custom_openapi
from app.core.database import engine
from app.core.cache import cache_service

logger = get_logger(__name__)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="FormIQ API for exercise form analysis",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add consolidated middleware
    application.add_middleware(FormIQMiddleware)
    
    # Initialize monitoring
    init_monitoring(application)
    
    # Include API router
    application.include_router(api_router, prefix=settings.API_V1_STR)
    application.include_router(health_router, prefix=settings.API_V1_STR)
    
    # Set custom OpenAPI schema
    application.openapi = custom_openapi
    
    @application.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("Starting up application...")
        try:
            # Test database connection
            await engine.connect()
            logger.info("Database connection successful")
            
            # Test Redis connection
            await cache_service.ping()
            logger.info("Redis connection successful")
            
        except Exception as e:
            logger.error("Startup error", error=str(e))
            raise
    
    @application.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down application...")
        try:
            await engine.dispose()
            await cache_service.close()
            logger.info("Cleanup successful")
        except Exception as e:
            logger.error("Shutdown error", error=str(e))
    
    return application

app = create_application()

@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "api_prefix": settings.API_V1_STR
    } 