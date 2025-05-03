"""Database session module.

This module re-exports database engine and session factories from app.core.database.
It provides convenient imports for database access throughout the application.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.core.database import (
    async_engine, 
    async_session_factory, 
    get_async_db,
    sync_engine, 
    SessionLocal,
    Base
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Re-export the engine and session factories for easy access
engine = async_engine

# Maintain backward compatibility for get_db
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session for dependency injection.
    
    This is a thin wrapper around the get_async_db function from app.core.database
    to provide backward compatibility with existing code using get_db.
    
    Yields:
        AsyncSession: Async database session
    """
    async for session in get_async_db():
        yield session

# Export a simpler sync session getter for non-async contexts
def get_sync_db() -> Session:
    """Get a synchronous database session.
    
    Returns:
        Session: Synchronous database session
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close() 