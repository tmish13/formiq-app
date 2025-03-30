from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.logging import logger
import aiosqlite

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

# Create sync engine with connection pooling
sync_engine = create_engine(
    get_database_url(),
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.ENVIRONMENT == "test" else {}
)

# Create async engine with connection pooling
engine = create_async_engine(
    get_async_database_url(),
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.ENVIRONMENT == "test" else {}
)

# Create sync session factory
SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

def get_db():
    """Get sync database session with proper error handling."""
    session = SessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

async def get_async_db():
    """Get async database session with proper error handling."""
    session = AsyncSessionLocal()
    try:
        yield session
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        await session.rollback()
        raise
    finally:
        await session.close()

async def init_db():
    """Initialize database with proper error handling."""
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

async def close_db():
    """Close database connections."""
    try:
        await engine.dispose()
        await sync_engine.dispose()
        logger.info("Database connections closed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise

def optimize_query(query: str) -> str:
    """Optimize a SQL query by adding appropriate indexes and hints."""
    # Add query optimization logic here
    # This is a placeholder implementation
    return query 