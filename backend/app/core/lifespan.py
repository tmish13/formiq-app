"""Application lifespan management."""
import logging
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger
from app.core.cache import cache_service
from app.core.connection_pool import monitor as connection_monitor
from app.db.session import engine
from app.core.database import init_db, close_db

# Import additional initialization functions
from app.core.monitoring import init_monitoring
from app.core.logging import init_logging
from app.core.cache import init_cache
from app.core.storage import init_storage
from app.core.security import init_security
from app.api.deps import register_deps
from app.services.scheduler_service import scheduler

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Application startup")
    
    # Start the scheduler in non-production environments
    # In production, scheduler should be controlled via admin API
    if app.debug:
        logger.info("Starting scheduler in development mode")
        await scheduler.start()
    
    # Startup Logic
    logger.info(f"Application starting up in {settings.ENVIRONMENT} environment...")
    try:
        # Log Redis URL source at startup so it's visible in Render logs
        _redis_url = settings.REDIS_URL
        _masked = re.sub(r"(redis://[^:@/]*):([^@]+)@", r"\1:*****@", _redis_url)
        _src = "REDIS_URL env var" if os.getenv("REDIS_URL") else "fallback (REDIS_HOST/localhost)"
        logger.info(f"[Redis] URL source: {_src} → {_masked}")

        # Initialize core services
        init_monitoring()
        init_logging()
        await init_cache()
        await init_storage()
        init_security()
        
        # Test database connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info(f"Database connection successful: {result.scalar()}")

        # Ensure core exercise template seed data exists on every startup.
        # This is idempotent (WHERE NOT EXISTS) and runs in all environments
        # so that production deploys don't require a separate manual migration step.
        try:
            async with engine.begin() as conn:
                insert_result = await conn.execute(text("""
                    INSERT INTO exercise_templates
                        (id, name, description, difficulty, muscle_group, created_at, updated_at)
                    SELECT
                        'a1b2c3d4-e5f6-4a1b-8c3d-000000000001'::uuid,
                        'Squat',
                        'Barbell back squat — primary lower-body compound movement.',
                        'Beginner',
                        'Legs',
                        NOW(),
                        NOW()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM exercise_templates WHERE LOWER(name) = 'squat'
                    )
                """))
                rows_inserted = insert_result.rowcount
                if rows_inserted:
                    logger.info(
                        "Exercise template seed applied: inserted Squat row "
                        "(id=a1b2c3d4-e5f6-4a1b-8c3d-000000000001)"
                    )
                else:
                    logger.info("Exercise template seed verified: Squat row already present")
        except Exception as seed_err:
            # Log but never block startup — the app can still serve other endpoints.
            logger.warning(f"Exercise template seed check failed (non-fatal): {seed_err}")
        
        # Initialize database tables if needed (dev/test environments)
        if settings.ENVIRONMENT in ["development", "test"]:
            try:
                await init_db()
                logger.info("Database tables initialized")
            except Exception as init_error:
                logger.error(f"Database initialization failed: {str(init_error)}")
                if settings.ENVIRONMENT == "test":
                    raise  # Re-raise in test environment
        
        # Start connection pool monitoring (only in production and staging)
        if settings.ENVIRONMENT in ["production", "staging"]:
            connection_monitor.start_monitoring()
            logger.info("Database connection pool monitoring started")
        
        # Initialize Redis connection
        try:
            await cache_service.connect()
            if cache_service.available:
                logger.info("Redis connection successful")
            else:
                logger.warning("Redis is not available - caching disabled")
        except Exception as redis_error:
            logger.error(f"Redis connection failed: {str(redis_error)}")
            if settings.ENVIRONMENT == "production":
                raise  # Re-raise in production
        
        # Register API dependencies to fix circular imports
        register_deps()
        logger.info("API dependencies registered")

        # Beta / config warnings
        if settings.BETA_ALLOW_UNVERIFIED:
            logger.warning(
                "BETA_ALLOW_UNVERIFIED=true — unverified users can log in. "
                "This MUST be disabled before production launch."
            )
        if settings.emails_enabled:
            logger.info(
                "Email sending ENABLED via %s (username: %s).",
                settings.MAIL_SERVER,
                settings.MAIL_USERNAME or "(not set)",
            )
        else:
            logger.warning(
                "Email sending DISABLED — SMTP credentials are missing or still placeholder values. "
                "Verification emails will be skipped (no silent SMTP failures). "
                "Option A (Gmail): set MAIL_USERNAME=you@gmail.com and "
                "MAIL_PASSWORD=<16-char App Password from myaccount.google.com/apppasswords>. "
                "Option B (Resend, recommended): set MAIL_SERVER=smtp.resend.com, "
                "MAIL_USERNAME=resend, MAIL_PASSWORD=re_<api_key>, "
                "MAIL_FROM_EMAIL=you@yourdomain.com. "
                "After editing .env, restart the server (--reload does NOT re-read .env) and verify: "
                "curl -X POST http://localhost:8000/api/v1/debug/email-test "
                "-H 'Content-Type: application/json' -d '{\"to\":\"you@example.com\"}'"
            )

        # Deadlock guard: BETA_ALLOW_UNVERIFIED=false + no SMTP = nobody can ever log in.
        if not settings.BETA_ALLOW_UNVERIFIED and not settings.emails_enabled:
            logger.critical(
                "CONFIGURATION DEADLOCK: BETA_ALLOW_UNVERIFIED=false but SMTP is not configured. "
                "New users cannot verify their email, so NO ONE can log in. "
                "Fix: set BETA_ALLOW_UNVERIFIED=true in .env (use .env.beta-local) "
                "or configure real MAIL_* credentials (use .env.beta-email) and restart. "
                "Status: curl http://localhost:8000/api/v1/health/health/auth-config"
            )
            
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        if settings.ENVIRONMENT in ["production", "staging"]:
            raise  # Only raise in production/staging

    # Yield control to app
    yield
    
    # Shutdown
    logger.info("Application shutdown")
    
    # Stop the scheduler if it's running
    if scheduler.is_running:
        logger.info("Stopping scheduler")
        await scheduler.stop()
    
    # Shutdown Logic
    logger.info("Application shutting down...")
    try:
        # Stop connection pool monitoring
        if settings.ENVIRONMENT in ["production", "staging"]:
            connection_monitor.stop_monitoring()
            logger.info("Database connection pool monitoring stopped")
        
        # Close database connections
        await close_db()
        logger.info("Database connections closed successfully")
        
        # Close Redis connections
        if cache_service.available:
            await cache_service.close()
            logger.info("Redis connections closed")
        
        logger.info("Cleanup successful")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}") 