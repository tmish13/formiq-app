"""
Database module for SQLAlchemy ORM configuration.

This module provides database connection, session management, and 
database utility functions for both synchronous and asynchronous contexts.
"""
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from contextlib import contextmanager
from typing import Generator, Dict, Any, AsyncGenerator, List
import contextlib
import os

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import DatabaseError
from app.core.monitoring import track_db_operation, db_connections

import time

# Create Base class for models - imported in app/db/base_class.py
Base = declarative_base()

# Track connection usage statistics for monitoring
connection_stats = {
    "active_connections": 0,
    "total_connections": 0,
    "max_concurrent": 0,
    "connection_errors": 0,
    "connection_timeouts": 0,
    "last_error_time": None,
    "last_error_message": None
}

def get_database_url() -> str:
    """
    Get the appropriate database URL based on environment.
    
    Returns:
        str: Database URL
        
    Raises:
        DatabaseError: If database URL is not configured
    """
    if not settings.SQLALCHEMY_DATABASE_URI:
        raise DatabaseError("Database URL not configured", status_code=500)
    return settings.SQLALCHEMY_DATABASE_URI

def get_async_database_url() -> str:
    """
    Get the appropriate async database URL based on environment.
    
    Returns:
        str: Async database URL
        
    Raises:
        DatabaseError: If database URL is not configured
    """
    if os.environ.get("ENVIRONMENT") == "test":
        return "sqlite+aiosqlite:///./test.db"
    
    db_url = get_database_url()
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db_url

# Create async engine
async_engine = create_async_engine(
    get_async_database_url(),
    echo=settings.DB_ECHO,
    poolclass=NullPool if os.environ.get("ENVIRONMENT") == "test" else QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

# Create async session factory
async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create sync engine
sync_engine = create_engine(
    get_database_url(),
    echo=settings.DB_ECHO,
    poolclass=NullPool if os.environ.get("ENVIRONMENT") == "test" else QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

# Create sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Track connection events
@event.listens_for(sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Track new database connections."""
    connection_stats["active_connections"] += 1
    connection_stats["total_connections"] += 1
    if connection_stats["active_connections"] > connection_stats["max_concurrent"]:
        connection_stats["max_concurrent"] = connection_stats["active_connections"]
    db_connections.inc()

@event.listens_for(sync_engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Track closed database connections."""
    connection_stats["active_connections"] -= 1
    db_connections.dec()

@event.listens_for(sync_engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """Track database connection checkouts."""
    track_db_operation("checkout")

@event.listens_for(sync_engine, "checkin")
def checkin(dbapi_connection, connection_record):
    """Track database connection checkins."""
    track_db_operation("checkin")

def get_engine():
    """
    Get the SQLAlchemy engine.
    
    Returns:
        Engine: SQLAlchemy engine
    """
    return sync_engine

@contextlib.contextmanager
def get_db() -> Session:
    """
    Get a database session.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    """
    Check if the database connection is working.
    
    Raises:
        DatabaseError: If database connection fails
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        connection_stats["connection_errors"] += 1
        connection_stats["last_error_time"] = time.time()
        connection_stats["last_error_message"] = str(e)
        raise e

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    Yields:
        AsyncSession: Async database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Initialize the database.
    
    This function creates all tables in the database.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """
    Close the database connection.
    
    This function closes the async engine.
    """
    await async_engine.dispose()

def execute_raw_sql(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute a raw SQL query.
    
    Args:
        query (str): SQL query
        params (Dict[str, Any], optional): Query parameters. Defaults to None.
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    with get_db() as db:
        result = db.execute(text(query), params or {})
        return [dict(row) for row in result]

async def execute_raw_sql_async(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute a raw SQL query asynchronously.
    
    Args:
        query (str): SQL query
        params (Dict[str, Any], optional): Query parameters. Defaults to None.
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    async with async_session() as session:
        result = await session.execute(text(query), params or {})
        return [dict(row) for row in result]

def get_db_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    
    Returns:
        Dict[str, Any]: Database statistics
    """
    return {
        "active_connections": connection_stats["active_connections"],
        "total_connections": connection_stats["total_connections"],
        "max_concurrent": connection_stats["max_concurrent"],
        "connection_errors": connection_stats["connection_errors"],
        "connection_timeouts": connection_stats["connection_timeouts"],
        "last_error_time": connection_stats["last_error_time"],
        "last_error_message": connection_stats["last_error_message"],
    }

def optimize_query(query: str) -> str:
    """
    Optimize a SQL query.
    
    Args:
        query (str): SQL query
        
    Returns:
        str: Optimized SQL query
    """
    # Add query optimization logic here
    return query

def optimize_sqlalchemy_query(query):
    """
    Optimize a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query
        
    Returns:
        Query: Optimized SQLAlchemy query
    """
    # Add query optimization logic here
    return query 