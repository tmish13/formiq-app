"""Database session module.

This module re-exports database engine and session factories from app.core.database.
It provides convenient imports for database access throughout the application.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Generator
from contextlib import contextmanager

from backend.app.core.database import (
    async_engine, 
    async_session_factory, 
    get_async_db,
    sync_engine, 
    SessionLocal,
    Base
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import get_logger

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

@contextmanager
def get_db_session():
    """Database session context manager for Celery tasks.
    
    This creates a new database session, yields it, and ensures it's
    closed when the context is exited, even if an exception occurs.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

# ADDED FUNCTION
def get_settings_override() -> Settings:
    """
    Returns the application settings, potentially overridden for specific contexts.
    Currently, this returns the global application settings.
    This function is intended to be used where settings might need to be
    context-specific (e.g., Celery tasks, test environments).
    """
    return get_settings()

__all__ = [
    "async_engine",
    "engine",  # alias for async_engine
    "async_session_factory",
    "get_async_db",
    "get_db",  # async version
    "sync_engine",
    "SessionLocal",
    "get_sync_db", # sync version
    "get_db_session", # sync context manager
    "Base",
    "get_settings_override" # ADDED
] 