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
    db_url = get_database_url()
    
    if db_url.startswith("sqlite://"):
        # For SQLite, use aiosqlite driver
        return db_url.replace("sqlite://", "sqlite+aiosqlite://")
    elif db_url.startswith("postgresql://"):
        # For PostgreSQL, use asyncpg driver
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        # For other databases, raise an error as we don't know the async driver
        raise DatabaseError(f"Unsupported database type for async operations: {db_url}", status_code=500)

# Create engine for synchronous operations
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    # SQLite connection needs special handling
    sync_engine = create_engine(
        get_database_url(),
        poolclass=NullPool,  # Use NullPool for SQLite to avoid thread issues
        echo=settings.DB_ECHO,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL and other databases - optimized for production
    connect_args = {
        "connect_timeout": 10,
        # Add statement timeout to prevent long-running queries
        "options": "-c statement_timeout=15000"  # 15 seconds
    }
    
    # Add SSL if required (for production)
    if settings.ENVIRONMENT == "production" and settings.SSL_REQUIRED:
        connect_args["sslmode"] = "require"
    
    sync_engine = create_engine(
        get_database_url(),
        poolclass=QueuePool if settings.ENVIRONMENT not in ["test"] else NullPool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DB_ECHO,
        connect_args=connect_args if not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}
    )

# Create async engine
if settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite://"):
    # SQLite async engine
    async_engine = create_async_engine(
        get_async_database_url(),
        poolclass=NullPool,  # Use NullPool for SQLite
        echo=settings.DB_ECHO,
        connect_args={"check_same_thread": False}
    )
    logger.info(f"Created SQLite async engine with NullPool: {get_async_database_url()}")
elif settings.SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
    # PostgreSQL async engine - optimized for production
    async_connect_args = {
        "command_timeout": 10,
        "statement_timeout": 15000,  # 15 seconds statement timeout
        "connect_timeout": 10
    }
    
    # Add SSL if required (for production)
    if settings.ENVIRONMENT == "production" and settings.SSL_REQUIRED:
        async_connect_args["ssl"] = True
    
    async_engine = create_async_engine(
        get_async_database_url(),
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        connect_args=async_connect_args
    )
    logger.info(f"Created PostgreSQL async engine with QueuePool: {get_async_database_url()}")
else:
    # For other databases, we won't create an async engine
    logger.warning(f"No async engine created for database URL: {get_database_url()}")
    async_engine = None

