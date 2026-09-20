"""
Database module for SQLAlchemy ORM configuration.

This module provides database connection, session management, and 
database utility functions for both synchronous and asynchronous contexts.
"""
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, Dict, Any, AsyncGenerator, List, Union, Optional
import contextlib
import os
import time
import json
from urllib.parse import quote_plus
import asyncio
import inspect

from app.core.config import settings, get_settings, Settings
from app.core.logging import get_logger
from app.core.exceptions import DatabaseException
from app.core.monitoring import track_db_operation, db_connections

# Set up logging
logger = get_logger(__name__)

# Create Base class for models - imported in app/db/base_class.py
Base = declarative_base()

# Import all models to ensure they're registered with Base.metadata
# This needs to be imported for ORM mapper initialization
# REMOVING WILDCARD IMPORT TO RESOLVE CIRCULAR DEPENDENCY
# from app.db.base import *

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

# Correctly get settings for engine creation
s_for_engine = get_settings()

def get_database_url() -> str:
    """
    Get the appropriate database URL based on environment.
    
    Returns:
        str: Database URL
        
    Raises:
        DatabaseException: If database URL is not configured
    """
    if not settings.SQLALCHEMY_DATABASE_URI:
        raise DatabaseException("Database URL not configured", status_code=500)
    return settings.SQLALCHEMY_DATABASE_URI

def get_async_database_url() -> str:
    """
    Get the appropriate async database URL based on environment.
    
    Returns:
        str: Async database URL
        
    Raises:
        DatabaseException: If database URL is not configured
    """
    if settings.ENVIRONMENT == "test":
        return "sqlite+aiosqlite:///./test.db"
    
    db_url = get_database_url()
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("sqlite://"):
        return db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return db_url

def get_engine_settings(url: str) -> Dict[str, Any]:
    """
    Get database engine settings based on URL.
    
    Args:
        url: Database URL
        
    Returns:
        Dict[str, Any]: Engine settings
    """
    is_sqlite = url.startswith("sqlite")
    is_test = settings.ENVIRONMENT == "test"
    
    # Use NullPool only for tests and SQLite (no real DB server).
    # asyncpg/PostgreSQL in production MUST use QueuePool so connections are
    # reused across requests — NullPool creates a new TCP connection per query.
    is_nullpool = is_test or is_sqlite
    engine_settings = {
        "echo": settings.DB_ECHO,
        "poolclass": NullPool if is_nullpool else QueuePool,
    }
    
    # Add connection arguments for SQLite
    if is_sqlite:
        engine_settings["connect_args"] = {"check_same_thread": False}
    
    # Add pool settings for production PostgreSQL, only if not using NullPool
    if not is_sqlite and not is_test and engine_settings.get("poolclass") is not NullPool:
        engine_settings.update({
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,  # Verify connections before checkout
        })
    
    return engine_settings

# Create async engine
async_engine = create_async_engine(
    s_for_engine.ASYNC_DATABASE_URL,
    **get_engine_settings(s_for_engine.ASYNC_DATABASE_URL)
)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ── Celery-safe async engine ────────────────────────────────────────────────
# Each Celery task runs via asyncio.run(), creating a NEW event loop per task.
# The QueuePool above keeps asyncpg connections alive between tasks; those
# connections are bound to the event loop that created them. When the next
# task's fresh loop tries to use or close them it gets:
#   "Future <Future pending> attached to a different loop"
#   "RuntimeError: Event loop is closed"
#
# Fix: NullPool — no connection is ever kept between operations. Every DB call
# opens a fresh TCP connection in the current loop and closes it on release.
# The cost (one extra handshake per task) is negligible for video-analysis jobs.
# Created lazily, never at import, and rebuilt whenever the PID changes.
#
# Under -P prefork the worker forks children AFTER this module is imported. An
# engine built at import time is therefore inherited by every child, and all of
# them share one object whose internal state was set up in the parent's process
# and (for anything loop-bound) the parent's event loop. NullPool means there are
# no live asyncpg sockets to inherit, which is why this has not corrupted data,
# but the engine still must not be shared: keying on PID guarantees each process
# builds its own, whether it was created before or after the fork.
_celery_async_engine = None
_celery_async_session_factory = None
_celery_engine_pid = None


