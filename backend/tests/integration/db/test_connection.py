"""Test database connection script."""
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def test_sqlite_connection():
    """Test SQLite connection."""
    print("Testing SQLite connection...")
    
    # SQLite file path
    db_file = "./test_connection.db"
    
    # Remove existing file if it exists
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing database file: {db_file}")
    
    # Create async engine
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        echo=True,
        connect_args={"check_same_thread": False}
    )
    
    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Test connection
    async with async_session() as session:
        # Execute a simple query
        result = await session.execute(text("SELECT 1 as test"))
        row = result.first()
        print(f"Query result: {row[0]}")
    
    # Close engine
    await engine.dispose()
    print("Connection test completed successfully!")

async def main():
    """Main function."""
    try:
        await test_sqlite_connection()
        print("All tests passed!")
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 