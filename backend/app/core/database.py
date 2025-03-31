from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging import logger
import aiosqlite
import inspect
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional, Union

# Create Base class for models
Base = declarative_base()

def get_database_url() -> str:
    """Get the appropriate database URL based on environment."""
    if settings.ENVIRONMENT == "test":
        return "sqlite:///./test.db"
    return settings.SQLALCHEMY_DATABASE_URI

def get_async_database_url() -> str:
    """Get the appropriate async database URL based on environment."""
    if settings.ENVIRONMENT == "test":
        return "sqlite+aiosqlite:///./test.db"
    return settings.SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+asyncpg://")

def get_engine_kwargs(is_async: bool = False):
    """Get engine kwargs based on environment."""
    kwargs = {
        "echo": settings.DB_ECHO,
    }
    
    if settings.ENVIRONMENT == "test":
        kwargs.update({
            "poolclass": NullPool,
            "connect_args": {"check_same_thread": False} if not is_async else {}
        })
    else:
        kwargs.update({
            "poolclass": QueuePool,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
            "connect_args": {
                "command_timeout": 10
            } if is_async else {}
        })
    return kwargs

# Create engines based on environment
sync_engine = create_engine(
    get_database_url(),
    **get_engine_kwargs(is_async=False)
)

async_engine = create_async_engine(
    get_async_database_url(),
    **get_engine_kwargs(is_async=True)
)

# Create sync session factory
SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def get_db():
    """Get sync database session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError(f"Database error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in database session: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

async def get_async_db():
    """Get async database session with proper error handling."""
    session = AsyncSessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        await session.rollback()
        raise DatabaseError(f"Database error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in database session: {str(e)}", exc_info=True)
        await session.rollback()
        raise
    finally:
        await session.close()

class DatabaseSession:
    """Database session context manager."""

    def __init__(self, session_factory: Optional[Callable[[], Union[Session, AsyncSession]]] = None):
        """Initialize database session context manager."""
        self.session_factory = session_factory or AsyncSessionLocal
        # Check if session factory is async by looking at its type or if it's a function
        self._is_async = (
            isinstance(self.session_factory, async_sessionmaker) or
            (inspect.isfunction(self.session_factory) and inspect.iscoroutinefunction(self.session_factory)) or
            (hasattr(self.session_factory, 'class_') and issubclass(self.session_factory.class_, AsyncSession)) or
            (hasattr(self.session_factory, 'is_async') and self.session_factory.is_async)
        )
        self.db: Optional[Union[Session, AsyncSession]] = None
        self._closed = False

    def _check_session(self):
        """Check if session is closed or not initialized."""
        if self._closed or not self.db:
            raise SQLAlchemyError("Session is closed or not initialized")

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying session."""
        self._check_session()
        return getattr(self.db, name)

    async def execute(self, *args, **kwargs):
        """Execute a query on the session."""
        self._check_session()
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(*args, **kwargs)
            return result
        raise SQLAlchemyError("Cannot use async execution with sync session")

    def execute_sync(self, *args, **kwargs):
        """Execute a query synchronously on the session."""
        self._check_session()
        if not isinstance(self.db, AsyncSession):
            result = self.db.execute(*args, **kwargs)
            return result
        raise SQLAlchemyError("Cannot use sync execution with async session")

    async def __aenter__(self):
        """Enter async context."""
        if self._closed:
            raise SQLAlchemyError("Cannot reuse a closed session")
        
        if not self._is_async:
            self._closed = True
            raise SQLAlchemyError("Cannot use sync session factory in async context")
        
        try:
            self.db = self.session_factory()
            if not isinstance(self.db, AsyncSession):
                self._closed = True
                raise SQLAlchemyError("Session factory returned non-async session")
            return self
        except Exception as e:
            self._closed = True
            if self.db:
                await self.db.close()
                self.db = None
            raise SQLAlchemyError(f"Failed to create session: {str(e)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if not self.db:
            self._closed = True
            return

        try:
            if exc_type is None:
                try:
                    await self.db.commit()
                except SQLAlchemyError as commit_error:
                    try:
                        await self.db.rollback()
                    except SQLAlchemyError as rollback_error:
                        raise SQLAlchemyError("Failed to rollback transaction: Rollback failed") from rollback_error
                    raise SQLAlchemyError("Failed to commit transaction: Commit failed") from commit_error
            else:
                try:
                    await self.db.rollback()
                except SQLAlchemyError as rollback_error:
                    raise SQLAlchemyError("Failed to rollback transaction: Rollback failed") from rollback_error
        finally:
            try:
                await self.db.close()
            except Exception:
                pass
            finally:
                self.db = None
                self._closed = True

    def __enter__(self):
        """Enter sync context."""
        if self._closed:
            raise SQLAlchemyError("Cannot reuse a closed session")
            
        if self._is_async:
            raise SQLAlchemyError("Cannot use async session factory in sync context")
            
        try:
            self.db = self.session_factory()
            if isinstance(self.db, AsyncSession):
                self._closed = True
                raise SQLAlchemyError("Session factory returned async session")
            return self
        except Exception as e:
            self._closed = True
            if self.db:
                self.db.close()
                self.db = None
            raise SQLAlchemyError(f"Failed to create session: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the sync context manager."""
        if not self.db:
            self._closed = True
            return

        try:
            if exc_type is None:
                try:
                    self.db.commit()
                except SQLAlchemyError as commit_error:
                    try:
                        self.db.rollback()
                    except SQLAlchemyError as rollback_error:
                        raise SQLAlchemyError("Failed to rollback transaction: Rollback failed") from rollback_error
                    raise SQLAlchemyError("Failed to commit transaction: Commit failed") from commit_error
            else:
                try:
                    self.db.rollback()
                except SQLAlchemyError as rollback_error:
                    raise SQLAlchemyError("Failed to rollback transaction: Rollback failed") from rollback_error
        finally:
            self.db.close()
            self.db = None
            self._closed = True

def get_db_session(session_factory=None):
    """Get a database session context manager."""
    if session_factory is None:
        if settings.ENVIRONMENT == "test":
            # For test environment, ensure we're using the async session factory
            # that's already configured for SQLite
            session_factory = AsyncSessionLocal
        else:
            session_factory = SessionLocal
    return DatabaseSession(session_factory)

async def init_db():
    """Initialize database with proper error handling."""
    try:
        async with async_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

async def close_db():
    """Close database connections."""
    try:
        await async_engine.dispose()
        sync_engine.dispose()
        logger.info("Database connections closed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise

def optimize_query(query: str) -> str:
    """Optimize a SQL query by adding appropriate indexes and hints."""
    # Add query optimization logic here
    # This is a placeholder implementation
    return query 

def optimize_sqlalchemy_query(query):
    """Optimize a SQLAlchemy query with appropriate joins and eager loading."""
    if hasattr(query, 'join'):
        # Add query optimization logic for joins
        return query
    return query 