def get_celery_async_engine():
    """Return this process's Celery engine, creating it on first use."""
    global _celery_async_engine, _celery_async_session_factory, _celery_engine_pid
    pid = os.getpid()
    if _celery_async_engine is None or _celery_engine_pid != pid:
        if _celery_engine_pid is not None and _celery_engine_pid != pid:
            # Inherited across a fork. Drop the reference without disposing it:
            # disposing here would reach into the parent's engine.
            logger.info(
                "Celery async engine inherited from PID %s; building a fresh one "
                "for PID %s.", _celery_engine_pid, pid,
            )
        _celery_async_engine = create_async_engine(
            s_for_engine.ASYNC_DATABASE_URL,
            poolclass=NullPool,
        )
        _celery_async_session_factory = async_sessionmaker(
            bind=_celery_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        _celery_engine_pid = pid
    return _celery_async_engine


def get_celery_async_session_factory():
    """Return this process's Celery session factory, creating it on first use."""
    get_celery_async_engine()
    return _celery_async_session_factory


async def dispose_celery_async_engine() -> None:
    """Dispose this process's Celery engine, if it owns one."""
    global _celery_async_engine, _celery_async_session_factory, _celery_engine_pid
    if _celery_async_engine is not None and _celery_engine_pid == os.getpid():
        await _celery_async_engine.dispose()
    _celery_async_engine = None
    _celery_async_session_factory = None
    _celery_engine_pid = None

# Create sync engine for operations that need synchronous access
sync_engine = create_engine(
    get_database_url(),
    **get_engine_settings(get_database_url())
)

# Create sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Register Base.metadata with the sync_engine to ensure all models are available
Base.metadata.bind = sync_engine

# Track connection events for the sync engine
@event.listens_for(sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Track new database connections."""
    connection_stats["active_connections"] += 1
    connection_stats["total_connections"] += 1
    if connection_stats["active_connections"] > connection_stats["max_concurrent"]:
        connection_stats["max_concurrent"] = connection_stats["active_connections"]
    db_connections.labels(state="active").inc()
    db_connections.labels(state="total").inc()

@event.listens_for(sync_engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Track closed database connections."""
    connection_stats["active_connections"] -= 1
    db_connections.labels(state="active").dec()

@event.listens_for(sync_engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """Track database connection checkouts."""
    track_db_operation("checkout", "connection_pool", 0)

@event.listens_for(sync_engine, "checkin")
def checkin(dbapi_connection, connection_record):
    """Track database connection checkins."""
    track_db_operation("checkin", "connection_pool", 0)

def get_engine():
    """
    Get the SQLAlchemy engine.
    
    Returns:
        Engine: SQLAlchemy engine
    """
    return sync_engine

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get a database session using a context manager.
    
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
        DatabaseException: If database connection fails
    """
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        connection_stats["connection_errors"] += 1
        connection_stats["last_error_time"] = time.time()
        connection_stats["last_error_message"] = str(e)
        raise DatabaseException(f"Database connection failed: {str(e)}", status_code=500) from e

async def get_async_db() -> AsyncGenerator[Union[AsyncSession, Session], None]:
    """
    Get an async database session.
    
    Yields:
        AsyncSession: Async database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

@asynccontextmanager
async def get_async_session_for_celery() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a NullPool-backed AsyncSession for Celery tasks.

    Uses _celery_async_engine (NullPool) so no asyncpg connection is ever
    held across asyncio.run() boundaries. Each task gets a fresh connection
    in its own event loop — no "Future attached to a different loop" errors.

    Commit should be handled explicitly within the task.
    """
    session: AsyncSession = get_celery_async_session_factory()()
    try:
        yield session
    except Exception:
        logger.error("Exception in Celery task DB session, rolling back.", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()

async def init_db():
    """
    Initialize the database by creating all tables.
    """
    try:
        # Import base here instead to avoid circular imports
        from app.db.base import __all__ as models
        logger.info(f"Initializing database with models: {models}")
        
        if settings.ENVIRONMENT == "test" or get_async_database_url().startswith("sqlite"):
            # Use sync method for SQLite for better compatibility
            Base.metadata.create_all(bind=sync_engine)
        else:
            # Use async method for production databases
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise DatabaseException(f"Failed to initialize database: {str(e)}")

async def close_db():
    """
    Close database connections.
    """
    if settings.ENVIRONMENT == "test" or get_async_database_url().startswith("sqlite"):
        # For SQLite, just dispose the engine
        async_engine.dispose()
    else:
        # For production databases, await disposal
        await async_engine.dispose()
    
    logger.info("Database connections closed")

def execute_raw_sql(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query and return results as dictionaries.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    start_time = time.time()
    try:
        with get_db() as db:
            result = db.execute(text(query), params or {})
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # Track query execution time
            duration = time.time() - start_time
            track_db_operation("raw_sql", "manual", duration)
            
            return rows
    except Exception as e:
        logger.error(f"Error executing raw SQL: {str(e)}")
        raise DatabaseException(f"Database query failed: {str(e)}", status_code=500) from e

async def execute_raw_sql_async(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query asynchronously and return results as dictionaries.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    start_time = time.time()
    try:
        if settings.ENVIRONMENT == "test" or get_async_database_url().startswith("sqlite"):
            # Use sync method for SQLite
            return execute_raw_sql(query, params)
        else:
            # Use async session for production
            async with async_session_factory() as session:
                result = await session.execute(text(query), params or {})
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                
                # Track query execution time
                duration = time.time() - start_time
                track_db_operation("raw_sql_async", "manual", duration)
                
                return rows
    except Exception as e:
        logger.error(f"Error executing raw SQL asynchronously: {str(e)}")
        raise DatabaseException(f"Database query failed: {str(e)}", status_code=500) from e

def get_db_stats() -> Dict[str, Any]:
    """
    Get database connection statistics.
    
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
        "engine_pool_size": getattr(sync_engine.pool, "size", None),
        "engine_pool_overflow": getattr(sync_engine.pool, "overflow", None),
        "engine_pool_timeout": getattr(sync_engine.pool, "timeout", None),
    }

def optimize_query(query: str) -> str:
    """
    Optimize a SQL query string.
    
    Args:
        query: SQL query string
        
    Returns:
        str: Optimized query
    """
    # Simple optimization - ensure queries use LIMIT
    if "SELECT" in query.upper() and "LIMIT" not in query.upper():
        query += " LIMIT 1000"  # Default limit to prevent large result sets
    return query

def optimize_sqlalchemy_query(query):
    """
    Optimize a SQLAlchemy query object.
    
    Args:
        query: SQLAlchemy query object
        
    Returns:
        SQLAlchemy query: Optimized query
    """
    # Apply optimization strategies to SQLAlchemy queries
    # This is a placeholder for more advanced optimizations
    return query

class DatabaseSession:
    """Context manager for database sessions supporting both sync and async usage."""
    
    def __init__(self, session_factory):
        """Initialize with a session factory."""
        self.session_factory = session_factory
        self.db = None
        self._closed = False
        
        # Determine if the session factory produces async sessions
        self.is_async = getattr(session_factory, 'is_async', False)
        
        # For session factories without an is_async attribute, try to infer
        if not hasattr(session_factory, 'is_async'):
            if hasattr(session_factory, '__call__'):
                test_session = None
                try:
                    test_session = session_factory()
                    self.is_async = hasattr(test_session, '__aenter__') or hasattr(test_session, 'async_execute')
                except Exception:
                    self.is_async = False
                finally:
                    if test_session is not None and hasattr(test_session, 'close'):
                        try:
                            if inspect.iscoroutinefunction(test_session.close):
                                asyncio.create_task(test_session.close())
                            else:
                                test_session.close()
                        except Exception:
                            pass
    
    def __enter__(self):
        """Enter the context manager for synchronous sessions."""
        if self.is_async:
            raise SQLAlchemyError("Cannot use sync context manager with async session")
        
        if self._closed:
            raise SQLAlchemyError("Cannot reuse a closed session")
        
        self.db = self.session_factory()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager for synchronous sessions."""
        if self.db is None:
            return
        
        try:
            if exc_type is not None:
                try:
                    self.db.rollback()
                except Exception as e:
                    logger.error(f"Error rolling back session: {e}")
            else:
                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Error committing session: {e}")
                    try:
                        self.db.rollback()
                    except Exception as e2:
                        logger.error(f"Error rolling back session after commit failure: {e2}")
        finally:
            try:
                self.db.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            
            self.db = None
            self._closed = True
    
    async def __aenter__(self):
        """Enter the context manager for asynchronous sessions."""
        if not self.is_async:
            raise SQLAlchemyError("Cannot use async context manager with sync session")
        
        if self._closed:
            raise SQLAlchemyError("Cannot reuse a closed session")
        
        self.db = self.session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager for asynchronous sessions."""
        if self.db is None:
            return
        
        try:
            if exc_type is not None:
                try:
                    await self.db.rollback()
                except Exception as e:
                    logger.error(f"Error rolling back async session: {e}")
            else:
                try:
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Error committing async session: {e}")
                    try:
                        await self.db.rollback()
                    except Exception as e2:
                        logger.error(f"Error rolling back async session after commit failure: {e2}")
        finally:
            try:
                # Check if close is a coroutine function and await it
                if hasattr(self.db, 'close'):
                    close_method = self.db.close
                    if inspect.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
            except Exception as e:
                logger.error(f"Error closing async session: {e}")
            
            self.db = None
            self._closed = True
    
    async def execute(self, statement, *args, **kwargs):
        """Execute a statement with the async session."""
        if self._closed or self.db is None:
            raise SQLAlchemyError("Session is closed or not initialized")
        
        if not self.is_async:
            raise SQLAlchemyError("Cannot use async execution with sync session")
        
        return await self.db.execute(statement, *args, **kwargs)
    
    def execute_sync(self, statement, *args, **kwargs):
        """Execute a statement with the sync session."""
        if self._closed or self.db is None:
            raise SQLAlchemyError("Session is closed or not initialized")
        
        if self.is_async:
            raise SQLAlchemyError("Cannot use sync execution with async session")
        
        return self.db.execute(statement, *args, **kwargs) 