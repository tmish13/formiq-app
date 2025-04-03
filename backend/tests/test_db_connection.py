"""Test database connection."""
import pytest
import asyncio
from sqlalchemy import text
from app.core.database import async_engine, init_db

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection."""
    # Test simple connection
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
    # Test transaction
    async with async_engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
    # Test initialization
    await init_db()
    
    # Test that tables were created
    async with async_engine.connect() as conn:
        # Check if users table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ))
        tables = result.fetchall()
        assert len(tables) > 0, "Users table not found"
        
        # Verify users table structure
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = {row[1] for row in result.fetchall()}
        expected_columns = {"id", "email", "hashed_password", "full_name"}
        assert expected_columns.issubset(columns), f"Missing columns in users table. Found: {columns}"
        
    print("Database connection and structure tests passed!") 