"""Simple test app for database connection."""
import asyncio
import os
from sqlalchemy import Column, Integer, String, text, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.future import select

# Create Base for models with proper naming convention
Base = declarative_base()

# Sample User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

# Engine configuration - using SQLite with aiosqlite driver
DB_FILE = "./test_async.db"

# Remove the existing database file if it exists
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
    print(f"Removed existing database file: {DB_FILE}")

# Create engine with proper configuration
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DB_FILE}",
    poolclass=NullPool,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        # Drop all tables first to ensure clean slate
        await conn.run_sync(Base.metadata.drop_all)
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    # Insert test user
    print("Adding test user...")
    async with async_session() as session:
        async with session.begin():
            # Create a test user
            test_user = User(name="Test User", email="test@example.com")
            session.add(test_user)
            await session.commit()
            print("Test user added successfully")

async def test_db_connection():
    """Test database connection."""
    # Initialize database with clean slate
    await init_db()
    
    # Test query
    print("\nTesting database connection:")
    async with async_session() as session:
        # Simple connection test
        result = await session.execute(text("SELECT 1"))
        print(f"Database connection test: {result.scalar()}")
        
        # Query users
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  - {user.name} ({user.email})")

if __name__ == "__main__":
    print("Starting database test...")
    asyncio.run(test_db_connection())
    print("Database test completed successfully!") 