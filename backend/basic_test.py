import asyncio
import logging
from sqlalchemy import text, MetaData, Table, Column, Integer, String, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./simple.db"
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    full_name = Column(String)
    password = Column(String)

async def init_db():
    # Create async engine
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    return engine, async_session

async def test_connection():
    engine, async_session = await init_db()
    
    try:
        # Test simple query
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"Test query result: {value}")
        
        # Test table operations
        async with async_session() as session:
            # Check if user exists
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            logger.info(f"User count: {count}")
            
            # Add a test user
            user = User(email="test@example.com", full_name="Test User", password="password")
            session.add(user)
            await session.commit()
            logger.info("Added test user")
            
            # Verify user was added
            result = await session.execute(text("SELECT * FROM users"))
            users = result.fetchall()
            logger.info(f"Users in database: {users}")
        
        logger.info("Database test completed successfully")
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection()) 