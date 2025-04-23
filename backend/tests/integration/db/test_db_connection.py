import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def test_connection():
    """Test the database connection using the configured URI."""
    print(f"Attempting to connect to: {settings.SQLALCHEMY_DATABASE_URI}")
    
    try:
        # Create engine with the configured URI
        engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI,
            echo=True,
            future=True
        )
        
        # Test connection - use text() to make it compatible with all dialects
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            print(f"Connection successful! Test query result: {value}")
            
        return True
    except Exception as e:
        print(f"Connection failed with error: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1) 