# Setup event listeners for connection monitoring
@event.listens_for(sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Track new connections."""
    connection_stats["active_connections"] += 1
    connection_stats["total_connections"] += 1
    connection_stats["max_concurrent"] = max(
        connection_stats["max_concurrent"], 
        connection_stats["active_connections"]
    )
    # Only log at debug level to avoid log flooding with 1,000 users
    if connection_stats["total_connections"] % 50 == 0:
        logger.info(f"Database connection milestone: {connection_stats['total_connections']} total connections created")
    logger.debug(f"Database connection opened. Active: {connection_stats['active_connections']}")

@event.listens_for(sync_engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Track closed connections."""
    connection_stats["active_connections"] -= 1
    logger.debug(f"Database connection closed. Active: {connection_stats['active_connections']}")

@event.listens_for(sync_engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """
    Detect dead connections and record checkout time.
    
    This listener ensures connections are valid when checked out from the pool.
    """
    connection_record.info['checkout_time'] = time.time()
    
    # Test if connection is dead
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except Exception as ex:
        connection_stats["connection_errors"] += 1
        connection_stats["last_error_time"] = time.time()
        connection_stats["last_error_message"] = str(ex)
        
        # Reconnect by raising DisconnectionError
        logger.warning(f"Connection failed health check: {str(ex)}")
        raise DisconnectionError("Connection failed health check") from ex
    finally:
        cursor.close()

@event.listens_for(sync_engine, "checkin")
def checkin(dbapi_connection, connection_record):
    """
    Record connection usage time on checkin.
    
    This tracks how long connections are used before returned to the pool.
    """
    checkout_time = connection_record.info.get('checkout_time')
    if checkout_time is not None:
        usage_time = time.time() - checkout_time
        logger.debug(f"Connection used for {usage_time:.2f} seconds")
        
        # Log long-running connections
        if usage_time > 10:  # 10 seconds threshold
            logger.warning(f"Long running database connection: {usage_time:.2f} seconds")
        
        # Clear checkout time
        connection_record.info['checkout_time'] = None

# Create sync session factory for synchronous routes
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Create async session factory - moved from app.db.session
async_session = sessionmaker(
    async_engine, 
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def get_engine():
    """Create SQLAlchemy engine with optimized connection pooling."""
    return create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DB_ECHO
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextlib.contextmanager
def get_db() -> Session:
    """Get database session with monitoring."""
    db = SessionLocal()
    start_time = time.time()
    try:
        # Update active connections metric
        db_connections.labels(state="active").inc()
        yield db
    finally:
        duration = time.time() - start_time
        # Track operation duration
        track_db_operation("session", "all", duration)
        db_connections.labels(state="active").dec()
        db.close()

def check_db_connection():
    """Verify database connection and connection pooling."""
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return True
    except Exception as e:
        track_db_operation("connection_error", "all", 0)
        raise e

# Initialize connection pool
engine.pool.dispose()
check_db_connection()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with proper error handling.
    
    This is a dependency injectable session provider for asynchronous routes.
    
    Yields:
        AsyncSession: Async SQLAlchemy session
    """
    if async_engine is None:
        raise DatabaseError("Async database engine not available", status_code=500)
        
    start_time = time.time()
    async with async_session() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Async database error: {str(e)}", exc_info=True)
            await session.rollback()
            raise DatabaseError(f"Database error occurred: {str(e)}", original_error=e)
        except Exception as e:
            logger.error(f"Unexpected error in async database session: {str(e)}", exc_info=True)
            await session.rollback()
            raise
        finally:
            duration = time.time() - start_time
            if duration > 0.5:  # Log slow operations (>500ms)
                logger.warning(f"Slow async database operation: {duration:.2f}s")
            logger.debug(f"Async database session used for {duration:.4f}s")
            await session.close()

async def init_db():
    """
    Initialize database tables.
    
    This creates all tables defined in the models.
    
    Raises:
        DatabaseError: On initialization errors
    """
    try:
        logger.info("Creating database tables...")
        # Import all models to ensure they're registered with Base.metadata
        # This import is inside the function to avoid circular imports
        from app.db.base import Base
        
        if async_engine is None:
            raise DatabaseError("Async database engine not available", status_code=500)
            
        async with async_engine.begin() as conn:
            try:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully")
            except SQLAlchemyError as e:
                # Check if the error is "table already exists" which can be ignored
                if "already exists" in str(e):
                    logger.info("Some tables already exist, continuing initialization")
                else:
                    raise
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise DatabaseError(f"Failed to initialize database: {str(e)}", status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {str(e)}")
        raise DatabaseError(f"Unexpected error initializing database: {str(e)}", status_code=500)

async def close_db():
    """
    Close database connections.
    
    This disposes of all engine connections.
    
    Raises:
        DatabaseError: On connection closure errors
    """
    try:
        logger.info("Closing database connections...")
        if async_engine:
            await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise DatabaseError(f"Error closing database connections: {str(e)}", status_code=500)
    except Exception as e:
        logger.error(f"Unexpected error closing database connections: {str(e)}")
        raise DatabaseError(f"Unexpected error closing database connections: {str(e)}", status_code=500)

def execute_raw_sql(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query synchronously.
    
    Args:
        query: SQL query
        params: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results as list of dictionaries
        
    Raises:
        DatabaseError: On query execution errors
    """
    db = SessionLocal()
    try:
        result = db.execute(text(query), params)
        return [dict(row) for row in result]
    except SQLAlchemyError as e:
        logger.error(f"Raw SQL error: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to execute raw SQL: {str(e)}") from e
    finally:
        db.close()

async def execute_raw_sql_async(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query asynchronously.
    
    Args:
        query: SQL query
        params: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results as list of dictionaries
        
    Raises:
        DatabaseError: On query execution errors
    """
    if async_engine is None:
        raise DatabaseError("Async database engine not available", status_code=500)
        
    async with async_session() as session:
        try:
            result = await session.execute(text(query), params)
            return [dict(row) for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Raw SQL error (async): {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to execute raw SQL: {str(e)}") from e

def get_db_stats() -> Dict[str, Any]:
    """
    Get database connection statistics.
    
    Returns:
        Dict[str, Any]: Connection statistics
    """
    return {
        **connection_stats,
        "pool_status": {
            "size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "timeout": settings.DB_POOL_TIMEOUT,
            "recycle": settings.DB_POOL_RECYCLE,
        },
        "checkout_count": getattr(sync_engine.pool, "checkedout", 0),
        "checkin_count": getattr(sync_engine.pool, "checkedin", 0),
    }

def optimize_query(query: str) -> str:
    """
    Optimize a SQL query by adding appropriate indexes and hints.
    
    Args:
        query: SQL query to optimize
        
    Returns:
        str: Optimized query
    """
    # Add query optimization logic here
    # This is a placeholder implementation
    return query 

def optimize_sqlalchemy_query(query):
    """
    Optimize a SQLAlchemy query with appropriate joins and eager loading.
    
    Args:
        query: SQLAlchemy query to optimize
        
    Returns:
        Any: Optimized query
    """
    if hasattr(query, 'join'):
        # Add query optimization logic for joins
        return query
    return query 