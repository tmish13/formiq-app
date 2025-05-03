"""Test database connection."""
import pytest
import asyncio
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_engine, init_db
from app.db.base_class import Base
from app.db.base import *  # Import all models

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection."""
    # Ensure database is initialized with all models
    async with async_engine.begin() as conn:
        # Drop all tables to ensure we're starting fresh
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables from metadata
        await conn.run_sync(Base.metadata.create_all)
        
    # Test simple connection
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
    # Test transaction
    async with async_engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
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
        expected_columns = {"id", "email", "hashed_password"}
        assert expected_columns.issubset(columns), f"Missing columns in users table. Found: {columns}"
        
    # Inspect all tables to verify schema
    async with async_engine.connect() as conn:
        # Get list of all tables via SQLAlchemy inspect
        inspector = await conn.run_sync(lambda sync_conn: inspect(sync_conn))
        tables = await conn.run_sync(lambda sync_conn: inspector.get_table_names())
        
        # Log tables
        print(f"Tables found in database: {tables}")
        
        # Verify expected models have corresponding tables
        expected_tables = {
            'users', 'exercise_templates', 'form_checks', 'feedback_items', 
            'workouts', 'exercises', 'workout_plans', 'subscriptions', 'videos'
        }
        assert expected_tables.issubset(set(tables)), f"Missing expected tables. Found: {tables}"
        
    print("Database connection and structure tests passed!") 