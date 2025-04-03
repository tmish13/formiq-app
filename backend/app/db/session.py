"""Database session module."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.core.database import async_engine, async_session, get_async_db as _get_async_db
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Re-export the engine and session factory
engine = async_engine

# Create synchronous engine and session for non-async operations
sync_engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Dependency to be injected into API routes
async def get_db():
    """Get async database session for dependency injection."""
    async for session in _get_async_db():
        yield session 