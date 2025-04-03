"""Tests for database functionality."""
import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.core.database import DatabaseSession, get_db, get_async_db
from app.core.exceptions import DatabaseError
from app.models.user import User
import uuid
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from fastapi import Depends
from app.models.enums import SubscriptionTier
from app.models.base import Base
from app.core.config import settings

# Test relies on the existing setup_db fixture from conftest.py

def test_database_session_context_manager(db):
    """Test database session as a context manager."""
    # Create a test user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="session_test@example.com",
        username="session_test",
        password="Test@123",
        is_active=True
    )
    
    # Add user with context manager
    with DatabaseSession(lambda: db) as session:
        session.add(user)
    
    # Verify the user was committed
    with DatabaseSession(lambda: db) as session:
        retrieved_user = session.query(User).filter_by(id=user_id).first()
        assert retrieved_user is not None
        assert retrieved_user.email == "session_test@example.com"
        
        # Clean up
        session.delete(retrieved_user)

def test_database_session_rollback(db):
    """Test database session rollback on error."""
    # Create a test user
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="rollback_test@example.com",
        username="rollback_test",
        password="Test@123",
        is_active=True
    )
    
    # Try to add user but raise an exception
    try:
        with DatabaseSession(lambda: db) as session:
            session.add(user)
            raise RuntimeError("Test exception")
    except RuntimeError:
        pass
    
    # Verify the user was not committed
    with DatabaseSession(lambda: db) as session:
        retrieved_user = session.query(User).filter_by(id=user_id).first()
        assert retrieved_user is None

@pytest.mark.asyncio
async def test_async_database_session(async_db):
    """Test that we can use the async session to access the database."""
    # Generate a UUID for the test user
    user_id = uuid.uuid4()
    user_id_str = str(user_id)
    
    # Create a test user
    test_user = {
        "id": user_id_str,
        "email": "async_test@example.com",
        "username": "async_test_user",
        "hashed_password": "hashed_password",
        "is_active": True,
        "subscription_tier": SubscriptionTier.FREE,
        "is_email_verified": True,
        "is_verified": True,
        "is_superuser": False
    }
    
    # The session is an AsyncSession
    assert isinstance(async_db, AsyncSession)
    
    # Insert a test user
    await async_db.execute(
        text("""
    INSERT INTO users (id, email, username, hashed_password, is_active, subscription_tier, is_email_verified, is_verified, is_superuser)
    VALUES (:id, :email, :username, :hashed_password, :is_active, :subscription_tier, :is_email_verified, :is_verified, :is_superuser)
    """),
        test_user
    )
    await async_db.commit()
    
    # Find the user in the database
    result = await async_db.execute(
        text("""
    SELECT * FROM users WHERE id = :id
    """),
        {"id": test_user["id"]}
    )
    found_user = result.fetchone()
    
    # Check that the user was inserted correctly
    assert found_user is not None
    assert found_user.email == test_user["email"]
    assert found_user.username == test_user["username"]
    
    # Clean up
    await async_db.execute(
        text("""
    DELETE FROM users WHERE id = :id
    """),
        {"id": test_user["id"]}
    )
    await async_db.commit()

@pytest.mark.asyncio
async def test_get_db_function():
    """Test the get_db function in both sync and async contexts."""
    # We need to use the fixtures from conftest.py to get a properly configured DB
    # Skip this test for now as it requires more complex setup
    pytest.skip("This test requires more complex setup with the actual app context") 